"""
Authentication and User Session Module.

Supports:
1. Cloud Mode (Supabase Auth):
   - Sign up with Email/Password
   - Sign in with Email/Password
   - Password reset email
   - Session refresh
   - Bearer token verification

2. Local Mode (Argon2id Envelope Encryption):
   - User registration with Argon2id password hashing
   - Envelope encryption setup (generates DEK and encrypts it with password-derived KEK)
   - User authentication and DEK decryption into memory
"""

import os
from typing import Optional, Tuple, Dict, Any
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from database.db_manager import get_db_connection
from database.cloud_db import get_anon_supabase_client, is_supabase_configured
from auth.encryption import (
    derive_kek_from_password,
    generate_random_dek,
    encrypt_bytes,
    decrypt_bytes,
)
from config import IS_DEMO_MODE, IS_CLOUD_MODE

# Standard Argon2 password hasher
ph = PasswordHasher()


# -------------------------------------------------------------
# Cloud Supabase Authentication Functions
# -------------------------------------------------------------

def supabase_sign_up(email: str, password: str, display_name: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Registers a new user in Supabase Auth."""
    if not is_supabase_configured():
        return False, "Supabase is not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY.", None

    client = get_anon_supabase_client()
    if not client:
        return False, "Failed to connect to Supabase authentication service.", None

    try:
        options = {"data": {"display_name": display_name or email.split("@")[0]}}
        res = client.auth.sign_up({"email": email, "password": password, "options": options})
        if res.user:
            return True, "Registration successful! Please check your email for confirmation if required.", {
                "id": str(res.user.id),
                "email": res.user.email,
                "session": res.session
            }
        return False, "Registration returned empty user object.", None
    except Exception as e:
        err_msg = str(e)
        if "already registered" in err_msg.lower():
            return False, "A user with this email address already exists.", None
        return False, f"Registration failed: {err_msg}", None


def supabase_sign_in(email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Authenticates an existing user in Supabase Auth and returns JWT session."""
    if not is_supabase_configured():
        return False, "Supabase is not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY.", None

    client = get_anon_supabase_client()
    if not client:
        return False, "Failed to connect to Supabase authentication service.", None

    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.session and res.user:
            return True, "Login successful!", {
                "user_id": str(res.user.id),
                "email": res.user.email,
                "access_token": res.session.access_token,
                "refresh_token": res.session.refresh_token,
                "display_name": res.user.user_metadata.get("display_name", email.split("@")[0])
            }
        return False, "Invalid email or password.", None
    except Exception as e:
        return False, f"Login failed: {str(e)}", None


def supabase_sign_out(access_token: str) -> bool:
    """Signs out the user session."""
    try:
        client = get_anon_supabase_client()
        if client and access_token:
            client.auth.sign_out()
            return True
    except Exception:
        pass
    return False


def supabase_reset_password(email: str) -> Tuple[bool, str]:
    """Sends password reset email via Supabase."""
    if not is_supabase_configured():
        return False, "Supabase is not configured."
    try:
        client = get_anon_supabase_client()
        if client:
            client.auth.reset_password_for_email(email)
            return True, "Password reset email sent if the address is registered."
    except Exception as e:
        return False, f"Password reset failed: {e}"
    return False, "Supabase client unavailable."


# -------------------------------------------------------------
# Local SQLite / Argon2id Authentication Functions
# -------------------------------------------------------------

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
        cursor.execute("SELECT id FROM users WHERE username = ?", (clean_username,))
        if cursor.fetchone():
            return False, f"Username '{clean_username}' is already registered."

        password_hash = ph.hash(password)
        salt = os.urandom(16)
        kek = derive_kek_from_password(password, salt)
        dek = generate_random_dek()
        encrypted_dek = encrypt_bytes(dek, kek)

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

        try:
            ph.verify(row["password_hash"], password)
        except (VerifyMismatchError, InvalidHashError):
            return None, None, None, "Invalid username or password."

        salt = bytes(row["salt"])
        encrypted_dek = bytes(row["encrypted_dek"])
        kek = derive_kek_from_password(password, salt)
        dek = decrypt_bytes(encrypted_dek, kek)

        return row["id"], row["username"], dek, "Authentication successful."
    except Exception as e:
        return None, None, None, f"Authentication error: {str(e)}"
    finally:
        conn.close()
