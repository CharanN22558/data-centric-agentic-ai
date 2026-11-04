"""
Test Suite for Transactional Versioning and Rollback.
"""

import uuid
from auth.encryption import generate_random_dek
from modifications.version_control import (
    save_initial_document,
    read_decrypted_document,
    commit_new_version,
    rollback_document_version
)
from database.db_manager import init_database


def test_transactional_versioning_and_rollback():
    init_database()
    user_id = 992
    dek = generate_random_dek()
    unique_suffix = str(uuid.uuid4())[:6]
    doc_id = f"doc_{unique_suffix}"
    filename = "report.txt"

    # Save v1
    v1_content = b"Report Version 1: Initial Findings"
    ok, _ = save_initial_document(user_id, dek, doc_id, filename, v1_content)
    assert ok is True

    # Commit v2
    v2_content = b"Report Version 2: Modified Analysis"
    v2_num, _ = commit_new_version(user_id, dek, doc_id, filename, v2_content, "Updated analysis")
    assert v2_num == 2

    # Verify latest read returns v2
    data_v2, _, ver = read_decrypted_document(user_id, dek, doc_id)
    assert ver == 2
    assert data_v2 == v2_content

    # Rollback to v1 (creates v3 containing v1 content)
    v3_num, msg = rollback_document_version(user_id, dek, doc_id, target_version_to_restore=1)
    assert v3_num == 3
    assert "successful" in msg.lower()

    # Verify current active version (v3) contains original v1 content
    data_v3, _, ver_now = read_decrypted_document(user_id, dek, doc_id)
    assert ver_now == 3
    assert data_v3 == v1_content
