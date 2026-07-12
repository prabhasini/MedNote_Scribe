"""
retrieve.py — Task 7: Implement retrieval and test against the tension-headache query.

Loads the persisted Chroma vector store and runs a similarity search for:
  "What ICD-10 code fits recurrent tension headache?"

Prints the top-3 retrieved chunks with their relevance scores and a
correct/incorrect judgment, and saves the full output to a timestamped log file.

Run:
    python src/scripts/retrieve.py
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Resolve parent directory to allow direct imports of core config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from config import CHROMA_DB_DIR, EMBEDDING_MODEL_NAME

# ---------------------------------------------------------------------------
# Logging setup — writes to both terminal and a timestamped log file
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOGS_DIR / f"retrieval_{timestamp}.log"

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
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)   # our logger speaks at INFO

# ---------------------------------------------------------------------------
# The Task 7 test query (from requirements.md Sample Query #2)
# ---------------------------------------------------------------------------
TEST_QUERY = "What ICD-10 code fits recurrent tension headache?"

# Codes considered correct for this query (G44.2 family)
CORRECT_CODE_PREFIXES = ("G44.2", "G44.209", "G44.219", "G44.229")

TOP_K = 3  # number of chunks to retrieve


def run_retrieval_test() -> None:
    """Load the vector store and run the test query, logging results."""
    log.info("=" * 70)
    log.info("  MedNote Scribe — Task 7: Retrieval Test")
    log.info(f"  Run timestamp : {timestamp}")
    log.info(f"  Log file      : {LOG_FILE}")
    log.info("=" * 70)

    # 1. Verify the vector store exists
    if not CHROMA_DB_DIR.exists():
        log.info(
            f"\n[ERROR] Chroma DB not found at: {CHROMA_DB_DIR}\n"
            "  Run the ingestion pipeline first:  .venv/bin/python src/scripts/ingest.py"
        )
        return

    # 2. Load embedding model (same one used during ingestion)
    log.info(f"\nLoading embedding model: {EMBEDDING_MODEL_NAME}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # 3. Connect to the persisted Chroma DB
    log.info(f"Connecting to vector store at: {CHROMA_DB_DIR}\n")
    vectorstore = Chroma(
        persist_directory=str(CHROMA_DB_DIR),
        embedding_function=embeddings,
    )

    # 4. Run similarity search with relevance scores
    log.info(f"Query: \"{TEST_QUERY}\"")
    log.info("-" * 70)

    results = vectorstore.similarity_search_with_relevance_scores(
        TEST_QUERY, k=TOP_K
    )

    # 5. Print each retrieved chunk with judgment
    all_correct = False
    for rank, (doc, score) in enumerate(results, start=1):
        source = doc.metadata.get("source", "unknown")
        doc_type = doc.metadata.get("type", "unknown")
        content_preview = doc.page_content[:300].replace("\n", " ")

        # Determine if this chunk contains a correct ICD-10 code
        is_correct = any(code in doc.page_content for code in CORRECT_CODE_PREFIXES)
        judgment = "✅ CORRECT — contains a G44.2-family code" if is_correct else "❌ Does not contain the target G44.2 code"
        if is_correct:
            all_correct = True

        log.info(f"\nRank #{rank}  |  Score: {score:.4f}  |  Source: {source}  |  Type: {doc_type}")
        log.info(f"Judgment : {judgment}")
        log.info(f"Content  : {content_preview}{'...' if len(doc.page_content) > 300 else ''}")
        log.info("-" * 70)

    # 6. Overall result
    log.info("\n" + "=" * 70)
    if all_correct:
        log.info("  RESULT: ✅ PASS — A G44.2-family chunk appeared in the top-3 results.")
    else:
        log.info("  RESULT: ❌ FAIL — No G44.2-family chunk found in the top-3 results.")
        log.info("  Action : Review corpus content or re-run ingestion pipeline.")
    log.info(f"  Log saved to: {LOG_FILE}")
    log.info("=" * 70)


if __name__ == "__main__":
    run_retrieval_test()
