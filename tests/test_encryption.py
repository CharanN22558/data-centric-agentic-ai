"""
Test Suite for AES-256-GCM Encryption and Argon2id KDF.
"""

import os
import pytest
from auth.encryption import (
    derive_kek_from_password,
    generate_random_dek,
    encrypt_bytes,
    decrypt_bytes,
    compute_sha256
)


def test_argon2id_derivation_and_aes_encryption():
    password = "MyStrongPassword456"
    salt = os.urandom(16)
    kek = derive_kek_from_password(password, salt)
    assert len(kek) == 32

    # Envelope encryption: encrypt random DEK
    dek = generate_random_dek()
    encrypted_dek = encrypt_bytes(dek, kek)
    assert len(encrypted_dek) > len(dek)  # Nonce + tag added

    decrypted_dek = decrypt_bytes(encrypted_dek, kek)
    assert decrypted_dek == dek


def test_document_encryption_and_integrity_tampering():
    dek = generate_random_dek()
    plaintext = b"Confidential Research Data for Agentic AI"

    encrypted = encrypt_bytes(plaintext, dek)
    assert encrypted != plaintext

    decrypted = decrypt_bytes(encrypted, dek)
    assert decrypted == plaintext

    # Tampering test (tampering with ciphertext MUST fail auth tag verification)
    tampered = bytearray(encrypted)
    tampered[-1] ^= 0xFF
    with pytest.raises(Exception):
        decrypt_bytes(bytes(tampered), dek)

