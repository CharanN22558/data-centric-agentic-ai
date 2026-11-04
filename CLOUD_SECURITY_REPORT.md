# CLOUD SECURITY & MULTI-TENANT ISOLATION REPORT

**Project:** DATA CENTRIC AGENTIC AI  
**Backend:** Supabase PostgreSQL + Row Level Security (RLS) + pgvector + Private Storage  
**Audit Date:** 2026-11-04  
**Audit Status:** PASSED (All 26 automated tests passing)  

---

## 1. Multi-Tenant Cryptographic & Access Isolation

### A. Bearer Token Verification (Zero Client-Side Trust)
- The frontend client is never trusted to identify users.
- In `server.py`, every endpoint requires a verified Supabase JWT Bearer token:
  ```python
  def get_current_user(authorization: Optional[str] = Header(None)):
      token = authorization.split("Bearer ")[1].strip()
      user_info = verify_jwt_token(token)
  ```
- The authenticated `user_id` (UUID) is extracted strictly from the cryptographic signature of the token verified against Supabase Auth.

### B. PostgreSQL Row Level Security (RLS)
- Enabled on every database table:
  - `user_profiles`
  - `documents`
  - `document_versions`
  - `modification_requests`
  - `document_chunks`
- Policy definition:
  ```sql
  CREATE POLICY "Users can select own documents"
      ON public.documents FOR SELECT
      USING (auth.uid() = user_id);
  ```
- This ensures that even raw SQL queries cannot accidentally read or update rows belonging to other users.

### C. Application-Level AES-256-GCM Encryption at Rest
- Server-side master key: `APP_ENCRYPTION_MASTER_KEY` (stored only as Render secret).
- Per-user encryption key derived via HKDF-SHA256 (`auth/cloud_encryption.py`):
  ```python
  user_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"supabase_user_data_key_v1", info=user_id.encode())
  ```
- File contents and sensitive modification instructions are encrypted prior to being stored in the database or private bucket.
- User B cannot decrypt User A's ciphertext even with database read access (tested in `tests/test_cloud_security.py`).

### D. Private Storage Bucket Isolation
- Bucket `user-documents` is strictly private (`public = false`).
- Storage RLS policy enforces that users can only upload, download, or delete objects within their own directory:
  ```sql
  (storage.foldername(name))[1] = auth.uid()::text
  ```

---

## 2. Test Verification Matrix (26 / 26 Passed)

| Test Module | Test Name | Target Security Function | Status |
| :--- | :--- | :--- | :--- |
| `test_cloud_security.py` | `test_user_key_derivation_isolation` | User A vs User B key differentiation | **PASSED** |
| `test_cloud_security.py` | `test_user_data_cross_access_denial` | Cross-user decryption prevention | **PASSED** |
| `test_cloud_security.py` | `test_associated_data_tampering_detection` | AAD tampering detection on doc_id/version | **PASSED** |
| `test_cloud_security.py` | `test_text_encryption_helpers` | String encryption at rest | **PASSED** |
| `test_cloud_security.py` | `test_pgvector_dimension_match` | Embedding dimension = 384 | **PASSED** |
| `test_cloud_security.py` | `test_sql_migration_file_exists` | SQL schema and RLS syntax verification | **PASSED** |
| `test_phase4_e2e.py` | *(All 7 E2E tests)* | Excel, TXT, PDF, versioning, rollback | **PASSED** |
| `test_auth.py` | `test_user_registration_and_authentication` | Local Argon2id fallback compatibility | **PASSED** |
| `test_backend_api.py` | `test_health_check_endpoint` | Backend API health check | **PASSED** |
| `test_backend_api.py` | `test_metrics_endpoint` | Backend metrics calculation | **PASSED** |
| `test_encryption.py` | *(All 2 tests)* | AES-256-GCM envelope encryption | **PASSED** |
| `test_gemini.py` | *(All 4 tests)* | Cloud boundary & privacy consent gating | **PASSED** |
| `test_modifications.py` | *(All 2 tests)* | Core modification engine | **PASSED** |
| `test_rag.py` | `test_txt_rag_pipeline` | Semantic chunking & retrieval | **PASSED** |
| `test_version_control.py` | `test_transactional_versioning_and_rollback` | Multi-version commit and rollback | **PASSED** |
