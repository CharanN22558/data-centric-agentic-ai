"""
UI Document Management Component.
Provides upload, inspection, preview, and download capabilities.
"""

import streamlit as st
import uuid
from database.db_manager import get_db_connection
from modifications.version_control import save_initial_document, read_decrypted_document
from config import IS_DEMO_MODE, ALLOWED_EXTENSIONS
from processors.excel_processor import inspect_excel
from processors.pdf_processor import extract_pdf_pages_and_text


def render_documents(user_id: int, user_dek: bytes):
    st.markdown("## 📁 Document Management")

    # Upload Section
    if not IS_DEMO_MODE:
        with st.expander("📤 Upload New Document (Encrypted Locally)", expanded=False):
            uploaded_file = st.file_uploader(
                "Choose a TXT, XLSX, or PDF file",
                type=["txt", "xlsx", "pdf"]
            )
            if uploaded_file is not None:
                if st.button("Encrypt & Store Document"):
                    content_bytes = uploaded_file.read()
                    doc_id = str(uuid.uuid4())[:8]
                    success, msg = save_initial_document(
                        user_id=user_id,
                        user_dek=user_dek,
                        doc_id=doc_id,
                        filename=uploaded_file.name,
                        content_bytes=content_bytes
                    )
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    else:
        st.info("ℹ️ Uploads disabled in Demonstration Mode. Viewing synthetic documents.")

    # List User Documents
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT doc_id, original_filename, extension, current_version, file_size_bytes, sha256_hash, uploaded_at
    FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC;
    """, (user_id,))
    docs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not docs:
        st.info("No documents found in your workspace. Use the upload panel above to add files.")
        return

    st.subheader(f"Workspace Files ({len(docs)})")
    for doc in docs:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            with col1:
                st.markdown(f"**📄 {doc['original_filename']}** (`{doc['extension'].upper()}`)")
                st.caption(f"ID: `{doc['doc_id']}` | Size: {round(doc['file_size_bytes']/1024, 1)} KB | Version: `v{doc['current_version']}`")
            with col2:
                # Decrypt & Download
                if st.button("📥 Download", key=f"dl_{doc['doc_id']}"):
                    try:
                        dec_bytes, fname, ver = read_decrypted_document(user_id, user_dek, doc["doc_id"])
                        st.download_button(
                            label=f"Save v{ver}_{fname}",
                            data=dec_bytes,
                            file_name=f"v{ver}_{fname}",
                            key=f"dl_btn_{doc['doc_id']}"
                        )
                    except Exception as e:
                        st.error(f"Decryption error: {e}")
            with col3:
                # Preview action
                preview_active = st.button("👁️ Inspect", key=f"insp_{doc['doc_id']}")

            if preview_active:
                st.markdown("---")
                st.markdown(f"#### 🔍 Content Preview: {doc['original_filename']}")
                try:
                    dec_bytes, fname, _ = read_decrypted_document(user_id, user_dek, doc["doc_id"])
                    ext = doc["extension"].lower()
                    if ext == ".txt":
                        st.text_area("Plain Text Content", dec_bytes.decode("utf-8", errors="replace"), height=200)
                    elif ext == ".xlsx":
                        info = inspect_excel(dec_bytes)
                        st.json(info)
                    elif ext == ".pdf":
                        pages, scanned = extract_pdf_pages_and_text(dec_bytes)
                        if scanned:
                            st.warning("⚠️ Warning: This PDF appears to be a scanned image. Optical Character Recognition (OCR) is required for full text extraction.")
                        for p in pages[:3]:
                            st.markdown(f"**Page {p['page_number']}:**")
                            st.text(p["text"][:300] + "...")
                except Exception as err:
                    st.error(f"Could not load preview: {err}")
            st.markdown("---")

