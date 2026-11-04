"""
UI Question Answering (RAG Chat) Component.

Supports individual document and entire workspace semantic search
using persistent pgvector in cloud mode or ChromaDB locally.
"""

import streamlit as st
from rag.retrieval import generate_rag_answer
from rag.vector_store import get_vector_store
from auth.gemini_client import get_gemini_api_key, get_gemini_model


def render_chat(repo, session_state):
    st.markdown("## 💬 Ask AI — Retrieval-Augmented Generation")
    st.caption("Perform semantic search with exact source citations across your private documents.")

    # Privacy & Consent Notice
    with st.expander("🛡️ Privacy & External AI Processing Notice", expanded=False):
        st.markdown("""
        - **Vector Search**: Runs securely in your private workspace.
        - **Google Gemini**: Only retrieved context excerpts are sent to Gemini if enabled.
        - **Consent**: Processing requires your explicit toggle below.
        """)

    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        cloud_consent = st.checkbox(
            "Enable Google Gemini Cloud Synthesis (Optional)",
            value=session_state.get("cloud_consent", False),
            help="Generates fluent conversational answers using retrieved context."
        )
        session_state["cloud_consent"] = cloud_consent

    with col_c2:
        has_key = bool(get_gemini_api_key())
        if has_key and cloud_consent:
            st.caption(f"🤖 Engine: **Gemini ({get_gemini_model()})**")
        elif has_key and not cloud_consent:
            st.caption("🔒 Engine: **Local Heuristic (Consent Disabled)**")
        else:
            st.caption("🖥️ Engine: **Local Offline Heuristic**")

    # Target Document Choice
    docs = repo.list_documents()
    doc_options = {"🌐 Entire Workspace (All Documents)": None}
    for d in docs:
        doc_options[f"📄 {d['original_filename']} (v{d['current_version']})"] = d["doc_id"]

    selected_label = st.selectbox("Search Target:", list(doc_options.keys()))
    selected_doc_id = doc_options[selected_label]

    query = st.text_input("Ask a question about your documents:", placeholder="e.g. 'What are the remote work policy hours?'")

    if st.button("🔍 Search & Answer", type="primary"):
        if not query.strip():
            st.error("Please enter a question.")
            return

        with st.spinner("Searching vector index and retrieving context..."):
            vstore = get_vector_store(session_state)
            retrieved_chunks = vstore.search(query, top_k=4, doc_id=selected_doc_id)

            if not retrieved_chunks:
                st.warning("No relevant passages found in the selected documents.")
                return

            # Format context
            context_blocks = []
            for idx, c in enumerate(retrieved_chunks):
                context_blocks.append(f"[Source {idx+1} | {c.get('metadata', '')}]:\n{c['text']}")

            full_context = "\n\n".join(context_blocks)
            answer = generate_rag_answer(query, full_context, cloud_consent=cloud_consent)

            st.markdown("### Answer")
            st.markdown(answer)

            st.markdown("---")
            st.markdown("### Retrieved Sources")
            for idx, c in enumerate(retrieved_chunks):
                with st.expander(f"Source {idx+1} (Relevance: {round(c.get('similarity', 0.0), 3)})", expanded=False):
                    st.write(c["text"])
