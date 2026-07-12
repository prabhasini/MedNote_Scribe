"""
ingest.py — Ingestion pipeline for MedNote Scribe RAG database.

Reads clinical references and ICD-10 code subsets from data/corpus/,
splits them into logical chunks, embeds them using local Hugging Face
embeddings (all-MiniLM-L6-v2), and indexes them into a persistent Chroma DB.

A timestamped run log is automatically saved to logs/ingest_<timestamp>.log.

Run:
    python src/scripts/ingest.py
"""

import sys
import shutil
import logging
from datetime import datetime
from pathlib import Path

# Resolve parent directory to allow direct imports of core config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from config import CORPUS_DIR, CHROMA_DB_DIR, EMBEDDING_MODEL_NAME

# ---------------------------------------------------------------------------
# Logging setup — writes to both the terminal and a timestamped log file
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOGS_DIR / f"ingest_{timestamp}.log"

# ---------------------------------------------------------------------------
# Configure logging: suppress all library noise before basicConfig runs
# ---------------------------------------------------------------------------
# Silence the root logger first so third-party libraries that propagate to
# root (e.g. httpx, huggingface_hub) cannot emit anything below WARNING.
logging.root.setLevel(logging.WARNING)

_NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "httpcore.http11",
    "httpcore.connection",
    "sentence_transformers",
    "huggingface_hub",
    "huggingface_hub.file_download",
    "huggingface_hub.utils",
    "transformers",
    "chromadb",
    "urllib3",
    "urllib3.connectionpool",
    "langchain",
    "langchain_core",
    "langchain_chroma",
    "langchain_huggingface",
)
for _name in _NOISY_LOGGERS:
    logging.getLogger(_name).setLevel(logging.ERROR)

# Now configure our own handlers — only our logger will produce output
logging.basicConfig(
    level=logging.WARNING,   # root stays quiet
    format="%(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),          # print to terminal
        logging.FileHandler(LOG_FILE, encoding="utf-8"),  # save to file
    ],
)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)   # our logger speaks at INFO


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
        icd_count = len([d for d in documents if d.metadata["source"] == "icd10_codes.md"])
        log.info(f"Loaded {icd_count} chunks from {icd_path.name}")
    else:
        log.info(f"Warning: {icd_path} not found.")

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
        log.info(f"Loaded {guidelines_count} chunks from {guidelines_path.name}")
    else:
        log.info(f"Warning: {guidelines_path} not found.")

    return documents


def run_ingestion() -> None:
    """Run the end-to-end ingestion pipeline."""
    log.info("=" * 60)
    log.info("  Starting MedNote Scribe Ingestion Pipeline")
    log.info(f"  Run timestamp : {timestamp}")
    log.info(f"  Log file      : {LOG_FILE}")
    log.info("=" * 60)

    # 1. Reset vector database directory to ensure idempotency
    if CHROMA_DB_DIR.exists():
        log.info(f"Resetting existing vector database at: {CHROMA_DB_DIR}")
        shutil.rmtree(CHROMA_DB_DIR)

    # 2. Load and split documents
    docs = load_corpus_docs()
    if not docs:
        log.info("Error: No documents loaded. Ingestion aborted.")
        return

    # 3. Initialize embedding model
    log.info(f"Initializing embedding model: {EMBEDDING_MODEL_NAME}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # 4. Create and persist Chroma DB
    log.info(f"Indexing {len(docs)} chunks into Chroma DB at {CHROMA_DB_DIR}...")
    Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=str(CHROMA_DB_DIR)
    )

    log.info("=" * 60)
    log.info("  Ingestion Completed Successfully!")
    log.info(f"  Total Indexed Chunks : {len(docs)}")
    log.info(f"    - icd10_codes.md   : {len([d for d in docs if d.metadata['source'] == 'icd10_codes.md'])} chunks")
    log.info(f"    - clinical_guidelines.md : {len([d for d in docs if d.metadata['source'] == 'clinical_guidelines.md'])} chunks")
    log.info(f"  Log saved to: {LOG_FILE}")
    log.info("=" * 60)


if __name__ == "__main__":
    run_ingestion()
