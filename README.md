# DATA CENTRIC AGENTIC AI
### Privacy-Aware Agentic AI for Retrieval-Augmented Question Answering and Verified Modification of Multi-Format Documents

---

## 1. Project Overview

**DATA CENTRIC AGENTIC AI** is a complete, beginner-friendly, and privacy-first document intelligence platform engineered for academic research and final-year capstone demonstrations.

The system solves two critical enterprise and research challenges:
1. **Intelligent Question Answering (RAG)**: Extracts, embeds, and semantically queries content across **TXT**, **Excel (.xlsx)**, and **PDF** documents with precise source citations (filename, page number, sheet name, row/cell, and excerpt).
2. **Transactional Document Modification**: Interprets natural-language instructions, builds structured execution plans, validates changes before and after execution, maintains immutable version history, supports rollback, and updates vector indexes automatically.

---

## 2. Privacy Architecture (Non-Negotiable Guarantees)

The platform supports two strictly separated modes:

### Mode 1: Local Private Mode (`APP_MODE=local`)
- **AES-256-GCM Authenticated Encryption**: All uploaded user files, backups, and modification histories are encrypted locally on disk with independent 96-bit nonces.
- **Argon2id Key Derivation**: User passwords derive a 256-bit Key Encryption Key (KEK) using 64MB memory cost to protect unique random Data Encryption Keys (DEKs).
- **In-Memory Ephemeral Vector Store**: ChromaDB vector indices reside strictly in RAM during the active session. **No plaintext document chunks or embeddings are ever written to an unencrypted database.**
- **Local SQLite Metadata**: Account records and hashes stay on your computer.
- **Explicit Cloud Consent**: Displays a privacy notice before transmitting excerpts to Google Gemini.

### Mode 2: Public Demonstration Mode (`APP_MODE=demo` / Render)
- Deploys pre-loaded synthetic demonstration files (`sample_employees.xlsx`, `sample_report.pdf`, `sample_notes.txt`).
- Real user document uploads are **disabled**.
- Private account registration is **disabled**.
- Local private data is **completely inaccessible**.

---

## 3. Technology Stack

- **UI & Dashboard**: Streamlit (Python)
- **Agent Workflow**: LangGraph, LangChain
- **LLM**: Google Gemini API (with deterministic local fallback)
- **Vector Search**: In-Memory ChromaDB
- **Embeddings**: SentenceTransformers (`all-MiniLM-L6-v2`) + fast deterministic local fallback
- **Document Processing**: `openpyxl`, `pandas`, `PyMuPDF` (fitz), `pypdf`
- **Security & Cryptography**: `cryptography` (AES-256-GCM), `argon2-cffi`
- **Database**: SQLite
- **Testing**: `pytest`

---

## 4. Quick Start Guide (Windows)

### Step 1: Clone or Navigate to the Project
```powershell
cd "C:\Users\DSP LAB\Desktop\PROJECT-1"
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
*(Optional)* Add your Google Gemini API Key in `.env` if you want generative AI responses:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
APP_MODE=local
EXECUTION_MODE=CONFIRMATION
```

### Step 3: Run the Application
Run the Streamlit app:
```powershell
streamlit run app.py
```
Open your browser at **`http://localhost:8501`**.

---

## 5. Running the Automated Test Suite

Run all automated unit and integration tests:
```powershell
python -m pytest tests -v
```

Expected output:
```
============================= test session starts =============================
tests/test_auth.py::test_user_registration_and_authentication PASSED     [ 14%]
tests/test_encryption.py::test_argon2id_derivation_and_aes_encryption PASSED [ 28%]
tests/test_encryption.py::test_document_encryption_and_integrity_tampering PASSED [ 42%]
tests/test_modifications.py::test_txt_modifications PASSED               [ 57%]
tests/test_modifications.py::test_excel_modifications PASSED             [ 71%]
tests/test_rag.py::test_txt_rag_pipeline PASSED                          [ 85%]
tests/test_version_control.py::test_transactional_versioning_and_rollback PASSED [100%]
============================== 7 passed in 2.02s ==============================
```

---

## 6. Deployment to Render (Demo Mode)

A `render.yaml` blueprint is included:
```yaml
services:
  - type: web
    name: data-centric-agentic-ai-demo
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
    envVars:
      - key: APP_MODE
        value: demo
```
In Render, `APP_MODE=demo` guarantees that:
1. Uploading private files is blocked.
2. Registration is blocked.
3. Visitors can only inspect synthetic demonstration documents.

---

## 7. Project Structure

```
DATA_CENTRIC_AGENTIC_AI/
├── app.py                      # Main Streamlit web application
├── config.py                   # Central settings & privacy modes
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment configuration
├── .gitignore                  # Excludes private data, .env, and databases
├── render.yaml                 # Render cloud deployment blueprint
├── README.md                   # Setup guide and instructions
├── RESEARCH_PAPER.md           # Research documentation for academic submission
│
├── auth/
│   ├── authentication.py       # Argon2id registration, login, and user isolation
│   └── encryption.py           # AES-256-GCM envelope encryption & key derivation
│
├── agents/
│   ├── state.py                # LangGraph state schema
│   ├── router.py               # Intent classifier (Question, Modify, Clarify, Unsupported)
│   └── graph.py                # Multi-node LangGraph execution engine
│
├── rag/
│   ├── document_loader.py      # Format-aware extractor for TXT, XLSX, and PDF
│   ├── chunking.py             # Context-preserving recursive chunker
│   ├── embeddings.py           # Local SentenceTransformers embedding provider
│   ├── vector_store.py         # Ephemeral in-memory ChromaDB manager
│   └── retrieval.py            # Individual and workspace semantic search pipeline
│
├── processors/
│   ├── txt_processor.py        # Text read, append, replace, and delete
│   ├── excel_processor.py      # Sheets, formulas, duplicate removal, sorting
│   └── pdf_processor.py        # Pages, annotations, and OCR detection
│
├── modifications/
│   ├── planner.py              # Natural-language plan generator
│   ├── executor.py             # Predefined tool execution dispatcher
│   ├── validator.py            # Pre/post-validation & checksum checks
│   └── version_control.py      # Transactional versioning & rollback
│
├── history/
│   └── history_manager.py      # Encrypted request history & audit trail
│
├── database/
│   └── db_manager.py           # SQLite tables & connections
│
├── ui/
│   ├── dashboard.py            # Metrics & recent operations
│   ├── documents.py            # File management & decrypted previews
│   ├── chat.py                 # RAG chat with source citations
│   ├── modifications.py        # Natural-language modification studio
│   ├── history.py              # Operation history & rollback controls
│   └── settings.py             # Execution modes & privacy settings
│
├── tests/                      # Automated test suite (Pytest)
└── sample_data/                # Synthetic demonstration files
```

