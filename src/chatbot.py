"""
chatbot.py — MedNote Scribe CLI chatbot.

Run:
    python src/chatbot.py

Paste a doctor-patient transcript at the prompt and get a SOAP note printed
to the terminal. Type 'exit' or press Ctrl+C to quit.
"""

from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from config import GROQ_API_KEY, GROQ_MODEL, SYSTEM_PROMPT_PATH


def load_system_prompt(path: Path) -> str:
    """Read the system prompt from the markdown file."""
    return path.read_text(encoding="utf-8")


def build_chain(system_prompt: str):
    """Build the LangChain LCEL chain: prompt | llm | parser."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{user_input}"),
        ]
    )
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0.2,  # Low temperature for consistent, factual clinical notes
    )
    return prompt | llm | StrOutputParser()


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
