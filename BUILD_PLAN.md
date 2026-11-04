# BUILD PLAN — DATA CENTRIC AGENTIC AI

## 1. Project Overview & Architecture
This academic research project develops a **Privacy-Aware Agentic AI for Retrieval-Augmented Question Answering and Verified Modification of Multi-Format Documents (TXT, XLSX, PDF)**.

### Core Principles
1. **Beginner-Friendly Code**: Modular, readable Python functions with clear comments and type hints. No over-engineered abstractions.
2. **Strict Privacy Architecture**:
   - **Local Private Mode (`APP_MODE=local`)**: Local SQLite authentication (Argon2id), local AES-256-GCM encrypted document storage, encrypted history, ephemeral in-memory vector store (ChromaDB), and explicit privacy notices before sending prompts to external Gemini LLM.
   - **Public Demonstration Mode (`APP_MODE=demo`)**: Synthetic demo files only, real uploads disabled, registration disabled, no private data accessible.
3. **Multi-Format Processing**: Full native handling of TXT, Excel (.xlsx with openpyxl/pandas), and PDF (PyMuPDF/pypdf).
4. **Agentic Workflow with LangGraph**:
   - Structured intent classifier: `QUESTION`, `MODIFICATION`, `CLARIFICATION`, `UNSUPPORTED_OPERATION`.
   - Dual execution modes: `CONFIRMATION` (default, reviews plan) vs `AUTOMATIC`.
   - Transactional document modifications with pre-validation, diff calculation, post-validation, and rollback.
5. **Modern Streamlit Multi-Page UI**: Professional dashboard, document manager, interactive chat, modification studio, history explorer, and privacy settings.

---

## 2. Directory Layout
```
DATA_CENTRIC_AGENTIC_AI/
├── app.py                      # Main Streamlit application entrypoint
├── config.py                   # Central settings, APP_MODE toggle, paths
├── requirements.txt            # Pinned dependencies
├── .env.example                # Example environment variables
├── .gitignore                  # Git privacy & security exclusions
├── render.yaml                 # Render deployment configuration (APP_MODE=demo)
├── README.md                   # Beginner-friendly setup & Windows instructions
├── RESEARCH_PAPER.md           # Research contribution, methodology & problem statement
│
├── auth/
│   ├── authentication.py       # User registration, login, session management (SQLite + Argon2id)
│   └── encryption.py           # AES-256-GCM authenticated encryption & user key derivation
│
├── agents/
│   ├── state.py                # LangGraph state schema
│   ├── router.py               # Natural language intent classification
│   └── graph.py                # LangGraph execution graph connecting QA and modification
│
├── rag/
│   ├── document_loader.py      # Format-aware content extraction (TXT, XLSX, PDF)
│   ├── chunking.py             # Context-preserving chunking (sheets, rows, pages)
│   ├── embeddings.py           # Local embedding model (SentenceTransformers / fallback)
│   ├── vector_store.py         # Ephemeral, in-memory ChromaDB manager
│   └── retrieval.py            # Individual document & workspace search pipelines
│
├── processors/
│   ├── txt_processor.py        # Text read, append, replace, delete
│   ├── excel_processor.py      # Worksheets, formulas, duplicates, sorting, column additions
│   └── pdf_processor.py        # Extract, merge, split, reorder, annotate, OCR detection
│
├── modifications/
│   ├── planner.py              # LLM / heuristic structured execution planner
│   ├── executor.py             # Predefined tool execution dispatcher
│   ├── validator.py            # Pre/post-validation and checksum verification
│   └── version_control.py      # Transaction-based versioning, snapshots & rollback
│
├── history/
│   └── history_manager.py      # Encrypted request history & audit trail
│
├── database/
│   └── db_manager.py           # SQLite metadata schema & transactions
│
├── ui/
│   ├── dashboard.py            # Metrics, recent activity, system status
│   ├── documents.py            # Document management, inspection & preview
│   ├── chat.py                 # RAG chat with source citations
│   ├── modifications.py        # Natural-language modification studio & plan confirmation
│   ├── history.py              # Traceable modification history & rollback UI
│   └── settings.py             # Dual mode toggle, Gemini API key, privacy controls
│
├── tests/
│   ├── test_auth.py            # User isolation & Argon2 verification tests
│   ├── test_encryption.py      # AES-256-GCM encryption/decryption tests
│   ├── test_rag.py             # Unified RAG retrieval & source citation tests
│   ├── test_modifications.py   # Multi-format document modification tests
│   └── test_version_control.py # Transactional versioning and rollback tests
│
├── sample_data/                # Synthetic demo documents (demo mode)
│   ├── sample_employees.xlsx
│   ├── sample_report.pdf
│   └── sample_notes.txt
│
└── data/                       # Local private storage (strictly excluded from Git)
```

---

## 3. Step-by-Step Implementation Sequence
- **Phase 1: Environment & Core Configuration**: `requirements.txt`, `.env.example`, `.gitignore`, `config.py`.
- **Phase 2: Privacy, Auth & Encryption Layer**: `encryption.py` (AES-256-GCM + Argon2id), `db_manager.py`, `authentication.py`.
- **Phase 3: Document Processors**: `txt_processor.py`, `excel_processor.py`, `pdf_processor.py`.
- **Phase 4: Unified In-Memory RAG Engine**: `document_loader.py`, `chunking.py`, `embeddings.py`, `vector_store.py`, `retrieval.py`.
- **Phase 5: Agentic Workflow & LangGraph**: `state.py`, `router.py`, `planner.py`, `executor.py`, `validator.py`, `version_control.py`, `graph.py`.
- **Phase 6: Encrypted History & Audit Manager**: `history_manager.py`.
- **Phase 7: Streamlit User Interface**: Interactive pages, dual execution modes, privacy notices.
- **Phase 8: Synthetic Demo Assets & Render Deployment**: `sample_data/`, `render.yaml`.
- **Phase 9: Comprehensive Automated Test Suite**: Run all 5 test modules using `pytest`.
- **Phase 10: Academic Deliverables & Documentation**: `README.md`, `RESEARCH_PAPER.md`.

