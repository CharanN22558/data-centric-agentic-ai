"""
Main Application Entrypoint for Streamlit.

Launches the complete privacy-aware Agentic AI application:
- Cloud Mode (Supabase Auth, PostgreSQL RLS, pgvector, Private Storage)
- Local Mode (Local Argon2id auth, local AES-256-GCM, SQLite)
"""

import streamlit as st
from config import APP_MODE, IS_CLOUD_MODE, IS_LOCAL_MODE, IS_DEMO_MODE, DEFAULT_EXECUTION_MODE, SAMPLE_DATA_DIR
from database.cloud_db import is_supabase_configured
from auth.authentication import (
    supabase_sign_in, supabase_sign_up, supabase_sign_out, supabase_reset_password,
    supabase_refresh_session, register_user, authenticate_user
)
from database.repository import get_document_repository
from ui.dashboard import render_dashboard
from ui.documents import render_documents
from ui.chat import render_chat
from ui.modifications import render_modifications
from ui.history import render_history
from ui.settings import render_settings

# Configure page layout
st.set_page_config(
    page_title="DATA CENTRIC AGENTIC AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "jwt_token" not in st.session_state:
    st.session_state.jwt_token = ""
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = ""
if "user_dek" not in st.session_state:
    st.session_state.user_dek = None
if "execution_mode" not in st.session_state:
    st.session_state.execution_mode = DEFAULT_EXECUTION_MODE


# -------------------------------------------------------------
# 1. Unauthenticated Screen (Login / Register / Setup Check)
# -------------------------------------------------------------
if not st.session_state.authenticated:
    st.title("🛡️ DATA CENTRIC AGENTIC AI")
    st.caption("Privacy-Aware Multi-User Agentic AI for Multi-Format Documents (TXT, XLSX, PDF)")

    # Check Cloud Configuration
    if IS_CLOUD_MODE and not is_supabase_configured():
        st.warning("⚠️ **Cloud Configuration Required**: Supabase credentials are not yet configured.")
        st.info("""
        To activate full multi-user cloud features:
        1. Open **Render Dashboard** -> Your Web Service -> **Environment Variables**.
        2. Set **`SUPABASE_URL`** and **`SUPABASE_ANON_KEY`** from your Supabase project settings.
        3. Set **`APP_ENCRYPTION_MASTER_KEY`** (a secure random string).
        4. Refer to `CLOUD_SETUP_GUIDE.md` for complete step-by-step instructions.
        """)
        st.stop()

    if IS_CLOUD_MODE:
        tab_login, tab_register, tab_reset = st.tabs(["🔐 Sign In", "📝 Create Account", "🔄 Reset Password"])

        with tab_login:
            st.subheader("Cloud Multi-User Login")
            l_email = st.text_input("Email Address", key="login_email")
            l_password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Sign In", type="primary"):
                if not l_email or not l_password:
                    st.error("Please provide both email and password.")
                else:
                    ok, msg, data = supabase_sign_in(l_email, l_password)
                    if ok and data:
                        st.session_state.authenticated = True
                        st.session_state.user_id = data["user_id"]
                        st.session_state.username = data["display_name"]
                        st.session_state.jwt_token = data["access_token"]
                        st.session_state.refresh_token = data.get("refresh_token", "")
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_register:
            st.subheader("Create Protected Account")
            st.caption("Each account receives an isolated, private workspace protected by PostgreSQL Row Level Security.")
            r_email = st.text_input("Email Address", key="reg_email")
            r_name = st.text_input("Display Name", key="reg_name")
            r_password = st.text_input("Password (min 6 characters)", type="password", key="reg_pass")
            if st.button("Create Account"):
                if not r_email or not r_password:
                    st.error("Please fill in email and password.")
                else:
                    ok, msg, data = supabase_sign_up(r_email, r_password, display_name=r_name)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        with tab_reset:
            st.subheader("Reset Password")
            reset_email = st.text_input("Enter your registered email", key="reset_email")
            if st.button("Send Reset Link"):
                ok, msg = supabase_reset_password(reset_email)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    else:
        # Local Private Mode
        from database.db_manager import init_database
        init_database()

        tab_login, tab_register = st.tabs(["🔐 Login to Local Workspace", "📝 Register Local Account"])
        with tab_login:
            st.subheader("Local Login")
            l_user = st.text_input("Username", key="local_login_user")
            l_pass = st.text_input("Password", type="password", key="local_login_pass")
            if st.button("Log In", type="primary"):
                uid, uname, dek, msg = authenticate_user(l_user, l_pass)
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
            st.subheader("Register Local Account")
            r_user = st.text_input("Choose Username", key="local_reg_user")
            r_pass = st.text_input("Choose Password", type="password", key="local_reg_pass")
            if st.button("Register"):
                ok, msg = register_user(r_user, r_pass)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.stop()


# -------------------------------------------------------------
# 2. Authenticated Application Layout
# -------------------------------------------------------------

# Sidebar Navigation & User Info
with st.sidebar:
    st.title("🛡️ AGENTIC AI")
    st.caption("Data Centric Document Intelligence")
    st.markdown("---")

    st.markdown(f"👤 **User:** `{st.session_state.username}`")
    mode_label = "🌐 Cloud (Supabase)" if IS_CLOUD_MODE else "🔒 Local Private"
    st.markdown(f"⚙️ **Mode:** {mode_label}")
    st.markdown(f"🛡️ **Policy:** Confirmation Required")

    st.markdown("---")
    menu = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📁 Documents",
            "💬 Ask AI (RAG)",
            "✏️ Modifications",
            "📜 Request History",
            "⚙️ Settings"
        ]
    )

    st.markdown("---")
    if st.button("🚪 Sign Out"):
        if IS_CLOUD_MODE and st.session_state.jwt_token:
            supabase_sign_out(st.session_state.jwt_token)
        st.session_state.clear()
        st.rerun()

# Render Selected View
repo = get_document_repository(st.session_state)

if menu == "📊 Dashboard":
    render_dashboard(repo, st.session_state)
elif menu == "📁 Documents":
    render_documents(repo, st.session_state)
elif menu == "💬 Ask AI (RAG)":
    render_chat(repo, st.session_state)
elif menu == "✏️ Modifications":
    render_modifications(repo, st.session_state)
elif menu == "📜 Request History":
    render_history(repo, st.session_state)
elif menu == "⚙️ Settings":
    render_settings(st.session_state)
