# MedNote Scribe

MedNote Scribe is an AI-powered clinical documentation assistant designed to convert doctor-patient consultation transcripts into structured, billing-ready **SOAP (Subjective, Objective, Assessment, Plan)** notes.

The primary user of this tool is **Dr. Ananya Rao**, a general physician aiming to reduce after-hours clinical documentation time from hours to under a minute per patient encounter.

---

## Key Features (Implemented)

### Week 1: Foundations & RAG
- **Zero-Shot SOAP Extraction**: Converts conversational or narrative doctor-patient transcripts into standard bulleted SOAP sections.
- **Tone & Clinical Safety Guardrails**:
  - Never asserts a diagnosis; all clinical assessments are framed as differentials and suggestions flagged `"For physician review: ..."` and pending confirmation.
  - Detects high-risk red-flag symptoms (like chest pain radiating to the left arm) and prepends an urgent escalation warning before compiling routine notes.
  - Refuses to suggest or adjust medication dosages unless explicitly declared in the transcript.
- **RAG Reference Corpus**: Includes a subset of ICD-10-CM codes and clinical guidelines under `data/corpus/`.
- **RAG Ingestion Pipeline**: Chunk, embed (using `all-MiniLM-L6-v2` locally), and index corpus files into a local persistent `Chroma` database under `data/chroma_db/`.
- **RAG Retrieval Validator**: A script (`src/scripts/retrieve.py`) verifying top-3 similarity search matches for ICD-10 lookup queries.

### Week 2: Tools, MCP & Memory
- **Tool Specifications & Implementation (`save_note` & `get_patient_history`)**: Mock EHR integration (`data/ehr_store.json`) allowing note persistence and chronological patient history lookup.
- **Model Context Protocol (MCP) Integration**: FastMCP server (`src/mcp_server.py`) exposing EHR tools over stdio transport to the ReAct agent (`src/agent.py`).
- **Memory Architecture & Schemas (`docs/memory_design.md`)**:
  - **Short-Term Memory**: In-memory `LangGraph` checkpointer (`MemorySaver`) maintaining multi-turn interaction thread context.
  - **Long-Term Memory**: Persistent patient-scoped EHR store (`ehr_store.json`) for cross-session visit recall.
  - **Cognitive Taxonomy**: Categorized into Episodic (Patient History), Semantic (RAG Reference), and Procedural (Rules & Safety).
  - **Confidence Scoring**: Formatted relevance scores in retrieval tool output to gate information confidence.
- **Modern Gradio Web Interface with Agent Trace**:
  - High-contrast Slate/Dark aesthetic with crisp white text readability and vibrant orange primary action buttons.
  - Expandable **Agent Trace & Memory Recall** panel detailing real-time tool calls (`save_note`, `get_patient_history`, `retrieve_icd10_context`), arguments, and tool outputs.
  - Dynamic status badges indicating when RAG retrieval or EHR store access occurred.

---

## Directory Structure
```
MedNote_Scribe/
├── Makefile                    # Developer tool command shortcuts
├── pyproject.toml              # Project dependencies and configuration
├── uv.lock                     # Locked dependency resolution file
├── data/
│   ├── corpus/                 # RAG corpus source files (ICD-10 subset, guidelines)
│   ├── chroma_db/              # Persistent Chroma database files
│   ├── ehr_store.json          # Mock EHR patient store database
│   └── transcripts_synthetic/  # SOAP-grounded evaluation transcripts JSONL dataset
├── docs/
│   ├── requirements.md         # Project requirements and queries
│   ├── tasks.md                # 4-week task checklist
│   ├── progress.md             # Project implementation progress tracking
│   ├── tools.md                # Tool specifications (save_note, get_patient_history)
│   └── memory_design.md        # Memory architecture, schemas & confidence scores
└── src/
    ├── config.py               # Centralized configuration (loads .env)
    ├── chatbot.py              # CLI interactive chatbot app (with RAG pipeline)
    ├── agent.py                # LangGraph ReAct Agent with MCP client & MemorySaver
    ├── mcp_server.py           # FastMCP server exposing save_note & get_patient_history
    ├── app.py                  # Gradio Web UI interface app with Agent Trace Panel
    ├── prompts/
    │   └── system_prompt.md    # SOAP prompt markdown definition with tool rules
    ├── scripts/
    │   ├── ingest.py           # Corpus indexing pipeline
    │   ├── retrieve.py         # RAG similarity retrieval validator
    │   ├── run_queries.py      # Batch sample queries runner script
    │   ├── test_mcp_roundtrip.py # MCP agent roundtrip integration test
    │   └── generate_transcripts.py # Synthetic transcripts jsonl builder script
    ├── tools/
    │   └── ehr_tools.py        # EHR tool implementations (save_note, get_patient_history)
    └── tests/
        ├── __init__.py
        ├── test_chatbot.py     # Integration test suite covering requirement queries
        ├── test_ehr_tools.py   # EHR tools smoke test
        └── test_memory.py      # Cross-session memory recall integration test
```

---

## Installation & Setup

1. **Prerequisites**:
   Install [`uv`](https://github.com/astral-sh/uv) (fast Python package installer & manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Environment Variables**:
   Create a `.env` file at the root of the project:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   # Optional: Override the model (defaults to llama-3.3-70b-versatile)
   # GROQ_MODEL=llama-3.3-70b-versatile
   ```

3. **Install Dependencies**:
   Install all project dependencies (creates/updates the virtual environment `.venv` automatically):
   ```bash
   make install
   # or directly:
   uv sync --all-extras
   ```

4. **Dependency Lock (Developers)**:
   If you modify `pyproject.toml`, update `uv.lock` by running:
   ```bash
   make lock
   # or directly:
   uv lock
   ```

---

## Commands and Usage

We provide a `Makefile` using `uv` to simplify common commands.

### 1. Build the Vector Store (Ingestion)
Normalizes the WHO ICD-10 ClaML XML into `data/corpus/icd10_2019.jsonl`, builds one
structured retrieval chunk per ICD class, computes local Hugging Face embeddings, and
stores them in the Chroma vector database. Later runs update only changed ICD records:
```bash
make ingest
```

Use a full reset only when needed:
```bash
uv run python src/scripts/ingest.py --full-rebuild
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

### 7. Run EHR Tools & MCP Tests
Run the local EHR tools (save_note, get_patient_history) smoke test:
```bash
make test-tools
```

Or run the end-to-end MCP round-trip integration test (which runs the FastMCP server as a subprocess and tests tool execution by the ReAct agent):
```bash
make mcp-roundtrip
```

### 8. Clean Up
Deletes python cache and test artifact files:
```bash
make clean
```
