# PHASE 7 CLOUD MIGRATION PLAN: DEMO TO MULTI-USER SUPABASE

**Project Name:** DATA CENTRIC AGENTIC AI  
**Repository:** `https://github.com/CharanN22558/data-centric-agentic-ai`  
**Current Live Website:** `https://data-centric-agentic-ai-fcsl.onrender.com`  
**Date:** 2026-11-04  

---

## 1. Executive Summary & Root Cause of Current Render Error

### The Error
On the live Render website, users encounter:
```text
sqlite3.OperationalError: no such table: documents
```
### Root Cause
1. In `app.py`, `init_database()` was called during startup, but when running on Render's ephemeral container with `APP_MODE=demo`, the code skipped persistent table creations or created an empty SQLite database in `/tmp` without initial documents.
2. The UI pages ([`ui/documents.py`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/ui/documents.py), [`ui/chat.py`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/ui/chat.py), [`ui/modifications.py`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/ui/modifications.py), [`ui/history.py`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/ui/history.py)) directly executed `conn = get_db_connection()` and queried `SELECT ... FROM documents WHERE user_id = ?`, assuming local SQLite is present.
3. On Render, local SQLite files are wiped on container restart, and concurrent multi-user access causes database locks.

### Objective
Migrate the cloud deployment from the single-user local SQLite / demo mode to a **production-ready multi-user cloud architecture** backed by **Supabase (PostgreSQL + pgvector + Supabase Auth + Private Storage)** while preserving full backward compatibility for `APP_MODE=local`.

---

## 2. Proposed Architecture & Component Design

```
+---------------------------------------------------------------------------------+
|                                Streamlit Frontend                               |
|                     (Protected Pages, Email/Password Auth, UI)                  |
+---------------------------------------------------------------------------------+
                                       |
                     +-----------------+-----------------+
                     |                                   |
                     v                                   v
        [Cloud Mode: Supabase]                 [Local Mode: SQLite]
         - Supabase Auth (JWT)                  - Local Argon2id Auth
         - CloudSupabaseRepository              - LocalSQLiteRepository
         - PostgreSQL + RLS                     - Local SQLite (data/)
         - Storage: user-documents              - Local AES-256-GCM Files
         - pgvector (dim=384)                   - In-memory ChromaDB
```

---

## 3. Database Schema (`supabase/migrations/0001_initial_schema.sql`)

1. **`user_profiles`**: Linked to `auth.users(id)` with auto-trigger on signup.
2. **`documents`**: Tracks active documents (`id`, `user_id`, `original_filename`, `extension`, `file_size_bytes`, `sha256_hash`, `current_version_id`).
3. **`document_versions`**: Persistent version tree (`document_id`, `user_id`, `version_number`, `storage_path`, `sha256_hash`, `operation_summary`).
4. **`modification_requests`**: Complete encrypted instruction and execution history.
5. **`document_chunks`**: Embeddings stored using **`pgvector`** with `vector(384)` matching our `all-MiniLM-L6-v2` / fast fallback dimension.
6. **Row Level Security (RLS)**: Enforced with `auth.uid() = user_id` on **every single table and storage object**. No cross-user access possible.

---

## 4. Application-Level Encryption at Rest (Cloud Mode)

- Master Key: `APP_ENCRYPTION_MASTER_KEY` (stored only as Render secret).
- Per-User Key Derivation: Derived via HKDF-SHA256 from `APP_ENCRYPTION_MASTER_KEY + user_id`.
- AES-256-GCM encryption for file contents and sensitive request history before uploading to the private Supabase storage bucket `user-documents`.

---

## 5. Migration Roadmap & Deliverables

1. **`requirements.txt`**: Add `supabase>=2.34.0`, `pyjwt>=2.15.1`.
2. **Database Adapter Layer**:
   - Create `database/cloud_db.py` (Supabase client & user-scoped JWT operations).
   - Create `database/repository.py` providing unified interface (`DocumentRepository`).
3. **Authentication Layer**:
   - Update `auth/authentication.py` with Supabase sign up, sign in, email verification, session refresh, and token extraction.
4. **Storage Layer**:
   - Create `storage/supabase_storage.py` to upload, stream, and generate short-lived signed URLs for `user_id/document_id/version_id.ext.enc`.
5. **Vector RAG Layer**:
   - Update `rag/vector_store.py` to route to pgvector in cloud mode and ChromaDB in local mode.
6. **UI Integration**:
   - Update all `ui/*.py` pages to query the unified repository instead of raw SQLite queries.
7. **Automated Test Suite**:
   - `tests/test_cloud_supabase.py` verifying multi-user isolation, token validation, and encryption.
8. **Documentation & Setup Guides**:
   - `CLOUD_SETUP_GUIDE.md`, `CLOUD_SECURITY_REPORT.md`, `CLOUD_MIGRATION_REPORT.md`.
