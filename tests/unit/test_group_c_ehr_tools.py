"""
test_group_c_ehr_tools.py — Unit test suite for Group C (EHR Tool Calls) patterns.

Reference: docs/testing.md & docs/testing_examples.md (Patterns C-1 through C-9)
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from tools.ehr_tools import get_patient_history, save_note


class TestGroupC_EHRTools:
    """Group C — EHR Tool Call Unit Tests (C-1 through C-9)."""

    def test_C1_save_note_happy_path(self):
        """Pattern C-1: Successful note save for known patient."""
        r = save_note.invoke({
            "patient_id": "PAT-001",
            "note": "S: Headache 3 days...\nO: BP 130/85...\nA: Tension headache...\nP: Rest and fluids"
        })
        assert r["status"] == "success"
        assert "note_id" in r
        assert r["note_id"].startswith("NOTE-PAT001-")
        assert "Awaiting physician sign-off" in r["message"]

    def test_C2_save_note_unknown_patient(self):
        """Pattern C-2: Save note for non-existent patient ID."""
        r = save_note.invoke({
            "patient_id": "PAT-999",
            "note": "S: Test note..."
        })
        assert r["status"] == "error"
        assert r["error_code"] == "PATIENT_NOT_FOUND"

    def test_C3_save_note_empty_note(self):
        """Pattern C-3: Save empty or whitespace-only note."""
        r = save_note.invoke({
            "patient_id": "PAT-001",
            "note": "   "
        })
        assert r["status"] == "error"
        assert r["error_code"] == "EMPTY_NOTE"

    def test_C4_save_note_invalid_date(self):
        """Pattern C-4: Save note with invalid date string."""
        r = save_note.invoke({
            "patient_id": "PAT-001",
            "note": "S: Valid note text",
            "visit_date": "not-a-date"
        })
        assert r["status"] == "error"
        assert r["error_code"] == "INVALID_DATE"

    def test_C5_get_patient_history_known_patient(self):
        """Pattern C-5: Retrieve prior-visit history for known patient."""
        r = get_patient_history.invoke({"patient_id": "PAT-001"})
        assert r["status"] == "success"
        assert r["visit_count"] >= 1
        assert len(r["visits"]) >= 1
        assert "note_id" in r["visits"][0]

    def test_C6_get_patient_history_new_patient(self):
        """Pattern C-6: Retrieve history for patient with zero visits."""
        r = get_patient_history.invoke({"patient_id": "PAT-003"})
        assert r["status"] == "success"
        assert r["visit_count"] == 0
        assert r["visits"] == []
        assert "new patient" in r["message"].lower()

    def test_C7_get_patient_history_unknown_id(self):
        """Pattern C-7: Retrieve history for unknown patient ID."""
        r = get_patient_history.invoke({"patient_id": "PAT-999"})
        assert r["status"] == "error"
        assert r["error_code"] == "PATIENT_NOT_FOUND"

    def test_C8_get_patient_history_max_visits_boundary(self):
        """Pattern C-8: max_visits parameter range validation."""
        r_valid = get_patient_history.invoke({"patient_id": "PAT-001", "max_visits": 1})
        assert r_valid["status"] == "success"
        assert len(r_valid["visits"]) <= 1

        r_zero = get_patient_history.invoke({"patient_id": "PAT-001", "max_visits": 0})
        assert r_zero["status"] == "error"
        assert r_zero["error_code"] == "INVALID_MAX_VISITS"

        r_high = get_patient_history.invoke({"patient_id": "PAT-001", "max_visits": 25})
        assert r_high["status"] == "error"
        assert r_high["error_code"] == "INVALID_MAX_VISITS"
