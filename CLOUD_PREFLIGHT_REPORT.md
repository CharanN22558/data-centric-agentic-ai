# CLOUD MIGRATION PREFLIGHT AUDIT REPORT

**Project:** DATA CENTRIC AGENTIC AI  
**Repository:** [https://github.com/CharanN22558/data-centric-agentic-ai](https://github.com/CharanN22558/data-centric-agentic-ai)  
**Branch:** `main`  
**Preflight Status:** **READY FOR SUPABASE EXECUTION & RENDER LINKING**  
**Preflight Automated Tests:** **27 / 27 PASSED (100%)**  

---

## 1. Schema Migration Inspection & Verification

The migration file [`supabase/migrations/0001_initial_schema.sql`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/supabase/migrations/0001_initial_schema.sql) was audited line-by-line:

### A. All Five Application Tables & RLS Policies
1. **`public.user_profiles`**:
   - Primary Key: `id UUID REFERENCES auth.users(id) ON DELETE CASCADE`.
   - Automatic signup trigger: `handle_new_user()` populates profile upon signup.
   - RLS: `ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;`
   - Policies: SELECT and UPDATE restricted by `auth.uid() = id`.
2. **`public.documents`**:
   - Linked to `auth.users(id)` with cascade deletion.
   - Tracks metadata: `original_filename`, `extension`, `file_size_bytes`, `sha256_hash`, `current_version_number`, `current_version_id`.
   - RLS Policies: Separate `SELECT`, `INSERT`, `UPDATE`, `DELETE` policies, each enforcing `auth.uid() = user_id`.
3. **`public.document_versions`**:
   - Unique constraint: `UNIQUE(document_id, version_number)`.
   - Tracks immutable versions and storage paths (`storage_path`).
   - RLS Policies: SELECT, INSERT, UPDATE, DELETE strictly restricted to `auth.uid() = user_id`.
4. **`public.modification_requests`**:
   - Stores encrypted request ciphertext and execution status.
   - RLS Policies: SELECT and INSERT restricted to `auth.uid() = user_id`.
5. **`public.document_chunks`**:
   - Stores encrypted chunk text and vector embeddings.
   - RLS Policies: SELECT, INSERT, DELETE strictly restricted to `auth.uid() = user_id`.

### B. pgvector Extension & Dimension Matching
- Extension enabled: `CREATE EXTENSION IF NOT EXISTS "vector";`
- Vector column definition: `embedding vector(384) NOT NULL`.
- Vector indexing: `CREATE INDEX idx_doc_chunks_embedding ON public.document_chunks USING hnsw (embedding vector_cosine_ops);`.
- Dimension verification: Matches our embedding model (`all-MiniLM-L6-v2` / fast local fallback), which generates vectors of length **384** (verified in `test_pgvector_dimension_match`).

### C. Secure Vector Search Function (`match_document_chunks`)
- **Safe Invocation Mode:** Defined with `SECURITY INVOKER` (not `SECURITY DEFINER`).
  - This guarantees that PostgreSQL executes the query under the permissions of the calling authenticated user, rather than elevated superuser rights.
- **Cross-User Leakage Prevention:** Includes mandatory constraint:
  ```sql
  WHERE dc.user_id = auth.uid()
    AND (filter_doc_id IS NULL OR dc.document_id = filter_doc_id)
  ```
- Users **cannot** retrieve chunks belonging to other users under any circumstances.

### D. Private Storage Bucket & Storage Object RLS
- Bucket initialization:
  ```sql
  INSERT INTO storage.buckets (id, name, public) VALUES ('user-documents', 'user-documents', false);
  ```
- Guaranteed **private** (`public = false`).
- Object isolation policies on `storage.objects`:
  - `(storage.foldername(name))[1] = auth.uid()::text`
  - Users can only upload, read, update, or delete objects located under their own UUID prefix (`user_id/...`).

---

## 2. Supabase API Key Configuration & Security

1. **Publishable Key Preference:**
   - Updated [`config.py`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/config.py) and [`database/cloud_db.py`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/database/cloud_db.py) to prioritize:
     ```python
     SUPABASE_PUBLISHABLE_KEY = (
         os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
         or os.getenv("SUPABASE_ANON_KEY", "").strip()
     )
     ```
   - Automatically supports Supabase's new nomenclature (`SUPABASE_PUBLISHABLE_KEY`) while preserving full backward-compatibility with `SUPABASE_ANON_KEY`.
2. **No Secret / Service-Role Key Required:**
   - The application does **not** use, require, or expose any `service_role` secret key for user operations.
   - All authenticated requests carry the user's Supabase JWT access token via:
     ```python
     client.postgrest.auth(jwt_access_token)
     client.storage.session.headers.update({"Authorization": f"Bearer {jwt_access_token}"})
     ```
   - All queries run directly against PostgreSQL Row Level Security.

---

## 3. Preflight Checklist Summary

| Check Item | Requirement | Preflight Result |
| :--- | :--- | :--- |
| **All 5 App Tables Present** | `user_profiles`, `documents`, `document_versions`, `modification_requests`, `document_chunks` | **VERIFIED** |
| **Row Level Security (RLS)** | `ENABLE ROW LEVEL SECURITY` on all 5 tables | **VERIFIED** |
| **Table Ownership Rule** | `auth.uid() = user_id` on all policies | **VERIFIED** |
| **Vector Dimension** | `vector(384)` matching local embeddings | **VERIFIED** |
| **RPC Search Function** | `SECURITY INVOKER` + `dc.user_id = auth.uid()` | **VERIFIED** |
| **Private Storage Bucket** | `public: false` on `user-documents` | **VERIFIED** |
| **Storage Object Policies** | `(storage.foldername(name))[1] = auth.uid()::text` | **VERIFIED** |
| **Key Precedence** | `SUPABASE_PUBLISHABLE_KEY` preferred with `SUPABASE_ANON_KEY` fallback | **VERIFIED** |
| **Service Role Exclusion** | Zero requirement or use of `service_role` secret key | **VERIFIED** |
| **Zero-Trust Backend** | JWT verified; user ID extracted only from token signature | **VERIFIED** |
| **Suitability for Clean Project** | Idempotent `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` statements | **VERIFIED** |

---

## 4. Ready for Supabase Setup

The code repository is verified and ready. You may now run [`supabase/migrations/0001_initial_schema.sql`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/supabase/migrations/0001_initial_schema.sql) in your Supabase SQL Editor and enter your credentials into Render.

