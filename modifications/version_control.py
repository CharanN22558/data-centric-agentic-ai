"""
Transactional Document Version Control & Storage Module.

Strict Privacy Architecture:
1. Files are stored locally on disk ONLY in AES-256-GCM encrypted format.
2. In-memory temporary decrypted copies during processing.
3. Transactional modification: failure discards working copy; original is never overwritten.
4. Rollback creates a new version from previous content (immutable audit trail).
5. Automatic re-indexing into ephemeral vector store upon modification.
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from auth.encryption import encrypt_bytes, decrypt_bytes, compute_sha256
from database.db_manager import get_db_connection
from config import USER_DATA_DIR, IS_DEMO_MODE
from rag.document_loader import load_document_content
from rag.chunking import chunk_document_items
from rag.vector_store import vector_store


def get_user_storage_dir(user_id: int) -> Path:
    """Returns local encrypted storage folder for user."""
    path = USER_DATA_DIR / f"user_{user_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_initial_document(
    user_id: int,
    user_dek: bytes,
    doc_id: str,
    filename: str,
    content_bytes: bytes
) -> Tuple[bool, str]:
    """
    Encrypts and saves a new document as Version 1.
    Indexes chunks into ephemeral memory.
    """
    if IS_DEMO_MODE:
        return False, "Uploading private documents is disabled in Demonstration Mode."

    user_dir = get_user_storage_dir(user_id)
    doc_dir = user_dir / doc_id / "v1"
    doc_dir.mkdir(parents=True, exist_ok=True)

    # 1. Encrypt file with user's DEK
    encrypted_payload = encrypt_bytes(content_bytes, user_dek)
    enc_path = doc_dir / f"{filename}.enc"

    with open(enc_path, "wb") as f:
        f.write(encrypted_payload)

    # 2. Checksum & metadata
    sha256 = compute_sha256(content_bytes)
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

    # 3. Load & index chunks into in-memory ChromaDB
    items, summary = load_document_content(filename, content_bytes)
    chunks = chunk_document_items(items)
    vector_store.index_document(user_id, doc_id, filename, chunks)

    # 4. Save metadata in SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    import json
    cursor.execute("""
    INSERT INTO documents (doc_id, user_id, original_filename, extension, current_version, file_size_bytes, sha256_hash, encrypted_file_path, summary_metadata)
    VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?);
    """, (doc_id, user_id, filename, ext, len(content_bytes), sha256, str(enc_path), json.dumps(summary)))

    cursor.execute("""
    INSERT INTO document_versions (doc_id, user_id, version_number, encrypted_file_path, sha256_hash, change_comment)
    VALUES (?, ?, 1, ?, ?, 'Initial upload');
    """, (doc_id, user_id, str(enc_path), sha256))

    conn.commit()
    conn.close()
    return True, f"Successfully encrypted and indexed '{filename}' as Version 1."


def read_decrypted_document(
    user_id: int,
    user_dek: bytes,
    doc_id: str,
    version: Optional[int] = None
) -> Tuple[bytes, str, int]:
    """
    Retrieves and decrypts a document for the authenticated user.
    Returns: (decrypted_bytes, filename, version_number)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT original_filename, current_version, encrypted_file_path
    FROM documents WHERE doc_id = ? AND user_id = ?;
    """, (doc_id, user_id))
    doc = cursor.fetchone()

    if not doc:
        conn.close()
        raise ValueError(f"Document with ID '{doc_id}' not found or access denied.")

    target_ver = version if version is not None else doc["current_version"]

    cursor.execute("""
    SELECT encrypted_file_path FROM document_versions
    WHERE doc_id = ? AND user_id = ? AND version_number = ?;
    """, (doc_id, user_id, target_ver))
    ver_row = cursor.fetchone()
    conn.close()

    if not ver_row:
        raise ValueError(f"Version {target_ver} of document '{doc['original_filename']}' not found.")

    enc_path = Path(ver_row["encrypted_file_path"])
    if not enc_path.exists():
        raise FileNotFoundError("Encrypted file missing from local storage.")

    with open(enc_path, "rb") as f:
        encrypted_payload = f.read()

    decrypted_bytes = decrypt_bytes(encrypted_payload, user_dek)
    return decrypted_bytes, doc["original_filename"], target_ver


def commit_new_version(
    user_id: int,
    user_dek: bytes,
    doc_id: str,
    filename: str,
    new_bytes: bytes,
    comment: str = "Modified by Agent"
) -> Tuple[int, str]:
    """
    Commits a new version to encrypted storage and updates vector search.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT current_version FROM documents WHERE doc_id = ? AND user_id = ?;", (doc_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Document not found.")

    new_version_num = row["current_version"] + 1

    # Save encrypted
    user_dir = get_user_storage_dir(user_id)
    ver_dir = user_dir / doc_id / f"v{new_version_num}"
    ver_dir.mkdir(parents=True, exist_ok=True)

    enc_path = ver_dir / f"{filename}.enc"
    encrypted_payload = encrypt_bytes(new_bytes, user_dek)
    with open(enc_path, "wb") as f:
        f.write(encrypted_payload)

    new_hash = compute_sha256(new_bytes)

    # Update metadata
    cursor.execute("""
    UPDATE documents SET current_version = ?, file_size_bytes = ?, sha256_hash = ?, encrypted_file_path = ?
    WHERE doc_id = ? AND user_id = ?;
    """, (new_version_num, len(new_bytes), new_hash, str(enc_path), doc_id, user_id))

    cursor.execute("""
    INSERT INTO document_versions (doc_id, user_id, version_number, encrypted_file_path, sha256_hash, change_comment)
    VALUES (?, ?, ?, ?, ?, ?);
    """, (doc_id, user_id, new_version_num, str(enc_path), new_hash, comment))

    conn.commit()
    conn.close()

    # Re-index in ephemeral ChromaDB
    items, _ = load_document_content(filename, new_bytes)
    chunks = chunk_document_items(items)
    vector_store.index_document(user_id, doc_id, filename, chunks)

    return new_version_num, f"Committed new Version {new_version_num} successfully."


def rollback_document_version(
    user_id: int,
    user_dek: bytes,
    doc_id: str,
    target_version_to_restore: int
) -> Tuple[int, str]:
    """
    Rolls back to a target version by committing its content as a new version.
    Never deletes existing versions (preserves complete provenance).
    """
    past_bytes, filename, _ = read_decrypted_document(
        user_id, user_dek, doc_id, version=target_version_to_restore
    )
    comment = f"Rollback to content of Version {target_version_to_restore}"
    new_v, msg = commit_new_version(user_id, user_dek, doc_id, filename, past_bytes, comment=comment)
    return new_v, f"Rollback successful: created Version {new_v} from Version {target_version_to_restore}."

