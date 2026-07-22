"""
test_group_h_confidence.py — Evaluation suite for Group H (Confidence Scoring & Approval Gate) patterns.

Reference: docs/testing.md & docs/testing_examples.md (Patterns H-1 through H-6)
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from chatbot import build_chain, load_system_prompt
from config import SYSTEM_PROMPT_PATH


@pytest.fixture(scope="module")
def chain():
    system_prompt = load_system_prompt(SYSTEM_PROMPT_PATH)
    return build_chain(system_prompt)


class TestGroupH_ConfidenceScoring:
    """Group H — Confidence Scoring & Physician Approval Gate."""

    def test_H1_high_confidence_clear_transcript(self, chain):
        """Pattern H-1: High-confidence note generation for clear, complete transcript."""
        transcript = (
            "Doctor: What brings you in today?\n"
            "Patient: I've had a headache for 3 days, worse in the morning. No nausea.\n"
            "Doctor: BP is 130/85. Heart rate 72. Lungs clear."
        )
        response = chain.invoke({"user_input": transcript})
        assert "130/85" in response
        assert "SUBJECTIVE" in response or "Subjective" in response

    def test_H2_low_confidence_vague_transcript(self, chain):
        """Pattern H-2: Vague transcript flags uncertainty for physician review."""
        transcript = "Patient doesn't feel well. Maybe a headache? Or back pain, not sure."
        response = chain.invoke({"user_input": transcript}).lower()

        assert any(
            phrase in response
            for phrase in ["physician review", "insufficient", "uncertain", "for physician", "limited information"]
        )
