# MedNote Scribe — Tool Specifications

> **Task #10 · Week 2** | Agreed tool contracts for the mock EHR API integration.

---

## Overview

Both tools wrap a **local JSON-file mock EHR store** (`data/ehr_store.json`).
No real patient data is used at any stage — all identifiers and records are synthetic.

Each tool is exposed to the LangChain agent as a `@tool`-decorated function, and later
surfaced over MCP in Task #13.

---

## 1. `save_note`

Saves a finished SOAP note for a given patient visit and returns a stable note ID that
can be cited for audit purposes.

### Signature

```python
def save_note(patient_id: str, note: str, visit_date: str | None = None) -> dict:
    ...
```

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `patient_id` | `str` | ✅ | Unique patient identifier (e.g. `"PAT-001"`). Must match an existing record in the EHR store. |
| `note` | `str` | ✅ | Full SOAP note text to persist. Must be non-empty. |
| `visit_date` | `str \| None` | ⬜ | ISO-8601 date string (e.g. `"2026-07-19"`). Defaults to today's date (UTC) if omitted. |

### Output (success)

```json
{
  "status": "success",
  "note_id": "NOTE-PAT001-20260719-001",
  "patient_id": "PAT-001",
  "visit_date": "2026-07-19",
  "message": "Note saved successfully. Awaiting physician sign-off."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `"success"` | Constant on the success path. |
| `note_id` | `str` | Stable, unique ID for the saved note. Format: `NOTE-<patient_id>-<YYYYMMDD>-<seq>`. |
| `patient_id` | `str` | Echo of the input `patient_id`. |
| `visit_date` | `str` | Resolved visit date (ISO-8601). |
| `message` | `str` | Human-readable confirmation; always mentions physician sign-off requirement. |

### Error Cases

| Scenario | `error_code` | `message` |
|----------|--------------|-----------|
| `patient_id` not found in EHR store | `"PATIENT_NOT_FOUND"` | `"No patient record found for ID: PAT-999."` |
| `note` is empty or whitespace-only | `"EMPTY_NOTE"` | `"Cannot save an empty note."` |
| `visit_date` is not a valid ISO-8601 date | `"INVALID_DATE"` | `"visit_date must be ISO-8601 (YYYY-MM-DD)."` |
| EHR store file I/O failure | `"STORE_WRITE_FAILURE"` | `"Failed to persist note; please retry."` |

**Error response shape:**

```json
{
  "status": "error",
  "error_code": "PATIENT_NOT_FOUND",
  "message": "No patient record found for ID: PAT-999."
}
```

### Example Calls

```python
# Success
save_note("PAT-001", "S: Headache 3 days...\nO: BP 130/85...\nA: ...\nP: ...")
# → {"status": "success", "note_id": "NOTE-PAT001-20260719-001", ...}

# Missing-patient error
save_note("PAT-999", "S: ...")
# → {"status": "error", "error_code": "PATIENT_NOT_FOUND", ...}

# Empty note error
save_note("PAT-001", "   ")
# → {"status": "error", "error_code": "EMPTY_NOTE", ...}
```

### Guardrail Note

> The tool returns `"Awaiting physician sign-off."` in every success message.
> The agent **must not** tell the user the note is "final" or "signed" — only the
> physician can do that (see `requirements.md` §5).

---

## 2. `get_patient_history`

Retrieves the prior-visit note history for a patient so the agent can surface relevant
context when drafting a new note.

### Signature

```python
def get_patient_history(patient_id: str, max_visits: int = 3) -> dict:
    ...
```

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `patient_id` | `str` | ✅ | Unique patient identifier (e.g. `"PAT-001"`). |
| `max_visits` | `int` | ⬜ | Maximum number of prior visits to return, sorted newest-first. Defaults to `3`. Valid range: 1–20. |

### Output (success — patient has history)

```json
{
  "status": "success",
  "patient_id": "PAT-001",
  "visit_count": 2,
  "visits": [
    {
      "note_id": "NOTE-PAT001-20260710-001",
      "visit_date": "2026-07-10",
      "note_summary": "S: Recurring tension headache...\nO: BP 128/82...",
      "icd10_suggestions": ["G44.2"]
    },
    {
      "note_id": "NOTE-PAT001-20260601-001",
      "visit_date": "2026-06-01",
      "note_summary": "S: Fatigue, mild sore throat...\nO: Temp 37.8 C...",
      "icd10_suggestions": ["J06.9"]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `"success"` | Constant on the success path. |
| `patient_id` | `str` | Echo of the input `patient_id`. |
| `visit_count` | `int` | Total number of visits returned (≤ `max_visits`). |
| `visits` | `list[dict]` | Ordered list of prior visit records, newest-first. |
| `visits[].note_id` | `str` | Stable note ID. |
| `visits[].visit_date` | `str` | ISO-8601 date of the visit. |
| `visits[].note_summary` | `str` | Full SOAP note text (truncated to 1 000 chars for context-window efficiency). |
| `visits[].icd10_suggestions` | `list[str]` | ICD-10 codes suggested during that visit. |

### Output (success — new patient, no history)

```json
{
  "status": "success",
  "patient_id": "PAT-042",
  "visit_count": 0,
  "visits": [],
  "message": "No prior visit history found for patient PAT-042. This appears to be a new patient."
}
```

### Error Cases

| Scenario | `error_code` | `message` |
|----------|--------------|-----------|
| `patient_id` not found in EHR store | `"PATIENT_NOT_FOUND"` | `"No patient record found for ID: PAT-999."` |
| `max_visits` out of range (< 1 or > 20) | `"INVALID_MAX_VISITS"` | `"max_visits must be between 1 and 20."` |
| EHR store file I/O failure | `"STORE_READ_FAILURE"` | `"Failed to read EHR store; please retry."` |

**Error response shape:**

```json
{
  "status": "error",
  "error_code": "PATIENT_NOT_FOUND",
  "message": "No patient record found for ID: PAT-999."
}
```

### Example Calls

```python
# Known patient with prior visits
get_patient_history("PAT-001")
# → {"status": "success", "visit_count": 2, "visits": [...]}

# New patient — no history (graceful, not an error)
get_patient_history("PAT-042")
# → {"status": "success", "visit_count": 0, "visits": [], "message": "...new patient."}

# Missing patient ID
get_patient_history("PAT-999")
# → {"status": "error", "error_code": "PATIENT_NOT_FOUND", ...}

# Limit to 1 most recent visit
get_patient_history("PAT-001", max_visits=1)
# → {"status": "success", "visit_count": 1, "visits": [<most recent>]}
```

---

## EHR Store Schema (`data/ehr_store.json`)

The mock store is a plain JSON file written and read by both tools.

```json
{
  "patients": {
    "PAT-001": {
      "name": "Synthetic Patient A",
      "dob": "1980-03-15",
      "visits": [
        {
          "note_id": "NOTE-PAT001-20260710-001",
          "visit_date": "2026-07-10",
          "note": "S: Recurring tension headache...\nO: BP 128/82...\nA: ...\nP: ...",
          "icd10_suggestions": ["G44.2"],
          "signed": false
        }
      ]
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `patients` | Top-level map keyed by `patient_id`. |
| `patients[id].visits` | Chronological list of visit records for this patient. |
| `visits[].note_id` | Globally unique note identifier. |
| `visits[].signed` | `false` until physician explicitly signs off (out of scope for these tools). |

---

## Constraints & Guardrails

1. **No real PHI** — all `patient_id` values in the demo store are synthetic (`PAT-001` through `PAT-006`).
2. **Sign-off is out of scope** — `signed: false` is always the initial state set by these tools; a separate physician action flips it.
3. **ICD-10 codes are suggestions** — stored as-is from the agent output; the tool never validates or fabricates codes.
4. **Observability hook (Task #24)** — both tools will emit a structured log entry on every call for future trace-ID instrumentation.

---

*Spec agreed for Task #10. Implementation begins in Task #11 (`save_note`) and Task #12 (`get_patient_history`).*
