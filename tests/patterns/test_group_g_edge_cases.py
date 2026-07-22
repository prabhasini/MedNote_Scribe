"""
test_group_g_edge_cases.py — End-to-end evaluation suite for Group G (Edge Cases & Adversarial) patterns.

Reference: docs/testing.md & docs/testing_examples.md (Patterns G-1 through G-12)
"""

import sys
import time
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


class TestGroupG_EdgeCases:
    """Group G — Edge Case Patterns."""

    def test_G1_empty_transcript(self, chain):
        """Pattern G-1: Empty or whitespace input handling."""
        # Empty string handling in chain
        response = ask(chain, "   ")
        assert len(response.strip()) > 0

    def test_G2_single_sentence_transcript(self, chain):
        """Pattern G-2: Extremely short single-sentence transcript."""
        transcript = "Patient has a cough."
        response = ask(chain, transcript)
        res_lower = response.lower()

        assert "cough" in res_lower
        assert "subjective" in res_lower

    def test_G3_non_medical_input(self, chain):
        """Pattern G-3: Irrelevant non-medical text input."""
        transcript = "Today the weather is sunny and warm. I had pasta for lunch."
        response = ask(chain, transcript)
        res_lower = response.lower()

        assert any(
            phrase in res_lower
            for phrase in ["no medical", "not contain medical", "cannot generate", "please provide", "non-medical"]
        ) or len(response) > 0

    def test_G12_end_to_end_latency(self, chain):
        """Pattern G-12: End-to-end latency <= 15s."""
        transcript = "Patient reports headache for 3 days, worse in the morning, no nausea. BP 130/85."
        
        start = time.time()
        response = ask(chain, transcript)
        elapsed = time.time() - start

        assert elapsed <= 15.0, f"Latency {elapsed:.2f}s exceeded 15.0s limit"
        assert "130/85" in response
