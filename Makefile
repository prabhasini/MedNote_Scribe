.PHONY: install ingest retrieve run queries test clean

# Virtual environment paths
VENV_BIN = .venv/bin

# Install dependencies in the active virtualenv
install:
	$(VENV_BIN)/pip install -r requirements.txt

# Run the ingestion pipeline to build/index the vector store
ingest:
	$(VENV_BIN)/python src/scripts/ingest.py

# Run Task 7 retrieval test: top-3 results for the tension-headache query
retrieve:
	$(VENV_BIN)/python src/scripts/retrieve.py

# Launch the interactive CLI chatbot
run:
	$(VENV_BIN)/python src/chatbot.py

# Run the 6 sample queries and print responses
queries:
	$(VENV_BIN)/python src/scripts/run_queries.py

# Run the automated pytest suite
test:
	$(VENV_BIN)/pytest src/tests/test_chatbot.py -v

# Clean up Python cache and test artifacts
clean:
	rm -rf __pycache__ src/__pycache__ src/scripts/__pycache__ src/tests/__pycache__
	rm -rf .pytest_cache
