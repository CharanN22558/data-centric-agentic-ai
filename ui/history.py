"""
UI Modification History & Rollback Component.

Displays encrypted operation logs and version rollback studio using the unified repository.
"""

import streamlit as st


def render_history(repo, session_state):
    st.markdown("## 📜 Request History & Version Rollback")
    st.caption("Inspect past operations, audit modifications, and roll back documents to any previous version.")

    docs = repo.list_documents()

    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        status_filter = st.selectbox("Status Filter:", ["ALL", "SUCCESS", "FAILED"])
    with col_f2:
        doc_opts = {"All Files": None}
        for d in docs:
            doc_opts[d["original_filename"]] = d["doc_id"]
        doc_filter = st.selectbox("Document Filter:", list(doc_opts.keys()))

    history = repo.list_history(doc_id=doc_opts[doc_filter], status_filter=status_filter)

    st.subheader(f"Operation History Records ({len(history)})")
    if not history:
        st.info("No modification history matches your filter.")
    else:
        for item in history:
            badge = "🟢 SUCCESS" if item["execution_status"] == "SUCCESS" else "🔴 FAILED"
            with st.expander(f"[{badge}] {item['instruction']} ({item['created_at']})", expanded=False):
                st.markdown(f"**Request ID**: `{item['request_id']}`")
                st.markdown(f"**Target Document**: `{item['doc_id']}`")
                st.markdown(f"**AI Interpretation**: {item['ai_interpretation']}")
                st.markdown(f"**Planned Operation**: `{item['planned_operation']}`")
                st.markdown(f"**Summary**: {item['summary_result']}")
                if item["new_version"] and item["new_version"] != item["previous_version"]:
                    st.markdown(f"**Version Transition**: `v{item['previous_version']}` ➡️ `v{item['new_version']}`")

    # Rollback Section
    st.markdown("---")
    st.subheader("🔄 Version Rollback Studio")
    if not docs:
        st.caption("No documents available for rollback.")
        return

    rb_doc = st.selectbox("Select Document to Rollback:", docs, format_func=lambda d: f"{d['original_filename']} (current: v{d['current_version']})")
    versions = repo.list_versions(rb_doc["doc_id"])

    if len(versions) <= 1:
        st.info("This document currently only has 1 version. Multiple versions are required to rollback.")
    else:
        past_versions = [v for v in versions if v["version_number"] != rb_doc["current_version"]]
        rb_target_v = st.selectbox(
            "Select Target Version to Restore:",
            past_versions,
            format_func=lambda v: f"v{v['version_number']} ({v['created_at']}) - {v.get('operation_summary', 'Edit')}"
        )

        if st.button("⚠️ Restore Selected Version", type="secondary"):
            with st.spinner("Restoring document content and committing new rollback version..."):
                ok, msg, new_v = repo.rollback_version(rb_doc["doc_id"], rb_target_v["version_number"])
                if ok:
                    st.success(f"Rollback successful! Created new version v{new_v} containing content from v{rb_target_v['version_number']}.")
                    st.rerun()
                else:
                    st.error(msg)
