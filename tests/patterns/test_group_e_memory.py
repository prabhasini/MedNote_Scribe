"""
test_group_e_memory.py — End-to-end evaluation suite for Group E (Memory & Session Continuity) patterns.

Reference: docs/testing.md & docs/testing_examples.md (Patterns E-1 through E-4)
"""

import asyncio
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from agent import run_agent, run_agent_with_trace


@pytest.mark.asyncio
async def test_E1_cross_session_recall():
    """Pattern E-1: Recalls facts from prior session using agent memory and EHR tools."""
    # Session 1: Note saved
    s1_query = (
        "Save this note for PAT-001: "
        "SUBJECTIVE: Patient presents for hypertension follow-up. On lisinopril 10mg daily.\n"
        "OBJECTIVE: BP 132/82.\n"
        "ASSESSMENT: Essential hypertension (I10).\n"
        "PLAN: Continue Lisinopril 10mg daily."
    )
    await run_agent(s1_query, thread_id="session_pat001_v1")

    # Session 2: New complaint query
    s2_query = "What did I note for PAT-001's last visit?"
    response, trace = await run_agent_with_trace(s2_query, thread_id="session_pat001_v2")

    res_lower = response.lower()
    assert "pat-001" in res_lower or "visit" in res_lower
    tool_calls = [t["name"] for t in trace if t.get("type") == "tool_call"]
    assert "get_patient_history" in tool_calls


@pytest.mark.asyncio
async def test_E2_new_patient_no_history():
    """Pattern E-2: New patient returns graceful zero-visit message."""
    query = "What did I note for PAT-003's last visit?"
    response, trace = await run_agent_with_trace(query, thread_id="session_pat003")

    res_lower = response.lower()
    assert "new patient" in res_lower or "no prior" in res_lower or "no visit" in res_lower
