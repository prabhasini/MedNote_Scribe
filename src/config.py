"""
config.py — Centralised configuration for MedNote Scribe.

Loads environment variables from a .env file at the project root.
All other modules should import from here instead of reading os.environ directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve the project root (two levels up from src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Path to the SOAP-note system prompt
SYSTEM_PROMPT_PATH: Path = PROJECT_ROOT / "src" / "prompts" / "system_prompt.md"

# Corpus and Vector Store configurations
CORPUS_DIR: Path = PROJECT_ROOT / "data" / "corpus"
CHROMA_DB_DIR: Path = PROJECT_ROOT / "data" / "chroma_db"
EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

# WHO ICD-10 ClaML source and its normalized, deterministic JSONL derivative.
ICD10_XML_PATH: Path = CORPUS_DIR / "icd102019en.xml"
ICD10_JSONL_PATH: Path = CORPUS_DIR / "icd10_2019.jsonl"
CLINICAL_GUIDELINES_PATH: Path = CORPUS_DIR / "clinical_guidelines.md"

# Mock EHR store (local JSON file)
EHR_STORE_PATH: Path = PROJECT_ROOT / "data" / "ehr_store.json"

# Synthetic transcripts dataset path
SYNTHETIC_DATASET_PATH: Path = PROJECT_ROOT / "data" / "transcripts_synthetic" / "transcripts.jsonl"


