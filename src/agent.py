"""
agent.py — MedNote Scribe ReAct agent with MCP tool integration.

Replaces the simple LCEL chain in chatbot.py with a LangGraph ReAct agent
that can call EHR tools (save_note, get_patient_history) via the MCP server.

Architecture
------------
1. The MCP server (src/mcp_server.py) is launched as a subprocess (stdio transport).
2. MultiServerMCPClient loads the tool definitions from the server.
3. create_react_agent wires those tools + the RAG retrieval tool into the agent.
4. The agent decides autonomously when to call tools vs. when to generate text.

Usage (async — call from asyncio context):
    from agent import run_agent
    response = await run_agent("Save this note to PAT-001: S: Headache ...")
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure src/ is importable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from config import (
    CHROMA_DB_DIR,
    EMBEDDING_MODEL_NAME,
    GROQ_API_KEY,
    GROQ_MODEL,
    SYSTEM_PROMPT_PATH,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP server path (resolved relative to this file's directory)
# ---------------------------------------------------------------------------
_MCP_SERVER_PATH = Path(__file__).resolve().parent / "mcp_server.py"
_PYTHON = sys.executable  # same venv interpreter


# ---------------------------------------------------------------------------
# RAG retrieval as a LangChain tool (so the agent can call it explicitly)
# ---------------------------------------------------------------------------

_vectorstore = None


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore
    if not CHROMA_DB_DIR.exists():
        log.warning("Chroma DB not found at %s — RAG disabled.", CHROMA_DB_DIR)
        return None
    try:
        from langchain_chroma import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        _vectorstore = Chroma(
            persist_directory=str(CHROMA_DB_DIR),
            embedding_function=embeddings,
        )
        return _vectorstore
    except Exception as exc:
        log.error("Failed to load Chroma DB: %s", exc)
        return None


from langgraph.checkpoint.memory import MemorySaver

# Shared checkpointer for short-term session state across multi-turn queries
_checkpointer = MemorySaver()

@tool
def retrieve_icd10_context(query: str) -> str:
    """Search the RAG index for ICD-10 codes and clinical guidelines relevant to a query.

    Use this when you need to suggest an ICD-10 code or find relevant
    clinical documentation guidelines. Returns the top-3 matching chunks with relevance confidence scores.

    Args:
        query: A clinical question or symptom description.
    """
    db = _get_vectorstore()
    if db is None:
        return "RAG index unavailable (run 'make ingest' first)."
    try:
        results = db.similarity_search_with_relevance_scores(query, k=3)
        chunks = [
            f"--- Chunk #{i} (Score: {score:.4f}, source: {doc.metadata.get('source', 'unknown')}) ---\n{doc.page_content}"
            for i, (doc, score) in enumerate(results, 1)
        ]
        return "\n\n".join(chunks)
    except Exception as exc:
        log.error("RAG retrieval error: %s", exc)
        return f"Retrieval failed: {exc}"


# ---------------------------------------------------------------------------
# Agent builder
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


@asynccontextmanager
async def build_agent_with_mcp():
    """Async context manager that yields a ready-to-use ReAct agent.

    The MCP client connects to the EHR server subprocess and exposes
    save_note + get_patient_history as LangChain-compatible tools alongside
    the local RAG retrieval tool.

    Usage:
        async with build_agent_with_mcp() as agent:
            result = await agent.ainvoke({"messages": [HumanMessage(...)]})
    """
    mcp_client = MultiServerMCPClient(
        {
            "ehr": {
                "command": _PYTHON,
                "args": [str(_MCP_SERVER_PATH)],
                "transport": "stdio",
            }
        }
    )
    # langchain-mcp-adapters v0.1.0: context manager removed; call get_tools() directly
    mcp_tools = await mcp_client.get_tools()
    log.info("MCP tools loaded: %s", [t.name for t in mcp_tools])

    all_tools = mcp_tools + [retrieve_icd10_context]

    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0.2,
    )

    system_prompt = _load_system_prompt()
    agent = create_react_agent(
        llm,
        all_tools,
        prompt=system_prompt,
        checkpointer=_checkpointer,
    )
    yield agent


# ---------------------------------------------------------------------------
# Public convenience wrapper
# ---------------------------------------------------------------------------

async def run_agent(user_input: str, thread_id: str = "default_session") -> str:
    """Run the agent on a single user input and return the final response text."""
    response, _ = await run_agent_with_trace(user_input, thread_id=thread_id)
    return response


async def run_agent_with_trace(
    user_input: str, thread_id: str = "default_session"
) -> tuple[str, list[dict]]:
    """Run the agent on user input and return (final_response, trace_events).

    trace_events contains structured dicts for each tool call, tool output, and RAG retrieval.
    """
    trace_events: list[dict] = []
    async with build_agent_with_mcp() as agent:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"thread_id": thread_id}},
        )

        messages = result.get("messages", [])
        for msg in messages:
            # Tool calls made by AI
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    trace_events.append(
                        {
                            "type": "tool_call",
                            "name": tc.get("name"),
                            "args": tc.get("args"),
                        }
                    )
            # Tool responses
            elif hasattr(msg, "name") and msg.name:
                trace_events.append(
                    {
                        "type": "tool_result",
                        "name": msg.name,
                        "content": str(msg.content)[:800],
                    }
                )

        final_response = messages[-1].content if messages else "No response generated."
        return final_response, trace_events


# ---------------------------------------------------------------------------
# CLI entry point for manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Run a single agent query.")
    parser.add_argument(
        "query",
        nargs="?",
        default="What did I note for PAT-001's last visit?",
        help="The query to send to the agent.",
    )
    args = parser.parse_args()

    print(f"\nQuery: {args.query}\n")
    response = asyncio.run(run_agent(args.query))
    print(f"Agent: {response}\n")
