.PHONY: install lock ingest retrieve run queries test test-tools mcp-server mcp-roundtrip clean ui

# Install all dependencies (creates/updates .venv automatically)
install:
	uv sync --all-extras

# Update uv.lock from pyproject.toml (replaces requirements.txt compilation)
lock:
	uv lock


# Run the ingestion pipeline to build/index the vector store
ingest:
	uv run python src/scripts/ingest.py

# Run Task 7 retrieval test: top-3 results for the tension-headache query
retrieve:
	uv run python src/scripts/retrieve.py

# Launch the interactive CLI chatbot
run:
	uv run python src/chatbot.py

# Launch the Gradio web UI
ui:
	uv run python src/app.py

# Run the 6 sample queries and print responses
queries:
	uv run python src/scripts/run_queries.py

# Run the automated pytest suite
test:
	uv run pytest src/tests/test_chatbot.py -v

# Run the EHR tools smoke test (save_note + get_patient_history)
test-tools:
	uv run python src/tests/test_ehr_tools.py

# Start the MCP EHR server manually (stdio — for debugging)
mcp-server:
	uv run python src/mcp_server.py

# Run the Task #13 MCP round-trip integration test
mcp-roundtrip:
	uv run python src/scripts/test_mcp_roundtrip.py

# Clean up Python cache and test artifacts
clean:
	rm -rf __pycache__ src/__pycache__ src/scripts/__pycache__ src/tests/__pycache__
	rm -rf .pytest_cache