"""
UI Dashboard Component.
Displays metrics, activity statistics, privacy status, and mode info.
Connects to backend on port 8000 (http://127.0.0.1:8000/api/v1/history/metrics)
with automatic fallback to local database query if backend is starting up.
"""

import streamlit as st
import requests
from database.db_manager import get_db_connection
from history.history_manager import get_user_history
from config import IS_DEMO_MODE

BACKEND_API_BASE = "http://127.0.0.1:8000"


def fetch_backend_metrics(user_id: int):
    """
    Attempts to fetch dashboard metrics from the Python FastAPI backend on port 8000.
    Returns: (is_online, metrics_dict, recent_requests)
    """
    try:
        url = f"{BACKEND_API_BASE}/api/v1/history/metrics?user_id={user_id}"
        resp = requests.get(url, timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            return True, data.get("metrics", {}), data.get("recent_requests", [])
    except Exception:
        pass
    return False, None, None


def render_dashboard(user_id: int, username: str):
    st.markdown("## 📊 System Overview & Workspace Metrics")

    # Mode banner
    if IS_DEMO_MODE:
        st.warning("⚠️ **Running in Public Demonstration Mode (Render)**: Real user uploads & private registration are disabled. Exploring synthetic sample files only.")
    else:
        st.success("🔒 **Local Private Mode Active**: AES-256-GCM encryption enabled. SQLite metadata local. In-memory ephemeral ChromaDB index active.")

    # Check Backend Status on port 8000
    backend_online, api_metrics, api_requests = fetch_backend_metrics(user_id)

    if backend_online and api_metrics:
        st.markdown(
            '<div style="padding: 8px 12px; border-radius: 8px; background-color: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #10B981; font-size: 13px; font-weight: 600; margin-bottom: 12px;">'
            '🟢 BACKEND ONLINE — Connected to Python API at http://127.0.0.1:8000'
            '</div>',
            unsafe_allow_html=True
        )
        doc_count = api_metrics.get("total_documents", 0)
        version_count = api_metrics.get("total_versions", 0)
        success_count = api_metrics.get("successful_modifications", 0)
        failed_count = api_metrics.get("failed_modifications", 0)
        history = api_requests
    else:
        # Graceful fallback: retrieve directly from local SQLite
        st.markdown(
            '<div style="padding: 8px 12px; border-radius: 8px; background-color: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #F59E0B; font-size: 13px; font-weight: 500; margin-bottom: 12px;">'
            '🟡 Backend server on port 8000 is not running yet. Displaying local workspace metrics. (Start backend with: <code>python server.py</code>)'
            '</div>',
            unsafe_allow_html=True
        )
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM documents WHERE user_id = ?", (user_id,))
        doc_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM document_versions WHERE user_id = ?", (user_id,))
        version_count = cursor.fetchone()["count"]
        conn.close()

        history = get_user_history(user_id)
        success_count = sum(1 for h in history if h.get("execution_status") == "SUCCESS")
        failed_count = sum(1 for h in history if h.get("execution_status") == "FAILED")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Documents", doc_count)
    with col2:
        st.metric("Committed Versions", version_count)
    with col3:
        st.metric("Successful Edits", success_count)
    with col4:
        st.metric("Failed / Rejected", failed_count)

    st.markdown("---")

    # Recent activity
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.subheader("Recent Agentic Requests")
        if history:
            for item in history[:5]:
                status = item["execution_status"]
                badge = "🟢" if status == "SUCCESS" else "🔴" if status == "FAILED" else "🟡"
                st.markdown(f"**{badge} {item['instruction']}**")
                st.caption(f"Target: {item['doc_id']} | Action: {item['planned_operation']} | Time: {item['created_at']}")
        else:
            st.info("No requests executed yet. Upload a document and try asking a question or requesting an edit.")

    with col_b:
        st.subheader("Security & Privacy Status")
        st.markdown("""
        - **Data Encryption**: `AES-256-GCM` (256-bit key)
        - **KDF**: `Argon2id` (Password-derived KEK)
        - **Vector Index**: In-memory ephemeral `ChromaDB`
        - **Backend API**: `FastAPI` (Port 8000)
        - **Frontend UI**: `Streamlit` (Port 8501)
        """)
