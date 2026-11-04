"""
Test Suite for User Authentication and Multi-Tenant Isolation.
"""

import uuid
import pytest
from auth.authentication import register_user, authenticate_user
from database.db_manager import init_database, get_db_connection


@pytest.fixture(autouse=True)
def setup_test_db():
    init_database()


def test_user_registration_and_authentication():
    # Use random unique username for isolated test runs
    unique_suffix = str(uuid.uuid4())[:6]
    username = f"user_{unique_suffix}"
    password = "SuperSecretPassword123"

    # Register
    ok, msg = register_user(username, password)
    assert ok is True
    assert "successfully" in msg.lower()

    # Duplicate registration fails
    dup_ok, dup_msg = register_user(username, password)
    assert dup_ok is False

    # Authenticate valid credentials
    uid, uname, dek, auth_msg = authenticate_user(username, password)
    assert uid is not None
    assert uname == username
    assert dek is not None
    assert len(dek) == 32  # 256-bit AES key

    # Authenticate invalid password
    bad_uid, _, bad_dek, _ = authenticate_user(username, "WrongPassword")
    assert bad_uid is None
    assert bad_dek is None
