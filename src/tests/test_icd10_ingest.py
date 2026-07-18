"""Unit tests for the WHO ClaML ICD-10 normalization pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from config import ICD10_XML_PATH
from ingest import parse_claml, render_icd_chunk, resolve_records, write_jsonl


def test_claml_resolution_and_chunk_rendering() -> None:
    classes, source_version = parse_claml(ICD10_XML_PATH)
    records = resolve_records(classes, source_version)
    tension_headache = next(record for record in records if record["code"] == "G44.2")

    assert len(records) == 11_539
    assert source_version == "icd10_20210322"
    assert tension_headache["chapter"] == {
        "code": "VI",
        "label": "Diseases of the nervous system",
    }
    assert tension_headache["block"]["code"] == "G40-G47"
    assert tension_headache["parent"]["code"] == "G44"

    chunk = render_icd_chunk(tension_headache)
    assert "Code: G44.2" in chunk
    assert "Includes: Chronic tension-type headache" in chunk
    assert "Excludes:" not in chunk


def test_jsonl_is_one_deterministic_record_per_class(tmp_path: Path) -> None:
    classes, source_version = parse_claml(ICD10_XML_PATH)
    records = resolve_records(classes, source_version)
    output = tmp_path / "icd10.jsonl"

    write_jsonl(records, output)

    assert len(output.read_text(encoding="utf-8").splitlines()) == len(records)
