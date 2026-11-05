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
                chunk_text = c.get("text", "")
                chunk_meta = c.get("metadata", {})
                context_blocks.append({
                    "filename": chunk_meta.get("filename", selected_label if selected_doc_id else "Document"),
                    "location": chunk_meta.get("location_label") or chunk_meta.get("sheet") or f"Chunk {idx+1}",
                    "text": chunk_text
                })

            rag_result = generate_rag_answer(
                query=query,
                retrieved_chunks=context_blocks,
                user_consented_to_cloud=cloud_consent,
                is_demo_mode=False
            )
            answer_text = rag_result.get("answer", "")
            engine_used = rag_result.get("engine", "Local")

            st.markdown("### Answer")
            st.caption(f"Engine: `{engine_used}`")
            st.markdown(answer_text)

            st.markdown("---")
            st.markdown("### Retrieved Sources")
            citations = rag_result.get("citations", [])
            if citations:
                for cite in citations:
                    with st.expander(f"Source {cite['source_id']}: {cite['filename']} ({cite['location']})", expanded=False):
                        st.write(cite["excerpt"])
            else:
                for idx, c in enumerate(retrieved_chunks):
                    with st.expander(f"Source {idx+1} (Relevance: {round(c.get('similarity', 0.0), 3)})", expanded=False):
                        st.write(c["text"])
