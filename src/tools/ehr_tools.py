"""
ehr_tools.py — LangChain tool implementations for the mock EHR API.

Task #11: save_note  — persists a SOAP note for a patient visit.
Task #12: get_patient_history — retrieves prior visit records for a patient.

Storage backend: data/ehr_store.json  (local JSON file, no database required).
See docs/tools.md for the full tool specifications.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Any

from langchain_core.tools import tool

from config import EHR_STORE_PATH

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_store() -> dict[str, Any]:
    """Read and return the EHR store dict. Raises on I/O failure."""
    try:
        return json.loads(EHR_STORE_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        log.error("EHR store read failed: %s", exc)
        raise


def _save_store(store: dict[str, Any]) -> None:
    """Write the EHR store dict back to disk. Raises on I/O failure."""
    try:
        EHR_STORE_PATH.write_text(
            json.dumps(store, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        log.error("EHR store write failed: %s", exc)
        raise


def _is_valid_iso_date(value: str) -> bool:
    """Return True if *value* is a valid YYYY-MM-DD date string."""
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)) and _parse_date(value) is not None


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _today_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _make_note_id(patient_id: str, visit_date: str, visits: list[dict]) -> str:
    """Generate a stable, sequential note ID for a given patient and date."""
    # Count how many notes already exist for this patient on the same date
    seq = sum(1 for v in visits if v.get("visit_date") == visit_date) + 1
    # Normalise patient_id for use in the ID (strip non-alphanumeric)
    pid_clean = re.sub(r"[^A-Za-z0-9]", "", patient_id).upper()
    date_clean = visit_date.replace("-", "")
    return f"NOTE-{pid_clean}-{date_clean}-{seq:03d}"


# ---------------------------------------------------------------------------
# Tool #1 — save_note  (Task #11)
# ---------------------------------------------------------------------------

@tool
def save_note(patient_id: str, note: str, visit_date: str = "") -> dict[str, Any]:
    """Save a SOAP note to the mock EHR for a given patient.

    Use this tool when the physician asks to save, store, or file a note.

    Args:
        patient_id: The patient's unique ID (e.g. "PAT-001").
        note: The full SOAP note text to persist. Must not be empty.
        visit_date: Optional ISO-8601 date (YYYY-MM-DD). Defaults to today (UTC).

    Returns:
        A dict with "status" of "success" or "error" plus supporting fields.
    """
    log.info("[save_note] Called — patient_id=%r visit_date=%r", patient_id, visit_date)

    # --- Resolve and validate visit_date ---
    resolved_date = visit_date.strip() if visit_date else ""
    if not resolved_date:
        resolved_date = _today_utc()
    elif not _is_valid_iso_date(resolved_date):
        log.warning("[save_note] Invalid visit_date: %r", visit_date)
        return {
            "status": "error",
            "error_code": "INVALID_DATE",
            "message": "visit_date must be ISO-8601 (YYYY-MM-DD).",
        }

    # --- Validate note content ---
    if not note or not note.strip():
        log.warning("[save_note] Empty note rejected for patient_id=%r", patient_id)
        return {
            "status": "error",
            "error_code": "EMPTY_NOTE",
            "message": "Cannot save an empty note.",
        }

    # --- Load store ---
    try:
        store = _load_store()
    except OSError:
        return {
            "status": "error",
            "error_code": "STORE_READ_FAILURE",
            "message": "Failed to read EHR store; please retry.",
        }

    # --- Validate patient ---
    patients: dict = store.get("patients", {})
    if patient_id not in patients:
        log.warning("[save_note] Unknown patient_id=%r", patient_id)
        return {
            "status": "error",
            "error_code": "PATIENT_NOT_FOUND",
            "message": f"No patient record found for ID: {patient_id}.",
        }

    # --- Build and persist the visit record ---
    visits: list[dict] = patients[patient_id].setdefault("visits", [])
    note_id = _make_note_id(patient_id, resolved_date, visits)

    visit_record: dict[str, Any] = {
        "note_id": note_id,
        "visit_date": resolved_date,
        "note": note.strip(),
        "icd10_suggestions": [],   # populated by agent after RAG lookup; stored later
        "signed": False,
    }
    visits.append(visit_record)

    try:
        _save_store(store)
    except OSError:
        return {
            "status": "error",
            "error_code": "STORE_WRITE_FAILURE",
            "message": "Failed to persist note; please retry.",
        }

    log.info("[save_note] Saved note_id=%r for patient_id=%r", note_id, patient_id)
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


# ---------------------------------------------------------------------------
# Tool #2 — get_patient_history  (Task #12 — placeholder, implemented next)
# ---------------------------------------------------------------------------

@tool
def get_patient_history(patient_id: str, max_visits: int = 3) -> dict[str, Any]:
    """Retrieve prior visit notes for a patient from the mock EHR.

    Use this tool when the physician asks what was noted at a previous visit,
    or when prior context is needed to draft the current note.

    Args:
        patient_id: The patient's unique ID (e.g. "PAT-001").
        max_visits: Maximum number of prior visits to return, newest-first (1–20).

    Returns:
        A dict with "status" of "success" or "error" plus a "visits" list.
    """
    log.info(
        "[get_patient_history] Called — patient_id=%r max_visits=%d",
        patient_id,
        max_visits,
    )

    # --- Validate max_visits ---
    if not (1 <= max_visits <= 20):
        return {
            "status": "error",
            "error_code": "INVALID_MAX_VISITS",
            "message": "max_visits must be between 1 and 20.",
        }

    # --- Load store ---
    try:
        store = _load_store()
    except OSError:
        return {
            "status": "error",
            "error_code": "STORE_READ_FAILURE",
            "message": "Failed to read EHR store; please retry.",
        }

    # --- Validate patient ---
    patients: dict = store.get("patients", {})
    if patient_id not in patients:
        log.warning("[get_patient_history] Unknown patient_id=%r", patient_id)
        return {
            "status": "error",
            "error_code": "PATIENT_NOT_FOUND",
            "message": f"No patient record found for ID: {patient_id}.",
        }

    # --- Fetch and format visits ---
    all_visits: list[dict] = patients[patient_id].get("visits", [])
    # Sort newest-first, then take at most max_visits
    sorted_visits = sorted(all_visits, key=lambda v: v.get("visit_date", ""), reverse=True)
    recent = sorted_visits[:max_visits]

    # Truncate note text to 1 000 chars to protect context window
    formatted = [
        {
            "note_id": v["note_id"],
            "visit_date": v["visit_date"],
            "note_summary": v["note"][:1000],
            "icd10_suggestions": v.get("icd10_suggestions", []),
        }
        for v in recent
    ]

    base: dict[str, Any] = {
        "status": "success",
        "patient_id": patient_id,
        "visit_count": len(formatted),
        "visits": formatted,
    }
    if not formatted:
        base["message"] = (
            f"No prior visit history found for patient {patient_id}. "
            "This appears to be a new patient."
        )

    log.info(
        "[get_patient_history] Returned %d visit(s) for patient_id=%r",
        len(formatted),
        patient_id,
    )
    return base


# Expose for import
EHR_TOOLS = [save_note, get_patient_history]
