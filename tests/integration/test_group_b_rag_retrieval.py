"""
test_group_b_rag_retrieval.py — Integration test suite for Group B (ICD-10 RAG Retrieval) patterns.

Reference: docs/testing.md & docs/testing_examples.md (Patterns B-1 through B-5)
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from chatbot import build_chain, load_system_prompt, retrieve_context
from config import SYSTEM_PROMPT_PATH


@pytest.fixture(scope="module")
def chain():
    system_prompt = load_system_prompt(SYSTEM_PROMPT_PATH)
    return build_chain(system_prompt)


class TestGroupB_RAGRetrieval:
    """Group B — RAG Retrieval Patterns (B-1 through B-5)."""

    def test_B1_exact_code_lookup(self, chain):
        """Pattern B-1: Direct query for recurrent tension headache ICD-10 code."""
        query = "What ICD-10 code fits 'recurrent tension headache'?"
        response = chain.invoke({"user_input": query}).lower()

        assert "g44.2" in response
        assert any(
            phrase in response
            for phrase in ["suggestion", "physician confirmation", "for physician"]
        )

    def test_B2_synonym_paraphrase_query(self, chain):
        """Pattern B-2: Synonym query for high blood pressure -> I10."""
        query = "What code should I use for a patient with high blood pressure?"
        response = chain.invoke({"user_input": query}).lower()

        assert "i10" in response or "hypertension" in response

    def test_B3_direct_vector_retrieval(self):
        """Pattern B-3: Direct vector store similarity search returns relevant chunks."""
        context = retrieve_context("tension headache")
        assert "G44.2" in context or "headache" in context.lower()
        assert "Context Chunk" in context
