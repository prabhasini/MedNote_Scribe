# MedNote Scribe — Progress Tracker

> Last updated: 2026-07-11

## Status Legend
| Symbol | Meaning |
|--------|---------|
| ✅ | Complete |
| 🔄 | In Progress |
| ⬜ | Not Started |
| ⏭️ | Skipped / Deferred |

---

## Week 1: Foundations, RAG & UI
**Demo Goal:** A live Gradio chat UI where you paste a transcript and get a RAG-grounded SOAP-note draft with a cited ICD-10 suggestion.

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1 | Kickoff: assign roles, review requirements.md, agree on tech stack | ✅ | `docs/team.md` exists; stack agreed (Python 3.14, LangChain, Groq, Gradio, ChromaDB) |
| 2 | Set up git repo: .gitignore, README, branch strategy | ✅ | Repo initialised; `.gitignore` includes `.env`, `venv`, `__pycache__`; README present |
| 3 | Draft system prompt for SOAP-note generation + tone/no-diagnosis guardrails | ✅ | `src/prompts/system_prompt.md` committed; 6-case test suite passes in `src/tests/test_chatbot.py` |
| 4 | Generate synthetic dataset of doctor-patient transcripts (incl. red-flag case) | ✅ | `data/transcripts_synthetic/transcripts.jsonl` containing 6 transcripts (including 1 red-flag case) |
| 5 | Collect ICD-10 code subset and clinical docs for RAG corpus | ✅ | `data/corpus/` containing `icd10_codes.md`, `clinical_guidelines.md`, and `SOURCES.md` |
| 6 | Build ingestion pipeline: chunk, embed, load into vector store | ✅ | Ingestion pipeline script `src/ingest.py` implemented and verified |
| 7 | Implement retrieval; test against tension-headache ICD-10 query | ⬜ | — |
| 8 | Wire minimal prototype: transcript → SOAP note (no tools/guardrails) | ⬜ | — |
| 9 | Build Gradio chat UI and deploy locally with shareable link | ⬜ | — |

---

## Week 2: Tools, MCP & Memory
**Demo Goal:** Gradio UI saves a note through the mock EHR tool and recalls prior-visit context.

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 10 | Design tool specs: `save_note` and `get_patient_history` | ✅ | `docs/tools.md` committed with both signatures, input/output tables, and error cases |
| 11 | Implement mock EHR API and `save_note` tool | ✅ | `src/tools/ehr_tools.py` + `data/ehr_store.json`; 7-case smoke test passes |
| 12 | Implement `get_patient_history` tool and wire into agent | ✅ | Implemented in `src/tools/ehr_tools.py`; all cases tested (known patient, new patient, unknown patient) |
| 13 | Set up MCP to expose both EHR tools; test full round-trip | ✅ | `src/mcp_server.py` (FastMCP server) + `src/agent.py` (ReAct + MCP client); `make mcp-roundtrip` passes both tool calls |
| 14 | Design memory schema: per-patient visit history and prior note drafts | ⬜ | — |
| 15 | Integrate memory so agent recalls prior-visit context across sessions | ⬜ | — |
| 16 | Wire tools and memory into Gradio UI via expandable "agent trace" panel | ⬜ | — |

---

## Week 3: Guardrails & Caching
**Demo Goal:** Red-flag escalation guardrail triggered live; visible cache-hit badge on repeated ICD-10 lookup.

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 17 | Codify guardrail rules: no diagnosis, red-flag detection, no dosage suggestions | ⬜ | — |
| 18 | Implement guardrail checks on generated notes before returning to user | ⬜ | — |
| 19 | Test guardrails against chest-pain and diagnosis-request queries | ⬜ | — |
| 20 | Implement caching for repeated ICD-10 lookups | ⬜ | — |
| 21 | Measure cache hit rate and latency improvement | ⬜ | — |
| 22 | Run all 6 sample queries end-to-end; fix bugs | ⬜ | — |
| 23 | Surface guardrail status and cache hit/miss as visible badges in Gradio UI | ⬜ | — |

---

## Week 4: Observability, Evals & Demo Readiness
**Demo Goal:** Full live walkthrough with observability dashboard, eval score before/after fixes, guardrail refusal on demand.

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 24 | Instrument observability: log every retrieval, tool call, guardrail trigger with trace IDs | ⬜ | — |
| 25 | Build eval harness from expected-answers table with pass/fail scoring | ⬜ | — |
| 26 | Run eval suite against synthetic transcripts; record baseline scores | ⬜ | — |
| 27 | Error analysis: categorize failures, find root causes, pick top 3 fixes | ⬜ | — |
| 28 | Apply top fixes and re-run eval suite; record improvement | ⬜ | — |
| 29 | Build dashboard: latency, hallucination-flag rate, guardrail trigger count | ⬜ | — |
| 30 | Handle edge cases: empty transcript, ambiguous symptoms, EHR tool failure | ⬜ | — |
| 31 | Prepare demo script: persona, 2-3 live queries, guardrail refusal, scorecard | ⬜ | — |
| 32 | Final rehearsal, deploy demo build, record backup video | ⬜ | — |

---

## Stretch Goals
| Goal | Status |
|------|--------|
| Baseline comparison (vanilla LLM vs. RAG/tools/guardrails) | ⬜ |
| Red-team the agent (try to force diagnosis/dosage assertion) | ⬜ |
| Voice-input mode (speech-to-text for live dictation) | ⬜ |
| Latency/cost budget (< 3s and < $0.01/note) | ⬜ |

---

## Notes
- `.env` is in `.gitignore`; contains `GROQ_API_KEY` and optionally `GROQ_MODEL`
- Default model: `llama-3.3-70b-versatile` (overridable via `GROQ_MODEL` env var)
- Python environment: `pyenv` virtualenv `mednote-scribe` (Python 3.14.6)
- All demo data is synthetic — no real PHI at any stage
