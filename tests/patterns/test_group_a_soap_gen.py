"""
test_group_a_soap_gen.py — End-to-end evaluation suite for Group A (SOAP Note Generation) patterns.

Reference: docs/testing.md & docs/testing_examples.md (Patterns A-1 through A-8)
"""

import re
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


def ask(chain, user_input: str) -> str:
    return chain.invoke({"user_input": user_input})


class TestGroupA_SOAPGeneration:
    """Group A — SOAP Note Generation Patterns."""

    def test_A1_happy_path_simple_transcript(self, chain):
        """Pattern A-1: Simple transcript with headache + BP reading."""
        transcript = "Patient reports headache for 3 days, worse in the morning, no nausea. BP 130/85."
        response = ask(chain, transcript)
        
        assert "SUBJECTIVE" in response or "Subjective" in response
        assert "OBJECTIVE" in response or "Objective" in response
        assert "ASSESSMENT" in response or "Assessment" in response
        assert "PLAN" in response or "Plan" in response
        assert "130/85" in response
        assert any(
            phrase in response.lower()
            for phrase in ["physician review", "physician confirmation", "for physician"]
        )

    def test_A2_multi_complaint_transcript(self, chain):
        """Pattern A-2: Multiple complaints (headache, knee pain, fatigue)."""
        transcript = (
            "Doctor: What brings you in today?\n"
            "Patient: I've had a headache for about 4 days, and my right knee has been aching "
            "since I went hiking last weekend. I've also been feeling really tired lately.\n"
            "Doctor: Let me check your BP... it's 122/78. Heart rate 72."
        )
        response = ask(chain, transcript)
        res_lower = response.lower()

        assert "headache" in res_lower
        assert "knee" in res_lower
        assert "122/78" in response

    def test_A5_no_objective_data(self, chain):
        """Pattern A-5: Symptoms only, no vitals recorded."""
        transcript = (
            "Patient: I've been having lower back pain for about a week. It's worse when I sit "
            "for long periods. No trauma, no radiation down the legs.\n"
            "Doctor: Okay, I'll review that. We'll discuss options."
        )
        response = ask(chain, transcript)
        res_lower = response.lower()

        assert "objective" in res_lower
        assert any(
            phrase in res_lower
            for phrase in ["no objective data", "not recorded", "none documented", "no vitals", "not specified"]
        )

    def test_A7_specialty_specific_terminology(self, chain):
        """Pattern A-7: Clinical terminology preservation."""
        transcript = (
            "Doctor: What happened to your ankle?\n"
            "Patient: I rolled it outward playing basketball yesterday.\n"
            "Doctor: Swelling and tenderness over anterior talofibular ligament. BP 118/76."
        )
        response = ask(chain, transcript)

        assert "anterior talofibular ligament" in response or "talofibular" in response
        assert "118/76" in response
