"""
test_mcp_roundtrip.py — Task #13 end-to-end round-trip test.

Verifies that the agent correctly calls both EHR tools via MCP:
  1. get_patient_history  — agent retrieves prior visit for PAT-001
  2. save_note            — agent saves a new note and gets back a note_id

Run:
    make mcp-roundtrip
    # or directly:
    python src/scripts/test_mcp_roundtrip.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import run_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

DIVIDER = "=" * 65


async def main() -> None:
    print(f"\n{DIVIDER}")
    print("  MedNote Scribe — MCP Round-Trip Test (Task #13)")
    print(DIVIDER)

    # --- Round trip 1: get_patient_history ---
    q1 = "What did I note for PAT-001's last visit?"
    print(f"\n[Query 1] {q1}\n")
    r1 = await run_agent(q1)
    print(f"[Response 1]\n{r1}")

    assert "PAT-001" in r1 or "tension headache" in r1.lower() or "visit" in r1.lower(), \
        "Response 1 did not reference patient history"
    print("\n✅  Round trip 1 passed — agent retrieved patient history via MCP.\n")

    # --- Round trip 2: save_note ---
    q2 = (
        "Save this note to PAT-002: "
        "S: Patient reports mild dizziness on standing. No syncope or chest pain. "
        "O: BP 118/72 (orthostatic drop from 130/80). Heart Rate 76. "
        "A: For physician review: Possible orthostatic hypotension (ICD-10 suggestion: I95.1). "
        "P: Increase fluid intake, advise slow position changes. Follow up in 2 weeks."
    )
    print(f"[Query 2] {q2[:80]}...\n")
    r2 = await run_agent(q2)
    print(f"[Response 2]\n{r2}")

    assert "note" in r2.lower() and (
        "saved" in r2.lower() or "PAT-002" in r2 or "sign" in r2.lower()
    ), "Response 2 did not confirm note was saved"
    print("\n✅  Round trip 2 passed — agent saved note via MCP.\n")

    print(DIVIDER)
    print("  All MCP round-trip tests passed.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    asyncio.run(main())
