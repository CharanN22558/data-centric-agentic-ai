"""
UI Document Management Component.

Provides multi-user upload, preview, download, and version history
using the unified repository adapter (Supabase in cloud mode, SQLite locally).
"""

import streamlit as st
import io
from processors.excel_processor import inspect_excel
from processors.pdf_processor import extract_pdf_pages_and_text
from rag.document_loader import load_and_chunk_document
from rag.vector_store import get_vector_store
from config import MAX_UPLOAD_MB


def render_documents(repo, session_state):
    st.markdown("## 📁 Document Management")
    st.caption("Upload, inspect, download, and manage your private multi-format documents (TXT, XLSX, PDF).")

    # Upload Section
    with st.expander("📤 Upload New Document", expanded=True):
        uploaded_file = st.file_uploader(
            "Choose a TXT, XLSX, or PDF file",
            type=["txt", "xlsx", "pdf"],
            help=f"Maximum file size allowed is {MAX_UPLOAD_MB} MB."
        )
        if uploaded_file is not None:
            if uploaded_file.size > (MAX_UPLOAD_MB * 1024 * 1024):
                st.error(f"File size exceeds limit of {MAX_UPLOAD_MB} MB.")
            elif st.button("🚀 Encrypt & Upload to Cloud Workspace"):
                with st.spinner("Encrypting at rest and uploading to private storage..."):
                    content_bytes = uploaded_file.read()
                    success, msg, doc_id = repo.upload_document(uploaded_file.name, content_bytes)
                    if success and doc_id:
                        # Index chunks in pgvector
                        try:
                            chunks = load_and_chunk_document(uploaded_file.name, content_bytes)
                            vstore = get_vector_store(session_state)
                            vstore.add_chunks(doc_id, 1, chunks)
                        except Exception as ex:
                            print(f"[INDEXING WARN]: {ex}")

                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # Document Listing
    docs = repo.list_documents()

    st.subheader(f"Your Stored Documents ({len(docs)})")
    if not docs:
        st.info("No documents uploaded yet. Upload a TXT, Excel, or PDF document above to get started.")
        return

    for doc in docs:
        doc_id = doc["doc_id"]
        v_num = doc["current_version"]
        fname = doc["original_filename"]
        size_kb = round(doc.get("file_size_bytes", 0) / 1024, 2)

        with st.expander(f"📄 **{fname}** (v{v_num}) — {size_kb} KB", expanded=False):
            col_info, col_actions = st.columns([2, 1])

            with col_info:
                st.markdown(f"**Document ID**: `{doc_id}`")
                st.markdown(f"**Format**: `{doc['extension'].upper()}`")
                st.markdown(f"**Current Version**: `v{v_num}`")
                st.markdown(f"**SHA-256 Hash**: `{doc['sha256_hash'][:16]}...`")

            with col_actions:
                # Download Button
                file_bytes = repo.read_document_bytes(doc_id, version_number=v_num)
                if file_bytes:
                    mime = "text/plain" if doc["extension"] == ".txt" else "application/pdf" if doc["extension"] == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    st.download_button(
                        label=f"⬇️ Download {fname}",
                        data=file_bytes,
                        file_name=fname,
                        mime=mime,
                        key=f"dl_{doc_id}_{v_num}"
                    )

            # Document Preview
            st.markdown("#### Document Preview")
            if file_bytes:
                if doc["extension"] == ".txt":
                    st.text_area("Content Preview", file_bytes.decode("utf-8", errors="replace")[:1500], height=180)
                elif doc["extension"] == ".xlsx":
                    try:
                        sheet_info = inspect_excel(file_bytes)
                        st.json(sheet_info)
                    except Exception as e:
                        st.caption(f"Excel inspection notice: {e}")
                elif doc["extension"] == ".pdf":
                    try:
                        pdf_data = extract_pdf_pages_and_text(file_bytes)
                        st.caption(f"Total Pages: {pdf_data.get('total_pages', 1)}")
                        if pdf_data.get("pages"):
                            st.text_area("Page 1 Text", pdf_data["pages"][0]["text"][:1000], height=150)
                    except Exception as e:
                        st.caption(f"PDF extraction notice: {e}")

            # Version History List
            st.markdown("#### Version History")
            versions = repo.list_versions(doc_id)
            if versions:
                for v in versions:
                    st.markdown(f"- **v{v['version_number']}** ({v['created_at']}): {v.get('operation_summary', 'Update')}")
