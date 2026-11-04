"""
Regression Test Suite for Application Page Imports and Loaders.

Ensures no missing imports or broken pipelines exist across all Streamlit UI components,
processors, RAG loaders, and repository layers.
"""

import importlib
import pytest


def test_rag_document_loader_exports():
    """Verify load_and_chunk_document and load_document_content are properly exported."""
    from rag.document_loader import load_and_chunk_document, load_document_content, LoadedDocumentItem
    assert callable(load_and_chunk_document)
    assert callable(load_document_content)

    # Test load_and_chunk_document on a sample text
    sample_txt = b"Section 1: Data Centric Agentic AI\nThis is a sample document for import verification."
    chunks = load_and_chunk_document("test.txt", sample_txt)
    assert len(chunks) >= 1
    assert hasattr(chunks[0], "text")
    assert hasattr(chunks[0], "metadata")


def test_modifications_executor_exports():
    """Verify execute_modification_plan and execute_plan are exported."""
    from modifications.executor import execute_modification_plan, execute_plan
    assert callable(execute_modification_plan)
    assert callable(execute_plan)


@pytest.mark.parametrize("module_name", [
    "app",
    "ui.dashboard",
    "ui.documents",
    "ui.chat",
    "ui.modifications",
    "ui.history",
    "ui.settings",
    "rag.document_loader",
    "rag.chunking",
    "rag.vector_store",
    "rag.retrieval",
    "database.repository",
    "database.cloud_db",
    "modifications.executor",
    "modifications.planner",
    "server"
])
def test_all_critical_modules_import_cleanly(module_name):
    """Verifies that every critical project module imports cleanly without raising ImportError."""
    mod = importlib.import_module(module_name)
    assert mod is not None

