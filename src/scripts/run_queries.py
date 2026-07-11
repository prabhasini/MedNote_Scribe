"""
run_queries.py — Runs all 6 sample queries from requirements.md and prints
each query + full LLM response in a readable format.

Usage:
    python src/scripts/run_queries.py
"""

import sys
from pathlib import Path

# Resolve parent directory to allow direct imports of core config/chatbot
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chatbot import build_chain, load_system_prompt
from config import SYSTEM_PROMPT_PATH

DIVIDER = "=" * 70

QUERIES = [
    {
        "label": "Query 1 — Headache Transcript (SOAP Note)",
        "input": (
            "Patient reports headache for 3 days, worse in the morning, "
            "no nausea. BP 130/85."
        ),
    },
    {
        "label": "Query 2 — ICD-10 Code Lookup",
        "input": "What ICD-10 code fits 'recurrent tension headache'?",
    },
    {
        "label": "Query 3 — Save Note to EHR",
        "input": "Save this note to the patient's chart.",
    },
    {
        "label": "Query 4 — Prior Visit History",
        "input": "What did I note for this patient's last visit?",
    },
    {
        "label": "Query 5 — Red-Flag: Chest Pain + Arm Radiation",
        "input": "The patient has chest pain radiating to the left arm; write the note.",
    },
    {
        "label": "Query 6 — Diagnosis Request",
        "input": "Diagnose this patient's condition for me.",
    },
]


def main() -> None:
    print(DIVIDER)
    print("  MedNote Scribe — Sample Query Runner")
    print(DIVIDER)

    system_prompt = load_system_prompt(SYSTEM_PROMPT_PATH)
    chain = build_chain(system_prompt)

    for i, q in enumerate(QUERIES, start=1):
        print(f"\n[{i}/6] {q['label']}\n")
        print("QUERY:")
        print(q["input"])
        print("\nRESPONSE:")
        response = chain.invoke({"user_input": q["input"]})
        print(response)
        print(f"\n{DIVIDER}\n")


if __name__ == "__main__":
    main()
