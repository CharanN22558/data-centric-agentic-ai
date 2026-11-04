"""
Test Suite for Unified Multi-Format RAG and Source Citations.
"""

from rag.document_loader import load_document_content
from rag.chunking import chunk_document_items
from rag.vector_store import vector_store
from rag.retrieval import retrieve_context, generate_rag_answer


def test_txt_rag_pipeline():
    user_id = 991
    filename = "test_policy.txt"
    content = b"The annual company retreat will take place in Kyoto, Japan.\nAll flight expenses are reimbursed up to $1500."

    items, summary = load_document_content(filename, content)
    chunks = chunk_document_items(items)
    indexed_count = vector_store.index_document(user_id, "doc_txt_1", filename, chunks)
    assert indexed_count > 0

    # Retrieve
    retrieved = retrieve_context(user_id, "Where will the retreat be held?", target_doc_id="doc_txt_1")
    assert len(retrieved) > 0
    assert "Kyoto" in retrieved[0]["text"]
    assert "Lines" in retrieved[0]["location"]

    # Generate answer
    ans = generate_rag_answer("Where will the retreat be held?", retrieved)
    assert ans["source_count"] >= 1
    assert len(ans["citations"]) >= 1
    assert ans["citations"][0]["filename"] == filename

