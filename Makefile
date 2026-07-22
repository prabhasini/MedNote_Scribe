.PHONY: install lock ingest retrieve run queries ui mcp-server test test-unit test-integration test-patterns test-tools mcp-roundtrip test-group-a test-group-b test-group-c test-group-d test-group-e test-group-f test-group-g test-group-h clean

# ---------------------------------------------------------------------------
# Setup & Dependencies
# ---------------------------------------------------------------------------

# Install all dependencies (creates/updates .venv automatically)
install:
	uv sync --all-extras

# Update uv.lock from pyproject.toml
lock:
	uv lock

# ---------------------------------------------------------------------------
# Execution & Application Targets
# ---------------------------------------------------------------------------

# Run the ingestion pipeline to build/index the vector store
ingest:
	uv run python src/scripts/ingest.py

# Run retrieval test: top-3 results for tension-headache query
retrieve:
	uv run python src/scripts/retrieve.py

# Launch interactive CLI chatbot
run:
	uv run python src/chatbot.py

# Launch Gradio web UI
ui:
	uv run python src/app.py

# Run all 6 sample queries end-to-end and print responses
queries:
	uv run python src/scripts/run_queries.py

# Start MCP EHR server manually (stdio — for debugging)
mcp-server:
	uv run python src/mcp_server.py

# ---------------------------------------------------------------------------
# Full Test Suites (Layer-Based)
# ---------------------------------------------------------------------------

# Run ALL automated pytest suites across unit, integration, and pattern layers
test:
	uv run pytest tests/ -v

# Run unit test layer only
test-unit:
	uv run pytest tests/unit/ -v

# Run integration test layer only
test-integration:
	uv run pytest tests/integration/ -v

# Run pattern evaluation suites only (matching docs/testing.md)
test-patterns:
	uv run pytest tests/patterns/ -v

# ---------------------------------------------------------------------------
# Group-Specific Pattern Targets (matching docs/testing.md Groups A–H)
# ---------------------------------------------------------------------------

# Group A: SOAP Note Generation Patterns (A-1 through A-8)
test-group-a:
	uv run pytest tests/patterns/test_group_a_soap_gen.py -v

# Group B: ICD-10 RAG Retrieval Patterns (B-1 through B-5)
test-group-b:
	uv run pytest tests/integration/test_group_b_rag_retrieval.py -v

# Group C: EHR Tool Call Patterns (C-1 through C-9)
test-group-c:
	uv run pytest tests/unit/test_group_c_ehr_tools.py -v

# Group D: MCP Agent ↔ FastMCP Round-Trip Patterns (D-1 through D-3)
test-group-d:
	uv run pytest tests/integration/test_group_d_mcp_roundtrip.py -v

# Group E: Memory & Session Continuity Patterns (E-1 through E-4)
test-group-e:
	uv run pytest tests/patterns/test_group_e_memory.py -v

# Group F: Guardrails & Refusal Patterns (F-1 through F-10)
test-group-f:
	uv run pytest tests/patterns/test_group_f_guardrails.py -v

# Group G: Edge Cases & Performance Patterns (G-1 through G-12)
test-group-g:
	uv run pytest tests/patterns/test_group_g_edge_cases.py -v

# Group H: Confidence Scoring & Physician Approval Gate Patterns (H-1 through H-6)
test-group-h:
	uv run pytest tests/patterns/test_group_h_confidence.py -v

# ---------------------------------------------------------------------------
# Aliases & Cleanup
# ---------------------------------------------------------------------------

# Alias for Group C
test-tools: test-group-c

# Alias for Group D
mcp-roundtrip: test-group-d

# Clean up Python cache and test artifacts
clean:
	rm -rf __pycache__ src/__pycache__ src/scripts/__pycache__ tests/__pycache__ tests/*/__pycache__
	rm -rf .pytest_cache