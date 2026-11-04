"""
Phase 3 Test Suite: Gemini API Integration, Connection, Gating & Privacy.
"""

import os
import pytest
from auth.gemini_client import (
    test_gemini_connection as check_gemini_connection,
    call_gemini_generate,
    get_gemini_api_key,
    get_gemini_model,
    DEFAULT_GEMINI_MODEL
)
from rag.retrieval import generate_rag_answer


def test_missing_api_key_detection():
    # If no key is set, check_gemini_connection should gracefully return false with clear message
    ok, msg, details = check_gemini_connection(api_key="", model="gemini-2.5-flash")
    assert ok is False
    assert "not configured" in msg.lower()
    assert details["error_type"] == "MISSING_KEY"


def test_invalid_api_key_handling():
    # An intentionally invalid key must be rejected with HTTP 400/403 and never leak the key in msg
    fake_key = "AIzaSyFakeInvalidKeyForTesting1234567890"
    ok, msg, details = check_gemini_connection(api_key=fake_key, model="gemini-2.5-flash")
    assert ok is False
    assert fake_key not in msg  # Key must NEVER be displayed or logged
    assert details["error_type"] in ("INVALID_KEY", "API_ERROR", "NETWORK_ERROR")


def test_privacy_gating_blocks_without_consent():
    # Calling Gemini with private data without consent must be blocked locally before making network calls
    res = call_gemini_generate(
        prompt="Tell me about secret document",
        api_key="AIzaSySomeKey",
        model="gemini-2.5-flash",
        user_approved_external_processing=False,
        is_demo_document=False
    )
    assert res["success"] is False
    assert res["error_type"] == "PRIVACY_BLOCKED"
    assert "consent" in res["error"].lower()


def test_rag_synthesis_fallback_when_offline():
    # RAG answer generation must succeed deterministically when no key is present
    dummy_chunks = [{
        "filename": "sample_employees.xlsx",
        "location": "Sheet1, Row 2",
        "text": "Employee Alice Smith is an AI Engineer earning 85000."
    }]

    ans = generate_rag_answer(
        query="What is Alice's role?",
        retrieved_chunks=dummy_chunks,
        user_consented_to_cloud=False,
        is_demo_mode=False
    )

    assert ans["source_count"] == 1
    assert len(ans["citations"]) == 1
    assert ans["citations"][0]["filename"] == "sample_employees.xlsx"
    assert "Alice Smith" in ans["answer"]
    assert "local" in ans["engine"].lower()
