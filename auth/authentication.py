"""
Authentication and User Session Module.

Provides:
- User registration with Argon2id password hashing
- Envelope encryption setup (generates DEK and encrypts it with password-derived KEK)
- User authentication and DEK decryption into memory
- Safe user logout and memory wiping
- Multi-user isolation enforcement
"""

import os
from typing import Optional, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from database.db_manager import get_db_connection
from auth.encryption import (
    derive_kek_from_password,
    generate_random_dek,
    encrypt_bytes,
    decrypt_bytes,
)
from config import IS_DEMO_MODE

# Standard Argon2 password hasher
ph = PasswordHasher()


def register_user(username: str, password: str) -> Tuple[bool, str]:
    """
    Registers a new local account:
    1. Validates username and password length.
    2. Generates random 16-byte salt and unique 256-bit DEK.
    3. Derives KEK using Argon2id and encrypts the DEK using AES-256-GCM.
    4. Hashes password using Argon2id for login verification.
    5. Saves account metadata to SQLite.
    """
    if IS_DEMO_MODE:
        return False, "Registration is disabled in Public Demonstration Mode."

    clean_username = username.strip().lower()
    if len(clean_username) < 3:
        return False, "Username must be at least 3 characters long."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if username exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (clean_username,))
        if cursor.fetchone():
            return False, f"Username '{clean_username}' is already registered."

        # 1. Hash password for login checks
        password_hash = ph.hash(password)

        # 2. Derive KEK and encrypt random DEK
        salt = os.urandom(16)
        kek = derive_kek_from_password(password, salt)
        dek = generate_random_dek()
        encrypted_dek = encrypt_bytes(dek, kek)

        # 3. Store record in database
        cursor.execute("""
        INSERT INTO users (username, password_hash, salt, encrypted_dek)
        VALUES (?, ?, ?, ?);
        """, (clean_username, password_hash, salt, encrypted_dek))

        conn.commit()
        return True, "Account registered successfully. You can now log in."
    except Exception as e:
        return False, f"Registration failed: {str(e)}"
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Tuple[Optional[int], Optional[str], Optional[bytes], str]:
    """
    Authenticates a user and recovers their in-memory Data Encryption Key (DEK).

    Returns:
    (user_id, username, in_memory_dek, message)
    """
    clean_username = username.strip().lower()

    # DEMO MODE Bypass: allows quick exploration with a synthetic demo account
    if IS_DEMO_MODE:
        dummy_dek = generate_random_dek()
        return 9999, "demo_user", dummy_dek, "Logged in as Demonstration User."

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        SELECT id, username, password_hash, salt, encrypted_dek
        FROM users WHERE username = ?;
        """, (clean_username,))
        row = cursor.fetchone()

        if not row:
            return None, None, None, "Invalid username or password."

        # 1. Verify password hash using Argon2
        try:
            ph.verify(row["password_hash"], password)
        except (VerifyMismatchError, InvalidHashError):
            return None, None, None, "Invalid username or password."

        # 2. Derive KEK and decrypt DEK into memory
        salt = bytes(row["salt"])
        encrypted_dek = bytes(row["encrypted_dek"])
        kek = derive_kek_from_password(password, salt)
        dek = decrypt_bytes(encrypted_dek, kek)

        return row["id"], row["username"], dek, "Authentication successful."
    except Exception as e:
        return None, None, None, f"Authentication error: {str(e)}"
    finally:
        conn.close()

