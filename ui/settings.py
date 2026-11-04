"""
UI Settings & Privacy Controls Component.
Configures execution mode, Gemini API keys, connection testing, and privacy parameters.
"""

import streamlit as st
import os
from config import IS_DEMO_MODE, GEMINI_MODEL
from auth.gemini_client import (
    test_gemini_connection,
    get_gemini_api_key,
    get_gemini_model,
    STABLE_GEMINI_MODELS
)


def render_settings():
    st.markdown("## ⚙️ Application Settings & Privacy Controls")

    # Execution Mode Setting
    st.subheader("Agentic Execution Mode")
    current_mode = st.session_state.get("execution_mode", "CONFIRMATION")
    new_mode = st.radio(
        "Choose modification execution mode:",
        options=["CONFIRMATION", "AUTOMATIC"],
        index=0 if current_mode == "CONFIRMATION" else 1,
        help="CONFIRMATION mode requires you to review and confirm the proposed plan before execution. AUTOMATIC mode executes immediately after planning."
    )
    if new_mode != current_mode:
        st.session_state["execution_mode"] = new_mode
        st.success(f"Execution mode set to: **{new_mode}**")

    st.markdown("---")

    # Gemini API Settings & Status
    st.subheader("🤖 Google Gemini LLM Configuration")
    st.markdown("""
    Gemini is used for high-fidelity natural language synthesis across documents.
    - All vector retrieval runs locally on your machine.
    - The API key is stored securely in environment/memory and **never logged or displayed**.
    """)

    # Connection Status Indicator
    api_key_set = bool(get_gemini_api_key())
    if api_key_set:
        st.markdown(
            '<div style="padding: 8px 12px; border-radius: 8px; background-color: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #10B981; font-size: 13px; font-weight: 600; margin-bottom: 12px;">'
            '🟢 GEMINI API KEY DETECTED (Securely stored in environment)'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="padding: 8px 12px; border-radius: 8px; background-color: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #F59E0B; font-size: 13px; font-weight: 500; margin-bottom: 12px;">'
            '🟡 GEMINI API KEY NOT CONFIGURED (Using local deterministic engine)'
            '</div>',
            unsafe_allow_html=True
        )

    # Model Selection
    current_model = get_gemini_model()
    model_options = list(dict.fromkeys([current_model] + STABLE_GEMINI_MODELS))
    selected_model = st.selectbox(
        "Gemini Model Selection (GEMINI_MODEL):",
        options=model_options,
        index=0,
        help="Choose a stable, supported model. Recommended: gemini-2.5-flash or gemini-2.0-flash"
    )

    # API Key Input (Password field - never echoes plaintext)
    api_key_input = st.text_input(
        "Enter or Update Gemini API Key (GEMINI_API_KEY):",
        type="password",
        placeholder="Paste your key here (e.g. AIzaSy...)"
    )

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("💾 Save Gemini Configuration"):
            if api_key_input.strip():
                os.environ["GEMINI_API_KEY"] = api_key_input.strip()
            os.environ["GEMINI_MODEL"] = selected_model
            st.success(f"Configuration saved! Model set to: `{selected_model}`")
            st.rerun()

    with col_btn2:
        if st.button("🔍 Test Gemini Connection"):
            test_key = api_key_input.strip() or get_gemini_api_key()
            with st.spinner("Connecting to Google Gemini API..."):
                ok, msg, details = test_gemini_connection(api_key=test_key, model=selected_model)
                if ok:
                    st.success(f"✅ {msg}")
                    st.info(f"Available models accessible on your account: {details.get('available_models_count', 'N/A')}")
                else:
                    st.error(f"❌ {msg}")

    st.markdown("---")

    # Cloud Consent Toggle
    st.subheader("🛡️ External Cloud Transmission Consent")
    consent = st.checkbox(
        "I explicitly consent to transmitting document excerpts to Google Gemini for AI answer synthesis.",
        value=st.session_state.get("cloud_consent", False),
        help="In Private Mode, document excerpts will NOT be transmitted to Gemini unless this box is checked."
    )
    st.session_state["cloud_consent"] = consent
    if consent:
        st.caption("🟢 Consent granted: RAG queries will use Gemini when an API key is present.")
    else:
        st.caption("🔒 Zero cloud transmission: RAG queries will run strictly offline using local deterministic extraction.")

    st.markdown("---")

    # Privacy Checklist
    st.subheader("Security & Privacy Architecture Guarantee")
    st.markdown("""
    ✅ **AES-256-GCM Authenticated Encryption**: Active for all private documents and backups.  
    ✅ **Argon2id Key Derivation**: User keys derived with 64MB memory cost.  
    ✅ **Zero Plaintext Persistence to Cloud**: No private files sent to Render or Supabase.  
    ✅ **Ephemeral Vector Index**: ChromaDB indices destroyed upon shutdown or logout.  
    ✅ **Strict Multi-Tenant Isolation**: Verified at database and file system levels.  
    """)
