"""
test_group_d_mcp_roundtrip.py — Integration test suite for Group D (MCP Round-Trip) patterns.

Reference: docs/testing.md & docs/testing_examples.md (Patterns D-1 through D-3)
"""

import asyncio
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from agent import run_agent, run_agent_with_trace


@pytest.mark.asyncio
async def test_D1_mcp_save_note_roundtrip():
    """Pattern D-1: Agent calls save_note tool via FastMCP server."""
    query = (
        "Save this note to PAT-001: "
        "SUBJECTIVE: Patient reports tension headache for 3 days.\n"
        "OBJECTIVE: BP 120/80.\n"
        "ASSESSMENT: For physician review — tension headache (G44.2).\n"
        "PLAN: Rest, hydration."
    )
    response, trace = await run_agent_with_trace(query)
    
    assert "NOTE-PAT001-" in response or "save_note" in str(trace).lower()
    tool_calls = [t["name"] for t in trace if t.get("type") == "tool_call"]
    assert "save_note" in tool_calls


@pytest.mark.asyncio
async def test_D2_mcp_patient_history_roundtrip():
    """Pattern D-2: Agent calls get_patient_history tool via FastMCP server."""
    query = "What did I note for PAT-001's last visit?"
    response, trace = await run_agent_with_trace(query)
    
    tool_calls = [t["name"] for t in trace if t.get("type") == "tool_call"]
    assert "get_patient_history" in tool_calls
    assert len(response.strip()) > 20
