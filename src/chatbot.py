"""
chatbot.py — MedNote Scribe CLI chatbot.

Run:
    python src/chatbot.py

Paste a doctor-patient transcript at the prompt and get a SOAP note printed
to the terminal. Type 'exit' or press Ctrl+C to quit.
"""

import sys
import logging
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from config import GROQ_API_KEY, GROQ_MODEL, SYSTEM_PROMPT_PATH

log = logging.getLogger(__name__)

# Initialize embeddings and Chroma DB lazily or globally
_vectorstore = None


def get_vectorstore():
    """Lazily load and cache the vector store connection."""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    from config import CHROMA_DB_DIR, EMBEDDING_MODEL_NAME
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    if not CHROMA_DB_DIR.exists():
        log.warning(f"Chroma DB directory not found at {CHROMA_DB_DIR}. Running without RAG context.")
        return None

    try:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        _vectorstore = Chroma(
            persist_directory=str(CHROMA_DB_DIR),
            embedding_function=embeddings,
        )
        return _vectorstore
    except Exception as e:
        log.error(f"Failed to load Chroma DB: {e}")
        return None


def retrieve_context(query: str) -> str:
    """Query the vector database for top-3 relevant chunks and format as text."""
    db = get_vectorstore()
    if db is None:
        return "No context available (vector database not found)."

    try:
        docs = db.similarity_search(query, k=3)
        formatted_chunks = []
        for idx, doc in enumerate(docs, start=1):
            source = doc.metadata.get("source", "unknown")
            formatted_chunks.append(
                f"--- Context Chunk #{idx} (Source: {source}) ---\n{doc.page_content}"
            )
        return "\n\n".join(formatted_chunks)
    except Exception as e:
        log.error(f"Retrieval error: {e}")
        return f"Retrieval failed: {e}"


def load_system_prompt(path: Path) -> str:
    """Read the system prompt from the markdown file."""
    return path.read_text(encoding="utf-8")


def build_chain(system_prompt: str):
    """Build the LangChain LCEL chain: retrieval | prompt | llm | parser."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "Retrieved Context:\n{context}\n\nUser Input:\n{user_input}"
            ),
        ]
    )
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0.2,  # Low temperature for consistent, factual clinical notes
    )

    # Use a dictionary runnable logic to retrieve context based on user_input
    inputs_with_context = {
        "context": lambda inputs: retrieve_context(inputs["user_input"]),
        "user_input": lambda inputs: inputs["user_input"]
    }

    return inputs_with_context | prompt | llm | StrOutputParser()


def run_chatbot() -> None:
    """Run the interactive CLI loop."""
    system_prompt = load_system_prompt(SYSTEM_PROMPT_PATH)
    chain = build_chain(system_prompt)

    print("=" * 60)
    print("  MedNote Scribe — Clinical Documentation Assistant")
    print(f"  Model: {GROQ_MODEL}")
    print("=" * 60)
    print("Paste a transcript or ask a question. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("Goodbye.")
            break

        print("\nMedNote Scribe:\n")
        response = chain.invoke({"user_input": user_input})
        print(response)
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    run_chatbot()
