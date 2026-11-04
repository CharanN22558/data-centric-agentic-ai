"""
Encryption and Key Derivation Module.

Implements strict privacy architecture:
1. AES-256-GCM authenticated encryption for private documents, backups, and history.
2. Argon2id password hashing and user master key derivation.
3. Envelope encryption: Each user has a unique random 256-bit Data Encryption Key (DEK).
   The DEK is encrypted using a Key Encryption Key (KEK) derived from the user's password via Argon2id.
4. Independent random 96-bit nonces (IV) generated for every single encryption operation.
"""

import os
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id


# Default Argon2id parameters (secure against GPU and ASIC attacks)
ARGON2_TIME_COST = 2
ARGON2_MEMORY_COST = 64 * 1024  # 64 MB
ARGON2_PARALLELISM = 4
KEY_LENGTH = 32  # 256-bit AES key


def derive_kek_from_password(password: str, salt: bytes) -> bytes:
    """
    Derives a 256-bit Key Encryption Key (KEK) from the user's password using Argon2id.
    """
    kdf = Argon2id(
        salt=salt,
        length=KEY_LENGTH,
        iterations=ARGON2_TIME_COST,
        lanes=ARGON2_PARALLELISM,
        memory_cost=ARGON2_MEMORY_COST,
    )
    return kdf.derive(password.encode("utf-8"))


def generate_random_dek() -> bytes:
    """
    Generates a secure random 256-bit Data Encryption Key (DEK).
    """
    return AESGCM.generate_key(bit_length=256)


def encrypt_bytes(data: bytes, key: bytes, associated_data: bytes = b"") -> bytes:
    """
    Encrypts arbitrary byte content using AES-256-GCM with an independent 12-byte nonce.
    Returns: nonce (12 bytes) + ciphertext + tag (16 bytes).
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit independent nonce
    ciphertext = aesgcm.encrypt(nonce, data, associated_data)
    # Pack: nonce + ciphertext (includes 16-byte auth tag)
    return nonce + ciphertext


def decrypt_bytes(payload: bytes, key: bytes, associated_data: bytes = b"") -> bytes:
    """
    Decrypts AES-256-GCM encrypted payload (nonce + ciphertext + tag).
    Raises an exception if ciphertext is tampered with or corrupted.
    """
    if len(payload) < 28:  # 12 nonce + 16 auth tag minimum
        raise ValueError("Encrypted payload is too short or malformed.")

    nonce = payload[:12]
    ciphertext = payload[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)


def compute_sha256(data: bytes) -> str:
    """
    Computes cryptographic SHA-256 checksum of raw bytes.
    Used for file integrity verification and change validation.
    """
    return hashlib.sha256(data).hexdigest()

