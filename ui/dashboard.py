"""
UI Dashboard Component.

Displays real-time cloud workspace metrics, document counts, privacy status,
and recent modification activity using the unified repository.
"""

import streamlit as st
from config import IS_CLOUD_MODE


def render_dashboard(repo, session_state):
    username = session_state.get("username", "User")
    st.markdown(f"## 📊 System Overview & Workspace Metrics")
    st.caption(f"Welcome back, **{username}**! Real-time statistics for your isolated cloud workspace.")

    if IS_CLOUD_MODE:
        st.success("🔒 **Supabase Multi-User Cloud Mode Active**: PostgreSQL Row Level Security (RLS) enforced. Private bucket storage with AES-256-GCM encryption at rest.")
    else:
        st.info("🔒 **Local Private Mode Active**: Local SQLite and AES-256-GCM encrypted directory.")

    docs = repo.list_documents()
    history = repo.list_history()

    # Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Documents", len(docs))
    with m2:
        txt_count = sum(1 for d in docs if d["extension"] == ".txt")
        st.metric("Text Files", txt_count)
    with m3:
        xlsx_count = sum(1 for d in docs if d["extension"] == ".xlsx")
        st.metric("Excel Workbooks", xlsx_count)
    with m4:
        pdf_count = sum(1 for d in docs if d["extension"] == ".pdf")
        st.metric("PDF Files", pdf_count)

    st.markdown("---")

    # Recent Activity
    st.subheader("Recent Workspace Activity")
    if not history:
        st.info("No modification requests recorded in this workspace yet.")
    else:
        for item in history[:5]:
            status_color = "🟢" if item["execution_status"] == "SUCCESS" else "🔴"
            st.markdown(f"{status_color} **{item['instruction']}** — *{item['planned_operation']}* ({item['created_at']})")
