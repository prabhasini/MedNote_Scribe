"""
ingest.py — Ingestion pipeline for MedNote Scribe RAG database.

Reads clinical references and ICD-10 code subsets from data/corpus/,
splits them into logical chunks, embeds them using local Hugging Face
embeddings (all-MiniLM-L6-v2), and indexes them into a persistent Chroma DB.

Run:
    python src/scripts/ingest.py
"""

import sys
import shutil
from pathlib import Path

# Resolve parent directory to allow direct imports of core config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from config import CORPUS_DIR, CHROMA_DB_DIR, EMBEDDING_MODEL_NAME


def clean_chunk(text: str) -> str:
    """Strip leading/trailing whitespace and clean up newlines."""
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def load_corpus_docs() -> list[Document]:
    """Load reference documents from the corpus directory and split by '---'."""
    documents = []

    # 1. Load ICD-10 codes
    icd_path = CORPUS_DIR / "icd10_codes.md"
    if icd_path.exists():
        content = icd_path.read_text(encoding="utf-8")
        chunks = content.split("---")
        for chunk in chunks:
            cleaned = clean_chunk(chunk)
            # Skip the main header or empty blocks
            if cleaned and "##" in cleaned:
                documents.append(
                    Document(
                        page_content=cleaned,
                        metadata={
                            "source": "icd10_codes.md",
                            "type": "icd10"
                        }
                    )
                )
        print(f"Loaded {len([d for d in documents if d.metadata['source'] == 'icd10_codes.md'])} chunks from {icd_path.name}")
    else:
        print(f"Warning: {icd_path} not found.")

    # 2. Load Clinical Guidelines
    guidelines_path = CORPUS_DIR / "clinical_guidelines.md"
    if guidelines_path.exists():
        content = guidelines_path.read_text(encoding="utf-8")
        chunks = content.split("---")
        guidelines_count = 0
        for chunk in chunks:
            cleaned = clean_chunk(chunk)
            # Skip introduction or empty blocks
            if cleaned and "##" in cleaned:
                documents.append(
                    Document(
                        page_content=cleaned,
                        metadata={
                            "source": "clinical_guidelines.md",
                            "type": "guideline"
                        }
                    )
                )
                guidelines_count += 1
        print(f"Loaded {guidelines_count} chunks from {guidelines_path.name}")
    else:
        print(f"Warning: {guidelines_path} not found.")

    return documents


def run_ingestion() -> None:
    """Run the end-to-end ingestion pipeline."""
    print("=" * 60)
    print("  Starting MedNote Scribe Ingestion Pipeline")
    print("=" * 60)

    # 1. Reset vector database directory to ensure idempotency
    if CHROMA_DB_DIR.exists():
        print(f"Resetting existing vector database at: {CHROMA_DB_DIR}")
        shutil.rmtree(CHROMA_DB_DIR)

    # 2. Load and split documents
    docs = load_corpus_docs()
    if not docs:
        print("Error: No documents loaded. Ingestion aborted.")
        return

    # 3. Initialize embedding model
    print(f"Initializing embedding model: {EMBEDDING_MODEL_NAME}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # 4. Create and persist Chroma DB
    print(f"Indexing {len(docs)} chunks into Chroma DB at {CHROMA_DB_DIR}...")
    db = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=str(CHROMA_DB_DIR)
    )

    print("=" * 60)
    print("  Ingestion Completed Successfully!")
    print(f"  Total Indexed Chunks: {len(docs)}")
    print("=" * 60)


if __name__ == "__main__":
    run_ingestion()
