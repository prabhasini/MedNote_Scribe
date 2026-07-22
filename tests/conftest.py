"""
conftest.py — Shared pytest fixtures for MedNote Scribe test suites.
"""

import json
import sys
from pathlib import Path
import pytest

# Ensure src/ is on the Python path for all tests
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chatbot import build_chain, load_system_prompt
from config import SYSTEM_PROMPT_PATH, SYNTHETIC_DATASET_PATH


@pytest.fixture(scope="module")
def chain():
    """Build the LangChain LCEL chain once for a test module."""
    system_prompt = load_system_prompt(SYSTEM_PROMPT_PATH)
    return build_chain(system_prompt)


@pytest.fixture(scope="session")
def synthetic_transcripts():
    """Load the synthetic dataset records."""
    if not SYNTHETIC_DATASET_PATH.exists():
        return []
    records = []
    with open(SYNTHETIC_DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


@pytest.fixture
def mock_ehr_store(tmp_path):
    """Create a temporary mock EHR store JSON for isolated test calls."""
    store_file = tmp_path / "ehr_store.json"
    initial_data = {
        "patients": {
            "PAT-001": {
                "name": "Synthetic Patient A",
                "dob": "1980-03-15",
                "visits": [
                    {
                        "note_id": "NOTE-PAT001-20260710-001",
                        "visit_date": "2026-07-10",
                        "note": "S: Recurring tension headache...\nO: BP 128/82...\nA: ...\nP: ...",
                        "icd10_suggestions": ["G44.2"],
                        "signed": False
                    }
                ]
            }
        }
    }
    store_file.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")
    return store_file
