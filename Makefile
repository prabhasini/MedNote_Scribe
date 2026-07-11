.PHONY: install ingest run queries test clean

# Install dependencies in the active virtualenv
install:
	pip install -r requirements.txt

# Run the ingestion pipeline to build/index the vector store
ingest:
	python src/scripts/ingest.py

# Launch the interactive CLI chatbot
run:
	python src/chatbot.py

# Run the 6 sample queries and print responses
queries:
	python src/scripts/run_queries.py

# Run the automated pytest suite
test:
	pytest src/tests/test_chatbot.py -v

# Clean up Python cache and test artifacts
clean:
	rm -rf __pycache__ src/__pycache__ src/scripts/__pycache__ src/tests/__pycache__
	rm -rf .pytest_cache
