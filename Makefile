.PHONY: install compile ingest retrieve run queries test test-tools mcp-server mcp-roundtrip clean ui

# Virtual environment paths
VENV_BIN = .venv/bin

# Install locked dependencies into the virtual environment
install:
	$(VENV_BIN)/pip install -r requirements.txt

# Compile dependency lockfile (requirements.txt) from pyproject.toml
compile:
	@if command -v uv >/dev/null 2>&1; then \
		uv pip compile pyproject.toml --extra dev -o requirements.txt; \
	else \
		$(VENV_BIN)/pip install -q pip-tools; \
		$(VENV_BIN)/pip-compile pyproject.toml --extra dev -o requirements.txt; \
	fi


# Run the ingestion pipeline to build/index the vector store
ingest:
	$(VENV_BIN)/python src/scripts/ingest.py

# Run Task 7 retrieval test: top-3 results for the tension-headache query
retrieve:
	$(VENV_BIN)/python src/scripts/retrieve.py

# Launch the interactive CLI chatbot
run:
	$(VENV_BIN)/python src/chatbot.py

# Launch the Gradio web UI
ui:
	$(VENV_BIN)/python src/app.py

# Run the 6 sample queries and print responses
queries:
	$(VENV_BIN)/python src/scripts/run_queries.py

# Run the automated pytest suite
test:
	$(VENV_BIN)/pytest src/tests/test_chatbot.py -v

# Run the EHR tools smoke test (save_note + get_patient_history)
test-tools:
	$(VENV_BIN)/python src/tests/test_ehr_tools.py

# Start the MCP EHR server manually (stdio — for debugging)
mcp-server:
	$(VENV_BIN)/python src/mcp_server.py

# Run the Task #13 MCP round-trip integration test
mcp-roundtrip:
	$(VENV_BIN)/python src/scripts/test_mcp_roundtrip.py

# Clean up Python cache and test artifacts
clean:
	rm -rf __pycache__ src/__pycache__ src/scripts/__pycache__ src/tests/__pycache__
	rm -rf .pytest_cache

