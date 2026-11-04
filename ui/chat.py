"""
UI Question Answering (RAG Chat) Component.
Provides individual and workspace search with strict citations,
external Gemini processing toggle, and privacy notifications.
"""

import streamlit as st
from database.db_manager import get_db_connection
from rag.retrieval import retrieve_context, generate_rag_answer
from auth.gemini_client import get_gemini_api_key, get_gemini_model
from config import IS_DEMO_MODE


def render_chat(user_id: int):
    st.markdown("## 💬 Ask AI — Retrieval-Augmented Generation")

    # Privacy & Processing Notice
    with st.expander("🛡️ Privacy & External Processing Notice", expanded=False):
        st.markdown("""
        - Local vector retrieval runs **entirely in-memory on your computer**.
        - Embeddings are generated locally using **SentenceTransformers**.
        - If Gemini is enabled, only the **retrieved excerpts** needed to answer your question are transmitted to Google Gemini.
        - **Consent**: Private user documents are never sent without your explicit approval.
        """)

    # Cloud Consent checkbox in chat
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        cloud_consent = st.checkbox(
            "Allow Gemini Cloud Synthesis for this session (Excerpts only)",
            value=st.session_state.get("cloud_consent", False),
            help="Enables Google Gemini LLM to generate smooth natural language answers based on retrieved context."
        )
        st.session_state["cloud_consent"] = cloud_consent

    with col_c2:
        has_key = bool(get_gemini_api_key())
        if has_key and cloud_consent:
            st.caption(f"🤖 Engine: **Gemini ({get_gemini_model()})**")
        elif has_key and not cloud_consent and not IS_DEMO_MODE:
            st.caption("🔒 Engine: **Local (Consent required)**")
        else:
            st.caption("🖥️ Engine: **Local Offline Fallback**")

    # Load files for filter dropdown
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT doc_id, original_filename FROM documents WHERE user_id = ?;", (user_id,))
    docs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Search Mode Selector
    search_options = {"All Workspace Documents (Workspace Search)": None}
    for d in docs:
        search_options[f"Document: {d['original_filename']} ({d['doc_id']})"] = d["doc_id"]

    selected_label = st.selectbox("Search Scope:", list(search_options.keys()))
    target_doc_id = search_options[selected_label]

    # Initialize session state for messages
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat stream
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("engine"):
                st.caption(f"Generated via: `{msg['engine']}`")
            if msg.get("citations"):
                with st.expander("📌 Source Citations & References", expanded=False):
                    for cit in msg["citations"]:
                        st.markdown(f"**[Source {cit['source_id']}] {cit['filename']}** — `{cit['location']}`")
                        st.caption(f"\"{cit['excerpt']}\"")

    # Chat input
    user_query = st.chat_input("Ask a question about your documents...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Retrieval & Answering
        with st.chat_message("assistant"):
            with st.spinner("Retrieving semantic evidence and formulating response..."):
                retrieved = retrieve_context(user_id, user_query, target_doc_id=target_doc_id, top_k=4)
                res = generate_rag_answer(
                    query=user_query,
                    retrieved_chunks=retrieved,
                    user_consented_to_cloud=cloud_consent,
                    is_demo_mode=IS_DEMO_MODE
                )

                st.markdown(res["answer"])
                st.caption(f"Generated via: `{res.get('engine', 'Local')}`")

                if res.get("citations"):
                    with st.expander("📌 Source Citations & References", expanded=True):
                        for cit in res["citations"]:
                            st.markdown(f"**[Source {cit['source_id']}] {cit['filename']}** — `{cit['location']}`")
                            st.caption(f"\"{cit['excerpt']}\"")

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": res["answer"],
            "citations": res.get("citations", []),
            "engine": res.get("engine")
        })

    if st.button("🧹 Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()
