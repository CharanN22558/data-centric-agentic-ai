"""
Automated Test Suite for Supabase Storage Header Propagation and RLS Policy Invariants.
"""

import os
import pytest
from database import cloud_db


def test_storage_client_receives_user_jwt(monkeypatch):
    """Verifies that get_user_supabase_client attaches the user's JWT to all storage headers."""
    monkeypatch.setenv("SUPABASE_URL", "https://ftyvumxamwdalqhwcmow.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_test_publishable_key")

    test_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_user_jwt_token_12345"
    client = cloud_db.get_user_supabase_client(test_jwt)
    assert client is not None

    # Check PostgREST headers
    assert client.postgrest.headers.get("authorization") == f"Bearer {test_jwt}"

    # Check Storage client internal headers
    assert client.storage._headers.get("authorization") == f"Bearer {test_jwt}"
    assert client.storage.session.headers.get("authorization") == f"Bearer {test_jwt}"

    # Check Bucket proxy headers
    bucket = client.storage.from_("user-documents")
    assert bucket._headers.get("authorization") == f"Bearer {test_jwt}"
    assert bucket._client.headers.get("authorization") == f"Bearer {test_jwt}"


def test_storage_repair_migration_invariants():
    """Verifies that 0002_repair_storage_rls.sql enforces strictly private bucket and folder RLS."""
    mig_path = os.path.join(os.path.dirname(__file__), "..", "supabase", "migrations", "0002_repair_storage_rls.sql")
    assert os.path.exists(mig_path)

    with open(mig_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Bucket must be private
    assert "user-documents', false" in sql

    # Policies must exist and target authenticated role
    assert "dcai_authenticated_upload_own_files" in sql
    assert "dcai_authenticated_read_own_files" in sql
    assert "dcai_authenticated_update_own_files" in sql
    assert "dcai_authenticated_delete_own_files" in sql
    assert "TO authenticated" in sql
    assert "(storage.foldername(name))[1] = (SELECT auth.uid()::text)" in sql


def test_repository_uses_upsert_false():
    """Verifies that document uploads never use upsert=true for immutable versions."""
    repo_path = os.path.join(os.path.dirname(__file__), "..", "database", "repository.py")
    with open(repo_path, "r", encoding="utf-8") as f:
        repo_code = f.read()

    # Check upload calls
    assert '"upsert": "false"' in repo_code
    assert '"upsert": "true"' not in repo_code
