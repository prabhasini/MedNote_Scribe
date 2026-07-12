# MedNote Scribe

MedNote Scribe is an AI-powered clinical documentation assistant designed to convert doctor-patient consultation transcripts into structured, billing-ready **SOAP (Subjective, Objective, Assessment, Plan)** notes.

The primary user of this tool is **Dr. Ananya Rao**, a general physician aiming to reduce after-hours clinical documentation time from hours to under a minute per patient encounter.

---

## Key Features (Implemented)
- **Zero-Shot SOAP Extraction**: Converts conversational or narrative doctor-patient transcripts into standard SOAP sections.
- **Tone & Clinical Safety Guardrails**:
  - Never asserts a diagnosis; all clinical assessments are framed as differentials and suggestions flagged `"For physician review: ..."` and pending confirmation.
  - Detects high-risk red-flag symptoms (like chest pain radiating to the left arm) and prepends an urgent escalation warning before compiling routine notes.
  - Refuses to suggest or adjust medication dosages unless explicitly declared in the transcript.
- **RAG Reference Corpus**: Includes a subset of ICD-10-CM codes and clinical guidelines under `data/corpus/`.
- **RAG Ingestion Pipeline**: Chunk, embed (using `all-MiniLM-L6-v2` locally), and index corpus files into a local persistent `Chroma` database under `data/chroma_db/`.
- **RAG Retrieval Validator**: A script (`src/scripts/retrieve.py`) verifying top-3 similarity search matches for ICD-10 lookup queries.
- **Gradio Web Interface**: Clean, side-by-side layout allowing Dr. Rao to paste transcripts and review generated SOAP notes with one-click example inputs.
- **Automated Integration Test Suite**: 6-case pytest coverage verifying chatbot compliance with requirements.

---

## Directory Structure
```
MedNote_Scribe/
├── Makefile                    # Developer tool command shortcuts
├── requirements.txt            # Project python dependencies
├── data/
│   ├── corpus/                 # RAG corpus source files (ICD-10 subset, guidelines)
│   ├── chroma_db/              # Persistent Chroma database files
│   └── transcripts_synthetic/  # SOAP-grounded evaluation transcripts CSV dataset
├── docs/
│   ├── requirements.md         # Project requirements and queries
│   ├── tasks.md                # 4-week task checklist
│   └── progress.md             # Project implementation progress tracking
└── src/
    ├── config.py               # Centralized configuration (loads .env)
    ├── chatbot.py              # CLI interactive chatbot app (with RAG pipeline)
    ├── app.py                  # Gradio Web UI interface app
    ├── prompts/
    │   └── system_prompt.md    # SOAP prompt markdown definition
    ├── scripts/
    │   ├── ingest.py           # Corpus indexing pipeline
    │   ├── retrieve.py         # RAG similarity retrieval validator
    │   ├── run_queries.py      # Batch sample queries runner script
    │   └── generate_transcripts.py # Synthetic transcripts csv builder script
    └── tests/
        ├── __init__.py
        └── test_chatbot.py     # Pytest test suite covering the 6 requirements queries
```

---

## Installation & Setup

1. **Environment Initialization**:
   Ensure you have a Python environment set up (e.g., using `pyenv` and `virtualenv` with Python 3.14.6):
   ```bash
   pyenv virtualenv 3.14.6 mednote-scribe
   pyenv local mednote-scribe
   ```

2. **Environment Variables**:
   Create a `.env` file at the root of the project:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   # Optional: Override the model used (defaults to llama-3.3-70b-versatile)
   # GROQ_MODEL=llama-3.3-70b-versatile
   ```

3. **Install Dependencies**:
   Install the required Python packages:
   ```bash
   make install
   ```

---

## Commands and Usage

We provide a `Makefile` to simplify common commands. Ensure your virtual environment is active before running these:

### 1. Build the Vector Store (Ingestion)
Runs the ingestion script to split the corpus docs, compute local Hugging Face embeddings, and store them in the Chroma vector database:
```bash
make ingest
```

### 2. Validate Retrieval (Task 7)
Runs similarity search testing against a sample query to verify that target code context is retrieved in the top-3 results:
```bash
make retrieve
```

### 3. Run the Interactive Chatbot (Task 8 CLI)
Launches the CLI-based chatbot where you can interactively paste transcripts or ask clinical questions:
```bash
make run
```

### 4. Launch the Gradio Web UI (Task 9 App)
Launches the web browser user interface containing sample transcripts and side-by-side rendering outputs:
```bash
make ui
```

### 5. Run Sample Queries
Runs all 6 sample queries specified in `requirements.md` in batch mode and displays the queries and formatted model responses:
```bash
make queries
```

### 6. Run Tests
Runs the automated integration test suite across all 6 scenario categories:
```bash
make test
```

### 7. Clean Up
Deletes python cache and test artifact files:
```bash
make clean
```
