"""
Unified Document Repository Adapter.

Provides a single interface for document CRUD, versions, and history:
- When IS_CLOUD_MODE: Uses CloudSupabaseRepository (PostgreSQL + RLS + Supabase Storage)
- When IS_LOCAL_MODE: Uses LocalSQLiteRepository (local app_metadata.db + local data/ directory)
"""

import os
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from config import IS_CLOUD_MODE, IS_LOCAL_MODE, IS_DEMO_MODE, SAMPLE_DATA_DIR
from database.cloud_db import get_user_supabase_client, get_anon_supabase_client
from database.db_manager import get_db_connection
from auth.cloud_encryption import encrypt_data_bytes, decrypt_data_bytes, encrypt_text, decrypt_text
from modifications.version_control import save_initial_document as local_save_initial
from modifications.version_control import read_decrypted_document as local_read_decrypted
from modifications.version_control import commit_new_version as local_create_version
from modifications.version_control import rollback_document_version as local_rollback


# =====================================================================
# 1. Cloud Supabase Repository Implementation
# =====================================================================

class CloudSupabaseRepository:
    def __init__(self, user_id: str, jwt_token: str):
        self.user_id = str(user_id)
        self.jwt_token = jwt_token
        self.client = get_user_supabase_client(jwt_token)

    def list_documents(self) -> List[Dict[str, Any]]:
        """Lists documents owned by the authenticated user enforcing RLS."""
        if not self.client:
            return []
        try:
            resp = self.client.table("documents").select("*").order("created_at", desc=True).execute()
            docs = []
            for r in resp.data:
                docs.append({
                    "doc_id": r["id"],
                    "original_filename": r["original_filename"],
                    "extension": r["extension"],
                    "current_version": r["current_version_number"],
                    "current_version_id": r.get("current_version_id"),
                    "file_size_bytes": r["file_size_bytes"],
                    "sha256_hash": r["sha256_hash"],
                    "uploaded_at": r["created_at"],
                })
            return docs
        except Exception as e:
            print(f"[REPO] list_documents error: {e}")
            return []

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves single document metadata owned by user."""
        if not self.client:
            return None
        try:
            resp = self.client.table("documents").select("*").eq("id", doc_id).execute()
            if resp.data:
                r = resp.data[0]
                return {
                    "doc_id": r["id"],
                    "original_filename": r["original_filename"],
                    "extension": r["extension"],
                    "current_version": r["current_version_number"],
                    "current_version_id": r.get("current_version_id"),
                    "file_size_bytes": r["file_size_bytes"],
                    "sha256_hash": r["sha256_hash"],
                    "uploaded_at": r["created_at"],
                }
        except Exception as e:
            print(f"[REPO] get_document error: {e}")
        return None

    def upload_document(self, filename: str, content_bytes: bytes) -> Tuple[bool, str, Optional[str]]:
        """
        Encrypts document bytes with AES-256-GCM and stores in private Supabase Storage,
        creating records in documents and document_versions tables.
        """
        if not self.client:
            return False, "Database client is not available.", None

        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        file_size = len(content_bytes)
        ext = os.path.splitext(filename)[1].lower()

        # 1. Application-level encryption at rest
        aad = f"{self.user_id}:{doc_id}:1"
        encrypted_bytes = encrypt_data_bytes(content_bytes, self.user_id, associated_data=aad)

        # 2. Upload to private Supabase Storage bucket 'user-documents'
        storage_path = f"{self.user_id}/{doc_id}/v1{ext}.enc"
        try:
            self.client.storage.from_("user-documents").upload(
                path=storage_path,
                file=encrypted_bytes,
                file_options={"content-type": "application/octet-stream", "upsert": "true"}
            )
        except Exception as e:
            return False, f"Storage upload failed: {e}", None

        # 3. Create document record
        try:
            doc_data = {
                "id": doc_id,
                "user_id": self.user_id,
                "original_filename": filename,
                "extension": ext,
                "file_size_bytes": file_size,
                "sha256_hash": sha256,
                "current_version_number": 1,
            }
            self.client.table("documents").insert(doc_data).execute()

            # 4. Create document_version record
            version_data = {
                "id": version_id,
                "user_id": self.user_id,
                "document_id": doc_id,
                "version_number": 1,
                "storage_path": storage_path,
                "sha256_hash": sha256,
                "operation_summary": "Initial upload",
            }
            self.client.table("document_versions").insert(version_data).execute()

            # 5. Link current version id on document
            self.client.table("documents").update({"current_version_id": version_id}).eq("id", doc_id).execute()

            return True, f"Successfully uploaded and encrypted {filename} (v1).", doc_id
        except Exception as e:
            return False, f"Database record creation failed: {e}", None

    def read_document_bytes(self, doc_id: str, version_number: Optional[int] = None) -> Optional[bytes]:
        """Downloads and decrypts document version from Supabase Storage."""
        if not self.client:
            return None
        try:
            doc = self.get_document(doc_id)
            if not doc:
                return None
            target_version = version_number or doc["current_version"]

            # Query version storage path
            v_resp = self.client.table("document_versions").select("*").eq("document_id", doc_id).eq("version_number", target_version).execute()
            if not v_resp.data:
                return None
            storage_path = v_resp.data[0]["storage_path"]

            # Download encrypted bytes from private bucket
            encrypted_payload = self.client.storage.from_("user-documents").download(storage_path)

            # Decrypt
            aad = f"{self.user_id}:{doc_id}:{target_version}"
            return decrypt_data_bytes(encrypted_payload, self.user_id, associated_data=aad)
        except Exception as e:
            print(f"[REPO] read_document_bytes error: {e}")
            return None

    def create_version(self, doc_id: str, new_content: bytes, operation_summary: str) -> Tuple[bool, str, int]:
        """Creates a new version record and uploads encrypted file bytes."""
        if not self.client:
            return False, "Database client unavailable", 0
        try:
            doc = self.get_document(doc_id)
            if not doc:
                return False, "Target document not found.", 0

            new_v_num = doc["current_version"] + 1
            version_id = str(uuid.uuid4())
            ext = doc["extension"]
            sha256 = hashlib.sha256(new_content).hexdigest()

            # Encrypt
            aad = f"{self.user_id}:{doc_id}:{new_v_num}"
            encrypted_bytes = encrypt_data_bytes(new_content, self.user_id, associated_data=aad)

            # Upload
            storage_path = f"{self.user_id}/{doc_id}/v{new_v_num}{ext}.enc"
            self.client.storage.from_("user-documents").upload(
                path=storage_path,
                file=encrypted_bytes,
                file_options={"content-type": "application/octet-stream", "upsert": "true"}
            )

            # Insert Version record
            v_data = {
                "id": version_id,
                "user_id": self.user_id,
                "document_id": doc_id,
                "version_number": new_v_num,
                "storage_path": storage_path,
                "sha256_hash": sha256,
                "operation_summary": operation_summary,
            }
            self.client.table("document_versions").insert(v_data).execute()

            # Update Document current version pointer
            self.client.table("documents").update({
                "current_version_number": new_v_num,
                "current_version_id": version_id,
                "file_size_bytes": len(new_content),
                "sha256_hash": sha256
            }).eq("id", doc_id).execute()

            return True, f"Successfully created version {new_v_num}.", new_v_num
        except Exception as e:
            return False, f"Failed to commit version: {e}", 0

    def rollback_version(self, doc_id: str, target_version_number: int) -> Tuple[bool, str, int]:
        """Rolls back document by reading target version and committing it as a new version."""
        content = self.read_document_bytes(doc_id, version_number=target_version_number)
        if content is None:
            return False, f"Target version {target_version_number} could not be retrieved.", 0
        summary = f"Rollback to content of version {target_version_number}"
        return self.create_version(doc_id, content, summary)

    def list_versions(self, doc_id: str) -> List[Dict[str, Any]]:
        """Lists all versions for a document owned by the user."""
        if not self.client:
            return []
        try:
            resp = self.client.table("document_versions").select("*").eq("document_id", doc_id).order("version_number", desc=True).execute()
            return resp.data or []
        except Exception as e:
            print(f"[REPO] list_versions error: {e}")
            return []

    def record_history(self, doc_id: str, instruction: str, interpretation: str, operation: str,
                       execution_status: str, validation_status: str, summary_result: str,
                       prev_v: int, new_v: int) -> bool:
        """Records modification request with encrypted instruction and interpretation."""
        if not self.client:
            return False
        try:
            req_data = {
                "user_id": self.user_id,
                "document_id": doc_id,
                "request_ciphertext": encrypt_text(instruction, self.user_id),
                "interpretation_ciphertext": encrypt_text(interpretation, self.user_id),
                "planned_operation": operation,
                "execution_status": execution_status,
                "validation_status": validation_status,
                "summary_result": summary_result,
                "previous_version_number": prev_v,
                "new_version_number": new_v
            }
            self.client.table("modification_requests").insert(req_data).execute()
            return True
        except Exception as e:
            print(f"[REPO] record_history error: {e}")
            return False

    def list_history(self, doc_id: Optional[str] = None, status_filter: str = "ALL") -> List[Dict[str, Any]]:
        """Retrieves and decrypts user modification request logs."""
        if not self.client:
            return []
        try:
            query = self.client.table("modification_requests").select("*").order("created_at", desc=True)
            if doc_id:
                query = query.eq("document_id", doc_id)
            if status_filter != "ALL":
                query = query.eq("execution_status", status_filter)
            resp = query.execute()

            history = []
            for r in (resp.data or []):
                history.append({
                    "request_id": r["id"],
                    "doc_id": r["document_id"],
                    "instruction": decrypt_text(r["request_ciphertext"], self.user_id),
                    "ai_interpretation": decrypt_text(r.get("interpretation_ciphertext") or "", self.user_id),
                    "planned_operation": r.get("planned_operation", "UNKNOWN"),
                    "execution_status": r["execution_status"],
                    "validation_result": r.get("validation_status", "VALID"),
                    "summary_result": r.get("summary_result", ""),
                    "previous_version": r.get("previous_version_number"),
                    "new_version": r.get("new_version_number"),
                    "created_at": r["created_at"]
                })
            return history
        except Exception as e:
            print(f"[REPO] list_history error: {e}")
            return []


# =====================================================================
# 2. Local SQLite Repository Implementation (Preserves Local Mode)
# =====================================================================

class LocalSQLiteRepository:
    def __init__(self, user_id: int, user_dek: bytes):
        self.user_id = user_id
        self.user_dek = user_dek

    def list_documents(self) -> List[Dict[str, Any]]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
            SELECT doc_id, original_filename, extension, current_version, file_size_bytes, sha256_hash, uploaded_at
            FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC;
            """, (self.user_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE doc_id = ? AND user_id = ?;", (doc_id, self.user_id))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def upload_document(self, filename: str, content_bytes: bytes) -> Tuple[bool, str, Optional[str]]:
        doc_id = str(uuid.uuid4())[:8]
        ok, msg = local_save_initial(self.user_id, self.user_dek, doc_id, filename, content_bytes)
        return ok, msg, doc_id if ok else None

    def read_document_bytes(self, doc_id: str, version_number: Optional[int] = None) -> Optional[bytes]:
        return local_read_decrypted(self.user_id, self.user_dek, doc_id, version_number=version_number)

    def create_version(self, doc_id: str, new_content: bytes, operation_summary: str) -> Tuple[bool, str, int]:
        return local_create_version(self.user_id, self.user_dek, doc_id, new_content, operation_summary)

    def rollback_version(self, doc_id: str, target_version_number: int) -> Tuple[bool, str, int]:
        return local_rollback(self.user_id, self.user_dek, doc_id, target_version_number)

    def list_versions(self, doc_id: str) -> List[Dict[str, Any]]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM document_versions WHERE doc_id = ? AND user_id = ? ORDER BY version_number DESC;", (doc_id, self.user_id))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def record_history(self, doc_id: str, instruction: str, interpretation: str, operation: str,
                       execution_status: str, validation_status: str, summary_result: str,
                       prev_v: int, new_v: int) -> bool:
        from history.history_manager import record_history_entry
        record_history_entry(
            user_id=self.user_id,
            doc_id=doc_id,
            instruction=instruction,
            ai_interpretation=interpretation,
            planned_op=operation,
            status=execution_status,
            validation=validation_status,
            summary=summary_result,
            prev_v=prev_v,
            new_v=new_v
        )
        return True

    def list_history(self, doc_id: Optional[str] = None, status_filter: str = "ALL") -> List[Dict[str, Any]]:
        from history.history_manager import get_user_history
        return get_user_history(self.user_id, doc_id=doc_id, status_filter=status_filter)


# =====================================================================
# 3. Factory Helper to select correct Repository based on session
# =====================================================================

def get_document_repository(session_state: Any):
    """Returns CloudSupabaseRepository if in cloud mode, otherwise LocalSQLiteRepository."""
    if IS_CLOUD_MODE:
        user_id = session_state.get("user_id")
        jwt_token = session_state.get("jwt_token", "")
        return CloudSupabaseRepository(user_id=user_id, jwt_token=jwt_token)
    else:
        user_id = session_state.get("user_id")
        user_dek = session_state.get("user_dek", b"")
        return LocalSQLiteRepository(user_id=user_id, user_dek=user_dek)
