"""
Database Manager Module.

Manages local SQLite tables for:
- User accounts (Argon2id password hashes, salt, encrypted DEK)
- Encrypted document metadata (file names, current version, checksums)
- Encrypted document version history (version number, encrypted storage path)
- Encrypted modification requests & audit logs
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from config import DATABASE_PATH, IS_DEMO_MODE


def get_db_connection() -> sqlite3.Connection:
    """
    Returns a connection to the local SQLite database.
    In DEMO mode, an in-memory SQLite database is used to guarantee no data persistence.
    """
    if IS_DEMO_MODE:
        db_path = ":memory:"
    else:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        db_path = str(DATABASE_PATH)

    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """
    Initializes SQLite tables if they do not exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt BLOB NOT NULL,
        encrypted_dek BLOB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Documents Metadata Table (Scoped strictly by user_id)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        original_filename TEXT NOT NULL,
        extension TEXT NOT NULL,
        current_version INTEGER NOT NULL DEFAULT 1,
        file_size_bytes INTEGER NOT NULL,
        sha256_hash TEXT NOT NULL,
        encrypted_file_path TEXT NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        summary_metadata TEXT DEFAULT '{}',
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 3. Document Versions Table (Transactional versioning & rollback)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        version_number INTEGER NOT NULL,
        encrypted_file_path TEXT NOT NULL,
        sha256_hash TEXT NOT NULL,
        change_comment TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (doc_id) REFERENCES documents (doc_id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 4. Modification Request History Table (Encrypted request records)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modification_history (
        request_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        doc_id TEXT,
        instruction TEXT NOT NULL,
        ai_interpretation TEXT NOT NULL,
        intent_classification TEXT NOT NULL,
        planned_operation TEXT NOT NULL,
        execution_status TEXT NOT NULL, -- 'SUCCESS' or 'FAILED' or 'ROLLED_BACK'
        validation_result TEXT NOT NULL,
        previous_version INTEGER,
        new_version INTEGER,
        summary_result TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    conn.commit()
    conn.close()

