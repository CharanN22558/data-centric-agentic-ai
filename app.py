"""
Main Application Entrypoint for Streamlit.

Launches the complete privacy-aware Agentic AI application:
    streamlit run app.py
"""

import streamlit as st
from config import APP_MODE, IS_DEMO_MODE, DEFAULT_EXECUTION_MODE, SAMPLE_DATA_DIR
from database.db_manager import init_database
from auth.authentication import register_user, authenticate_user
from modifications.version_control import save_initial_document
from ui.dashboard import render_dashboard
from ui.documents import render_documents
from ui.chat import render_chat
from ui.modifications import render_modifications
from ui.history import render_history
from ui.settings import render_settings

# Configure page metadata & layout
st.set_page_config(
    page_title="DATA CENTRIC AGENTIC AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize local database tables
init_database()

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "user_dek" not in st.session_state:
    st.session_state.user_dek = None
if "execution_mode" not in st.session_state:
    st.session_state.execution_mode = DEFAULT_EXECUTION_MODE


def inject_demo_data(user_id: int, user_dek: bytes):
    """Loads synthetic demonstration documents into the session in DEMO mode."""
    if not st.session_state.get("demo_data_loaded", False):
        for fname in ["sample_employees.xlsx", "sample_report.pdf", "sample_notes.txt"]:
            fpath = SAMPLE_DATA_DIR / fname
            if fpath.exists():
                with open(fpath, "rb") as f:
                    content = f.read()
                save_initial_document(user_id, user_dek, f"demo_{fname[:4]}", fname, content)
        st.session_state["demo_data_loaded"] = True


# -------------------------------------------------------------
# Authentication / Login Flow
# -------------------------------------------------------------
if not st.session_state.authenticated:
    st.title("🛡️ DATA CENTRIC AGENTIC AI")
    st.caption("Privacy-Aware Agentic AI for Multi-Format Documents (TXT, XLSX, PDF)")

    if IS_DEMO_MODE:
        st.info("🌐 **Public Demonstration Mode Detected (Render)**: Real user registration is disabled. Click below to enter with synthetic demonstration documents.")
        if st.button("🚀 Enter Demonstration Workspace", type="primary"):
            uid, uname, dek, msg = authenticate_user("demo_user", "")
            st.session_state.authenticated = True
            st.session_state.user_id = uid
            st.session_state.username = uname
            st.session_state.user_dek = dek
            inject_demo_data(uid, dek)
            st.rerun()
    else:
        tab_login, tab_register = st.tabs(["🔐 Login to Local Workspace", "📝 Register Local Account"])

        with tab_login:
            st.subheader("Login")
            l_username = st.text_input("Username", key="login_user")
            l_password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In", type="primary"):
                uid, uname, dek, msg = authenticate_user(l_username, l_password)
                if uid:
                    st.session_state.authenticated = True
                    st.session_state.user_id = uid
                    st.session_state.username = uname
                    st.session_state.user_dek = dek
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with tab_register:
            st.subheader("Create Encrypted Local Account")
            st.caption("Your password derives your AES-256-GCM data key via Argon2id. Never lost or shared.")
            r_username = st.text_input("Choose Username", key="reg_user")
            r_password = st.text_input("Choose Password (min 6 chars)", type="password", key="reg_pass")
            r_confirm = st.text_input("Confirm Password", type="password", key="reg_conf")
            if st.button("Register Account"):
                if r_password != r_confirm:
                    st.error("Passwords do not match.")
                else:
                    success, msg = register_user(r_username, r_password)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

# -------------------------------------------------------------
# Main Authenticated Application Dashboard
# -------------------------------------------------------------
else:
    # Sidebar Navigation
    with st.sidebar:
        st.markdown("### 🛡️ AGENTIC AI")
        st.caption(f"User: **{st.session_state.username}** (`ID: {st.session_state.user_id}`)")
        st.markdown(f"Mode: `{APP_MODE.upper()}` | Exec: `{st.session_state.execution_mode}`")
        st.markdown("---")

        page = st.radio(
            "Navigate Workspace:",
            [
                "📊 Dashboard",
                "📁 Documents",
                "💬 Ask AI (RAG)",
                "✏️ Modify Documents",
                "📜 History & Rollback",
                "⚙️ Settings & Privacy"
            ]
        )

        st.markdown("---")
        if st.button("🚪 Log Out"):
            # Secure logout: clear session and in-memory DEK
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.user_dek = None
            st.rerun()

    # Page Routing
    u_id = st.session_state.user_id
    u_dek = st.session_state.user_dek

    if page == "📊 Dashboard":
        render_dashboard(u_id, st.session_state.username)
    elif page == "📁 Documents":
        render_documents(u_id, u_dek)
    elif page == "💬 Ask AI (RAG)":
        render_chat(u_id)
    elif page == "✏️ Modify Documents":
        render_modifications(u_id, u_dek, st.session_state.execution_mode)
    elif page == "📜 History & Rollback":
        render_history(u_id, u_dek)
    elif page == "⚙️ Settings & Privacy":
        render_settings()

