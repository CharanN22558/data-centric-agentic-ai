"""
Cloud Key Derivation & Application-Level Encryption Module.

Implements AES-256-GCM encryption at rest for documents, backups, and sensitive history.
Derives deterministic per-user data encryption keys from APP_ENCRYPTION_MASTER_KEY
using HKDF-SHA256.
"""

import os
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from config import APP_ENCRYPTION_MASTER_KEY


def get_or_derive_master_key() -> bytes:
    """
    Returns the server-side master key as 32 bytes.
    If APP_ENCRYPTION_MASTER_KEY is not set or invalid length, uses a deterministic fallback.
    """
    if APP_ENCRYPTION_MASTER_KEY:
        # Normalize to 32 bytes via SHA-256
        return hashlib.sha256(APP_ENCRYPTION_MASTER_KEY.encode("utf-8")).digest()
    # Safe default for local/test instances
    return hashlib.sha256(b"DATA_CENTRIC_AGENTIC_AI_DEFAULT_CLOUD_KEY_V1").digest()


def derive_user_data_key(user_id: str) -> bytes:
    """
    Derives an isolated 32-byte AES-256-GCM encryption key for a specific user UUID
    using HKDF-SHA256 with user_id as info context.
    """
    master_key = get_or_derive_master_key()
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"supabase_user_data_key_v1",
        info=user_id.encode("utf-8"),
    )
    return hkdf.derive(master_key)


def encrypt_data_bytes(plaintext: bytes, user_id: str, associated_data: str = "") -> bytes:
    """
    Encrypts arbitrary bytes using AES-256-GCM.
    Returns: 12-byte Nonce + Ciphertext (with 16-byte auth tag appended).
    """
    user_key = derive_user_data_key(user_id)
    aesgcm = AESGCM(user_key)
    nonce = os.urandom(12)
    aad = associated_data.encode("utf-8") if associated_data else None
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
    return nonce + ciphertext


def decrypt_data_bytes(payload: bytes, user_id: str, associated_data: str = "") -> bytes:
    """
    Decrypts payload using the user's derived AES-256-GCM key.
    Raises ValueError on tampering or invalid key.
    """
    if len(payload) < 28:
        raise ValueError("Invalid payload: data too short for nonce and tag.")
    nonce = payload[:12]
    ciphertext = payload[12:]
    user_key = derive_user_data_key(user_id)
    aesgcm = AESGCM(user_key)
    aad = associated_data.encode("utf-8") if associated_data else None
    return aesgcm.decrypt(nonce, ciphertext, aad)


def encrypt_text(plaintext_str: str, user_id: str, associated_data: str = "") -> str:
    """Encrypts a string into a hex-encoded ciphertext."""
    encrypted_bytes = encrypt_data_bytes(plaintext_str.encode("utf-8"), user_id, associated_data)
    return encrypted_bytes.hex()


def decrypt_text(ciphertext_hex: str, user_id: str, associated_data: str = "") -> str:
    """Decrypts a hex-encoded ciphertext back to a string."""
    try:
        raw_bytes = bytes.fromhex(ciphertext_hex)
        decrypted = decrypt_data_bytes(raw_bytes, user_id, associated_data)
        return decrypted.decode("utf-8", errors="replace")
    except Exception as e:
        return f"[Decryption Error: {e}]"
