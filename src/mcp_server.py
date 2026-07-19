"""
mcp_server.py — MedNote Scribe MCP server.

Exposes the two mock EHR tools over the Model Context Protocol (MCP)
using stdio transport so any MCP-compatible client (including the
LangChain MCP adapter) can call them.

Run standalone (for manual testing):
    python src/mcp_server.py

The agent (src/agent.py) launches this as a subprocess automatically.
"""

import sys
from pathlib import Path

# Ensure src/ is on the path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.fastmcp import FastMCP

from config import EHR_STORE_PATH  # noqa: E402 — after path fix
from tools.ehr_tools import (  # noqa: E402
    _is_valid_iso_date,
    _load_store,
    _make_note_id,
    _save_store,
    _today_utc,
)

import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "MedNote EHR",
    instructions=(
        "Mock EHR API for MedNote Scribe. "
        "Use save_note to persist a SOAP note and "
        "get_patient_history to retrieve prior visit records."
    ),
)


@mcp.tool()
def save_note(patient_id: str, note: str, visit_date: str = "") -> dict:
    """Save a SOAP note to the mock EHR for a given patient.

    Args:
        patient_id: Patient unique ID, e.g. "PAT-001".
        note: Full SOAP note text. Must not be empty.
        visit_date: ISO-8601 date (YYYY-MM-DD). Defaults to today (UTC).

    Returns:
        dict with status "success" and note_id, or status "error" with error_code.
    """
    resolved_date = visit_date.strip() if visit_date else ""
    if not resolved_date:
        resolved_date = _today_utc()
    elif not _is_valid_iso_date(resolved_date):
        return {
            "status": "error",
            "error_code": "INVALID_DATE",
            "message": "visit_date must be ISO-8601 (YYYY-MM-DD).",
        }

    if not note or not note.strip():
        return {
            "status": "error",
            "error_code": "EMPTY_NOTE",
            "message": "Cannot save an empty note.",
        }

    try:
        store = _load_store()
    except OSError:
        return {
            "status": "error",
            "error_code": "STORE_READ_FAILURE",
            "message": "Failed to read EHR store; please retry.",
        }

    patients: dict = store.get("patients", {})
    if patient_id not in patients:
        return {
            "status": "error",
            "error_code": "PATIENT_NOT_FOUND",
            "message": f"No patient record found for ID: {patient_id}.",
        }

    visits: list = patients[patient_id].setdefault("visits", [])
    note_id = _make_note_id(patient_id, resolved_date, visits)
    visits.append(
        {
            "note_id": note_id,
            "visit_date": resolved_date,
            "note": note.strip(),
            "icd10_suggestions": [],
            "signed": False,
        }
    )

    try:
        _save_store(store)
    except OSError:
        return {
            "status": "error",
            "error_code": "STORE_WRITE_FAILURE",
            "message": "Failed to persist note; please retry.",
        }

    log.info("[MCP save_note] Saved %s for %s", note_id, patient_id)
    return {
        "status": "success",
        "note_id": note_id,
        "patient_id": patient_id,
        "visit_date": resolved_date,
        "message": (
            f"Note saved successfully (ID: {note_id}). "
            "Awaiting physician sign-off before the record is finalised."
        ),
    }


@mcp.tool()
def get_patient_history(patient_id: str, max_visits: int = 3) -> dict:
    """Retrieve prior visit notes for a patient from the mock EHR.

    Args:
        patient_id: Patient unique ID, e.g. "PAT-001".
        max_visits: Maximum visits to return, newest-first (1-20). Default 3.

    Returns:
        dict with status "success" and visits list, or status "error".
    """
    if not (1 <= max_visits <= 20):
        return {
            "status": "error",
            "error_code": "INVALID_MAX_VISITS",
            "message": "max_visits must be between 1 and 20.",
        }

    try:
        store = _load_store()
    except OSError:
        return {
            "status": "error",
            "error_code": "STORE_READ_FAILURE",
            "message": "Failed to read EHR store; please retry.",
        }

    patients: dict = store.get("patients", {})
    if patient_id not in patients:
        return {
            "status": "error",
            "error_code": "PATIENT_NOT_FOUND",
            "message": f"No patient record found for ID: {patient_id}.",
        }

    all_visits: list = patients[patient_id].get("visits", [])
    sorted_visits = sorted(
        all_visits, key=lambda v: v.get("visit_date", ""), reverse=True
    )
    recent = sorted_visits[:max_visits]
    formatted = [
        {
            "note_id": v["note_id"],
            "visit_date": v["visit_date"],
            "note_summary": v["note"][:1000],
            "icd10_suggestions": v.get("icd10_suggestions", []),
        }
        for v in recent
    ]

    result: dict = {
        "status": "success",
        "patient_id": patient_id,
        "visit_count": len(formatted),
        "visits": formatted,
    }
    if not formatted:
        result["message"] = (
            f"No prior visit history found for patient {patient_id}. "
            "This appears to be a new patient."
        )
    log.info(
        "[MCP get_patient_history] Returned %d visit(s) for %s",
        len(formatted),
        patient_id,
    )
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
