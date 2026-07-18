"""Build the local RAG corpus and Chroma index.

ICD-10 is ingested from the WHO ClaML XML file in two passes.  The first pass
collects the flat ``Class`` records; the second resolves each record's
chapter/block/parent context and cross references.  The normalized JSONL file
is retained as the deterministic source from which ICD chunks are built.

Run with ``python src/scripts/ingest.py``.
"""

import argparse
import json
import logging
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from config import (
    CHROMA_DB_DIR,
    CLINICAL_GUIDELINES_PATH,
    EMBEDDING_MODEL_NAME,
    ICD10_JSONL_PATH,
    ICD10_XML_PATH,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOGS_DIR / f"ingest_{timestamp}.log"

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
for logger_name in ("chromadb", "httpx", "huggingface_hub", "langchain", "transformers"):
    logging.getLogger(logger_name).setLevel(logging.ERROR)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

LONG_RUBRIC_CHARACTERS = 1_200
SPACE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Collapse ClaML formatting whitespace while retaining its text content."""
    return SPACE.sub(" ", value).strip()


def label_text(element: ET.Element) -> str:
    """Read a Label, including nested Fragment/Para/Reference text."""
    return normalize_text(" ".join(element.itertext()))


def english_labels(rubric: ET.Element) -> list[str]:
    """Return English labels, falling back to an unlabelled/default Label."""
    labels = rubric.findall("Label")
    english = [
        label_text(label)
        for label in labels
        if label.get("{http://www.w3.org/XML/1998/namespace}lang") in (None, "en")
    ]
    return [text for text in english if text]


def parse_claml(xml_path: Path) -> tuple[list[dict[str, Any]], str]:
    """Pass 1: parse flat Class nodes and extract their local ClaML fields."""
    root = ET.parse(xml_path).getroot()
    identifier = root.find("Identifier")
    source_version = identifier.get("uid", "unknown") if identifier is not None else "unknown"
    classes: list[dict[str, Any]] = []

    for class_element in root.findall("Class"):
        rubrics: dict[str, list[str]] = {}
        references: list[str] = []
        for rubric in class_element.findall("Rubric"):
            kind = rubric.get("kind", "text")
            rubrics.setdefault(kind, []).extend(english_labels(rubric))
            references.extend(
                reference.get("code") for reference in rubric.findall(".//Reference") if reference.get("code")
            )

        preferred = (rubrics.get("preferred") or rubrics.get("preferredLong") or [""])[0]
        notes = []
        for kind in ("note", "coding-hint", "introduction", "footnote", "text", "modifierlink"):
            notes.extend(rubrics.get(kind, []))

        classes.append(
            {
                "code": class_element.get("code", ""),
                "kind": class_element.get("kind", "category"),
                "super_code": next((node.get("code") for node in class_element.findall("SuperClass") if node.get("code")), None),
                "child_codes": [node.get("code") for node in class_element.findall("SubClass") if node.get("code")],
                "preferred": preferred,
                "inclusions": rubrics.get("inclusion", []),
                "exclusions": rubrics.get("exclusion", []),
                "notes": notes,
                "definition": "\n".join(rubrics.get("definition", [])) or None,
                "reference_codes": list(dict.fromkeys(references)),
            }
        )
    return classes, source_version


def resolve_records(classes: list[dict[str, Any]], source_version: str) -> list[dict[str, Any]]:
    """Pass 2: attach ancestor context and resolve referenced code labels."""
    by_code = {record["code"]: record for record in classes}

    def ancestor_of_kind(record: dict[str, Any], kind: str) -> dict[str, str] | None:
        current = record
        visited = {record["code"]}
        while current.get("super_code"):
            parent_code = current["super_code"]
            if parent_code in visited or parent_code not in by_code:
                return None
            visited.add(parent_code)
            current = by_code[parent_code]
            if current["kind"] == kind:
                return {"code": current["code"], "label": current["preferred"]}
        return None

    resolved: list[dict[str, Any]] = []
    for raw in classes:
        direct_parent = by_code.get(raw["super_code"]) if raw.get("super_code") else None
        parent = (
            {"code": direct_parent["code"], "label": direct_parent["preferred"]}
            if direct_parent and direct_parent["kind"] == "category"
            else None
        )
        resolved.append(
            {
                "code": raw["code"],
                "kind": raw["kind"],
                "chapter": ancestor_of_kind(raw, "chapter"),
                "block": ancestor_of_kind(raw, "block"),
                "parent": parent,
                "preferred": raw["preferred"],
                "inclusions": raw["inclusions"],
                "exclusions": raw["exclusions"],
                "notes": raw["notes"],
                "definition": raw["definition"],
                "cross_references": [
                    {"code": code, "label": by_code.get(code, {}).get("preferred", "")}
                    for code in raw["reference_codes"]
                ],
                "children": [
                    {"code": code, "label": by_code.get(code, {}).get("preferred", "")}
                    for code in raw["child_codes"]
                    if code in by_code
                ],
                "source_version": source_version,
            }
        )
    return resolved


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    """Write a stable, one-record-per-line re-embedding source file."""
    with output_path.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def render_icd_chunk(record: dict[str, Any]) -> str:
    """Render the semantic unit embedded for one ICD Class record."""
    lines = [f"Code: {record['code']}"]
    if record["parent"]:
        lines.append(f"Category: {record['parent']['label']} ({record['parent']['code']})")
    if record["block"]:
        lines.append(f"Block: {record['block']['label']} ({record['block']['code']})")
    if record["chapter"]:
        lines.append(f"Chapter: {record['chapter']['label']} ({record['chapter']['code']})")
    if record["preferred"]:
        lines.extend(["", record["preferred"]])
    if record["inclusions"]:
        lines.extend(["", f"Includes: {'; '.join(record['inclusions'])}"])
    # Exclusions deliberately remain payload-only: they should not pull the
    # vector toward diagnoses that this code rules out.
    for heading, value in (("Definition", record["definition"]), ("Notes", " ".join(record["notes"]))):
        if value and len(value) <= LONG_RUBRIC_CHARACTERS:
            lines.extend(["", f"{heading}: {value}"])
    return "\n".join(lines)


def chroma_metadata(record: dict[str, Any], *, chunk_type: str = "class") -> dict[str, Any]:
    """Flatten record data to Chroma-supported scalar metadata values."""
    return {
        "source": ICD10_XML_PATH.name,
        "type": "icd10",
        "chunk_type": chunk_type,
        "code": record["code"],
        "root_code": record["code"],
        "kind": record["kind"],
        "preferred": record["preferred"],
        "chapter_code": (record["chapter"] or {}).get("code", ""),
        "chapter_label": (record["chapter"] or {}).get("label", ""),
        "block_code": (record["block"] or {}).get("code", ""),
        "block_label": (record["block"] or {}).get("label", ""),
        "parent_code": (record["parent"] or {}).get("code", ""),
        "has_children": bool(record["children"]),
        "source_version": record["source_version"],
        "inclusions_json": json.dumps(record["inclusions"], ensure_ascii=False),
        "exclusions_json": json.dumps(record["exclusions"], ensure_ascii=False),
        "cross_references_json": json.dumps(record["cross_references"], ensure_ascii=False),
    }


def load_icd10_documents() -> list[Document]:
    if not ICD10_XML_PATH.exists():
        raise FileNotFoundError(f"ICD-10 XML source was not found: {ICD10_XML_PATH}")
    raw_classes, source_version = parse_claml(ICD10_XML_PATH)
    records = resolve_records(raw_classes, source_version)
    write_jsonl(records, ICD10_JSONL_PATH)
    documents = [
        Document(page_content=render_icd_chunk(record), metadata=chroma_metadata(record, chunk_type="class"), id=record["code"])
        for record in records
    ]
    for record in records:
        for rubric_kind, text in (("definition", record["definition"]), ("note", " ".join(record["notes"]))):
            if text and len(text) > LONG_RUBRIC_CHARACTERS:
                documents.append(
                    Document(
                        page_content=f"Code: {record['code']}\n{rubric_kind.title()}: {text}",
                        metadata=chroma_metadata(record, chunk_type=rubric_kind),
                        id=f"{record['code']}#{rubric_kind}-1",
                    )
                )
    log.info("Parsed %d ICD-10 classes; wrote %s", len(records), ICD10_JSONL_PATH.name)
    return documents


def load_guideline_documents() -> list[Document]:
    if not CLINICAL_GUIDELINES_PATH.exists():
        log.warning("Clinical guidelines source was not found: %s", CLINICAL_GUIDELINES_PATH)
        return []
    return [
        Document(
            page_content=chunk.strip(),
            metadata={"source": CLINICAL_GUIDELINES_PATH.name, "type": "guideline"},
            id=f"guideline-{index}",
        )
        for index, chunk in enumerate(CLINICAL_GUIDELINES_PATH.read_text(encoding="utf-8").split("---"))
        if chunk.strip() and "##" in chunk
    ]


def load_corpus_docs() -> list[Document]:
    """Build all indexable documents; XML is the sole ICD-10 source."""
    return load_icd10_documents() + load_guideline_documents()


def previous_jsonl_records() -> dict[str, dict[str, Any]]:
    """Load the prior normalized corpus for code-level change detection."""
    if not ICD10_JSONL_PATH.exists():
        return {}
    return {
        record["code"]: record
        for line in ICD10_JSONL_PATH.read_text(encoding="utf-8").splitlines()
        if (record := json.loads(line))
    }


def run_ingestion(*, full_rebuild: bool = False) -> None:
    log.info("Starting ICD-10 ingestion; log: %s", LOG_FILE)
    previous_records = previous_jsonl_records()
    docs = load_corpus_docs()
    if not docs:
        raise RuntimeError("No documents were loaded; ingestion aborted.")
    icd_docs = [document for document in docs if document.metadata["type"] == "icd10"]
    guideline_docs = [document for document in docs if document.metadata["type"] == "guideline"]
    current_records = {
        json.loads(line)["code"]: json.loads(line)
        for line in ICD10_JSONL_PATH.read_text(encoding="utf-8").splitlines()
    }

    if full_rebuild or not CHROMA_DB_DIR.exists() or not previous_records:
        if CHROMA_DB_DIR.exists():
            log.info("Removing existing Chroma index at: %s", CHROMA_DB_DIR)
            shutil.rmtree(CHROMA_DB_DIR)
        log.info("Embedding and indexing %d chunks with %s", len(docs), EMBEDDING_MODEL_NAME)
        Chroma.from_documents(
            documents=docs,
            embedding=HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME),
            persist_directory=str(CHROMA_DB_DIR),
            ids=[document.id for document in docs],
        )
        log.info("Completed full rebuild: %d ICD-10 chunks, %d guideline chunks.", len(icd_docs), len(guideline_docs))
        return

    changed_codes = {
        code for code, record in current_records.items() if previous_records.get(code) != record
    }
    removed_codes = set(previous_records) - set(current_records)
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    vectorstore = Chroma(persist_directory=str(CHROMA_DB_DIR), embedding_function=embeddings)
    for code in changed_codes | removed_codes:
        vectorstore.delete(where={"root_code": code})
    changed_docs = [document for document in icd_docs if document.metadata["root_code"] in changed_codes]
    if changed_docs:
        vectorstore.add_documents(changed_docs, ids=[document.id for document in changed_docs])
    # Guidelines are small and independently sourced, so replacing their few
    # chunks is simpler and avoids treating them as ICD code records.
    vectorstore.delete(where={"source": CLINICAL_GUIDELINES_PATH.name})
    if guideline_docs:
        vectorstore.add_documents(guideline_docs, ids=[document.id for document in guideline_docs])
    log.info(
        "Completed incremental update: %d changed, %d removed ICD-10 codes; %d guideline chunks refreshed.",
        len(changed_codes), len(removed_codes), len(guideline_docs),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest WHO ICD-10 ClaML into Chroma.")
    parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="discard the current Chroma collection and rebuild every chunk",
    )
    run_ingestion(full_rebuild=parser.parse_args().full_rebuild)
