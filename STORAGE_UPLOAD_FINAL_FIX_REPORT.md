# STORAGE UPLOAD FINAL FIX REPORT

**Project Name:** DATA CENTRIC AGENTIC AI  
**Repository:** [https://github.com/CharanN22558/data-centric-agentic-ai](https://github.com/CharanN22558/data-centric-agentic-ai)  
**Supabase Project ID:** `ftyvumxamwdalqhwcmow`  
**Live Website URL:** [https://data-centric-agentic-ai-fcsl.onrender.com](https://data-centric-agentic-ai-fcsl.onrender.com)  
**Date:** 2026-11-04  
**Audit & Regression Test Status:** **48 / 48 TESTS PASSED (100%)**  

---

## 1. Precise Root Cause Diagnosis

When attempting to upload documents on the live cloud site, users received:
```json
{
  "statusCode": 403,
  "error": "Unauthorized",
  "message": "new row violates row-level security policy"
}
```

Detailed inspection revealed three simultaneous factors causing this error:

1. **Python Supabase SDK Storage Header Propagation:**
   In [`database/cloud_db.py`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/database/cloud_db.py), `client.storage.session.headers.update({"Authorization": ...})` updated the httpx session, but the internal `storage3` client (`client.storage._headers` and `SyncBucketProxy._headers`) was initialized during `create_client` with only the `anon` key. As a result, file upload requests sent the publishable/anon key as their bearer token (`Bearer <anon_key>`) rather than the user's JWT (`Bearer <user_jwt>`). In PostgreSQL RLS, this meant `auth.uid()` evaluated to `NULL` (unauthenticated).
2. **`upsert=true` Requirement for SELECT & UPDATE Permissions:**
   In [`database/repository.py`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/database/repository.py), `self.client.storage.from_("user-documents").upload()` had `file_options={"upsert": "true"}`. When `upsert=true` is sent to Supabase Storage, Supabase checks both `SELECT` and `UPDATE` permissions in addition to `INSERT`. Because our application uses immutable versions (`v1`, `v2`, `v3`), `upsert=false` is the correct setting.
3. **Storage RLS Evaluation in PostgreSQL:**
   In PostgreSQL, using `(SELECT auth.uid()::text)` ensures that the JWT claims sub-query is properly evaluated within the RLS security context of `storage.objects`.

---

## 2. Solutions Implemented

### A. Corrected Client Initialization in `database/cloud_db.py`
Updated `get_user_supabase_client()` to inject custom headers into `ClientOptions`:
```python
custom_headers = {
    "Authorization": f"Bearer {jwt_access_token}",
    "apikey": key,
}
options = ClientOptions(headers=custom_headers)
client = create_client(url, key, options=options)

# Explicitly ensure postgrest, storage, and underlying httpx clients have the auth header set
client.postgrest.auth(jwt_access_token)
client.storage._headers["Authorization"] = f"Bearer {jwt_access_token}"
client.storage.session.headers["Authorization"] = f"Bearer {jwt_access_token}"
```
Tested and confirmed: All requests to `client.storage.from_("user-documents").upload()` now carry the user's validated JWT.

### B. Enforced `upsert="false"` in `database/repository.py`
Updated both `upload_document()` and `create_version()`:
```python
file_options={"content-type": "application/octet-stream", "upsert": "false"}
```
Guarantees clean INSERT execution without triggering unexpected upsert conflicts.

### C. Created Dedicated Storage RLS Repair Migration
Created [`supabase/migrations/0002_repair_storage_rls.sql`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/supabase/migrations/0002_repair_storage_rls.sql) and updated [`0001_initial_schema.sql`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/supabase/migrations/0001_initial_schema.sql):
- Ensures bucket `user-documents` is strictly private (`public = false`).
- Deploys four distinct owner policies on `storage.objects`:
  - `dcai_authenticated_upload_own_files` (FOR INSERT)
  - `dcai_authenticated_read_own_files` (FOR SELECT)
  - `dcai_authenticated_update_own_files` (FOR UPDATE)
  - `dcai_authenticated_delete_own_files` (FOR DELETE)
- Each enforces:
  ```sql
  bucket_id = 'user-documents' AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
  ```

---

## 3. Automated Test Verification

All **48 / 48** tests passed:
- `tests/test_storage_rls.py`:
  - `test_storage_client_receives_user_jwt` -> **PASSED** (verifies JWT header on PostgREST, storage, and bucket clients).
  - `test_storage_repair_migration_invariants` -> **PASSED** (verifies private bucket & folder RLS policies).
  - `test_repository_uses_upsert_false` -> **PASSED** (verifies `upsert="false"` across upload methods).
- `tests/test_cloud_security.py`: All 7 passed.
- `tests/test_page_imports.py`: All 18 passed.
- `tests/test_phase4_e2e.py`: All 7 passed.
- All remaining unit tests: 13 passed.

---

## 4. Execution Step in Supabase

To apply the storage policy repair to your Supabase project (`ftyvumxamwdalqhwcmow`):
1. I opened the **Supabase SQL Editor** in your browser:
   👉 **[https://supabase.com/dashboard/project/ftyvumxamwdalqhwcmow/sql/new](https://supabase.com/dashboard/project/ftyvumxamwdalqhwcmow/sql/new)**
2. Paste the SQL from [`supabase/migrations/0002_repair_storage_rls.sql`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/supabase/migrations/0002_repair_storage_rls.sql) and click **Run**.

