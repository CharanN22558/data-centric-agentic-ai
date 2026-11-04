"""
UI Modification History & Rollback Component.
Displays private request logs, filters, diff summaries, and rollback controls.
"""

import streamlit as st
from database.db_manager import get_db_connection
from history.history_manager import get_user_history
from modifications.version_control import rollback_document_version, read_decrypted_document


def render_history(user_id: int, user_dek: bytes):
    st.markdown("## 📜 Request History & Version Rollback")

    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        status_filter = st.selectbox("Status Filter:", ["ALL", "SUCCESS", "FAILED"])
    with col_f2:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT doc_id, original_filename FROM documents WHERE user_id = ?;", (user_id,))
        docs = [dict(r) for r in cursor.fetchall()]
        conn.close()
        doc_opts = {"All Files": None}
        for d in docs:
            doc_opts[d["original_filename"]] = d["doc_id"]
        doc_filter = st.selectbox("Document Filter:", list(doc_opts.keys()))

    history = get_user_history(user_id, doc_id=doc_opts[doc_filter], status_filter=status_filter)

    st.subheader(f"Logged Operations ({len(history)})")
    if not history:
        st.info("No modification history matches your filter.")
        return

    for item in history:
        with st.expander(f"[{item['execution_status']}] {item['instruction']} ({item['created_at']})", expanded=False):
            st.markdown(f"**Request ID**: `{item['request_id']}`")
            st.markdown(f"**Target Document**: `{item['doc_id']}`")
            st.markdown(f"**AI Interpretation**: {item['ai_interpretation']}")
            st.markdown(f"**Operation**: `{item['planned_operation']}`")
            st.markdown(f"**Validation Report**: {item['validation_result']}")
            st.markdown(f"**Summary**: {item['summary_result']}")

            if item["new_version"]:
                st.markdown(f"**Version Transition**: `v{item['previous_version']}` ➡️ `v{item['new_version']}`")

    # Document Rollback Studio
    st.markdown("---")
    st.subheader("🔄 Version Rollback Studio")
    st.caption("Restore any previous version by creating an immutable new version from its content.")

    if docs:
        selected_doc = st.selectbox("Select Document for Rollback:", docs, format_func=lambda d: d["original_filename"])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT version_number, change_comment, created_at FROM document_versions
        WHERE doc_id = ? AND user_id = ? ORDER BY version_number ASC;
        """, (selected_doc["doc_id"], user_id))
        versions = [dict(r) for r in cursor.fetchall()]
        conn.close()

        v_choice = st.selectbox(
            "Select Version to Restore:",
            versions,
            format_func=lambda v: f"Version {v['version_number']} ({v['change_comment']}) - {v['created_at']}"
        )

        if st.button("⏪ Rollback to this Version"):
            with st.spinner("Executing transactional rollback..."):
                try:
                    new_v, msg = rollback_document_version(
                        user_id=user_id,
                        user_dek=user_dek,
                        doc_id=selected_doc["doc_id"],
                        target_version_to_restore=v_choice["version_number"]
                    )
                    st.success(msg)
                    st.rerun()
                except Exception as e:
                    st.error(f"Rollback failed: {str(e)}")

