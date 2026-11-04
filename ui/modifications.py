"""
UI Document Modification Studio Component.

Handles natural-language modification requests, preview plan, confirmation,
and version commit using the unified repository.
"""

import streamlit as st
from modifications.planner import generate_structured_plan
from modifications.executor import execute_modification_plan
from rag.document_loader import load_and_chunk_document
from rag.vector_store import get_vector_store


def render_modifications(repo, session_state):
    st.markdown("## ✏️ Natural-Language Document Modification Studio")
    st.caption("Instruct the agentic engine to update, replace values, append notes, or clean data in TXT, Excel, and PDF files.")

    docs = repo.list_documents()
    if not docs:
        st.info("No documents found in your workspace. Please upload a document first.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        doc_choice = st.selectbox(
            "Select Target Document:",
            docs,
            format_func=lambda d: f"{d['original_filename']} (v{d['current_version']})"
        )
        st.info(f"Target Format: `{doc_choice['extension'].upper()}` | Current Version: `v{doc_choice['current_version']}`")

    with col2:
        instruction = st.text_area(
            "Enter Modification Instruction:",
            placeholder="e.g. 'Change the employee name Rahul to Charan.' or 'Replace remote hours with 9 AM to 5 PM'"
        )

    if st.button("🚀 Analyze & Generate Execution Plan"):
        if not instruction.strip():
            st.error("Please enter an instruction.")
            return

        with st.spinner("Analyzing instruction and verifying tool compatibility..."):
            plan = generate_structured_plan(instruction, doc_choice["original_filename"])
            st.session_state["pending_plan"] = plan
            st.session_state["pending_instruction"] = instruction
            st.session_state["pending_doc"] = doc_choice

    # Display Plan and Confirmation
    if "pending_plan" in st.session_state:
        plan = st.session_state["pending_plan"]
        inst = st.session_state["pending_instruction"]
        target_doc = st.session_state["pending_doc"]

        st.markdown("---")
        st.subheader("📋 Proposed Execution Plan")
        st.json(plan)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm & Execute Modification", type="primary"):
                with st.spinner("Executing modification, updating checksums, and committing new version..."):
                    # 1. Read existing bytes
                    current_bytes = repo.read_document_bytes(target_doc["doc_id"])
                    if not current_bytes:
                        st.error("Failed to read document bytes.")
                        return

                    # 2. Execute modification
                    success, modified_bytes, summary = execute_modification_plan(
                        current_bytes=current_bytes,
                        extension=target_doc["extension"],
                        plan=plan
                    )

                    prev_v = target_doc["current_version"]

                    if success and modified_bytes:
                        # 3. Create version
                        ok, msg, new_v = repo.create_version(target_doc["doc_id"], modified_bytes, summary)
                        if ok:
                            # 4. Record history
                            repo.record_history(
                                doc_id=target_doc["doc_id"],
                                instruction=inst,
                                interpretation=plan.get("details", summary),
                                operation=plan.get("action", "UPDATE"),
                                execution_status="SUCCESS",
                                validation_status="VALID",
                                summary_result=summary,
                                prev_v=prev_v,
                                new_v=new_v
                            )

                            # 5. Re-index vectors
                            try:
                                chunks = load_and_chunk_document(target_doc["original_filename"], modified_bytes)
                                vstore = get_vector_store(session_state)
                                vstore.add_chunks(target_doc["doc_id"], new_v, chunks)
                            except Exception as ex:
                                print(f"[REINDEX WARN]: {ex}")

                            st.success(f"Successfully created v{new_v}: {summary}")
                            del st.session_state["pending_plan"]
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        repo.record_history(
                            doc_id=target_doc["doc_id"],
                            instruction=inst,
                            interpretation=plan.get("details", summary),
                            operation=plan.get("action", "UNKNOWN"),
                            execution_status="FAILED",
                            validation_status="INVALID",
                            summary_result=summary,
                            prev_v=prev_v,
                            new_v=prev_v
                        )
                        st.error(f"Modification Failed: {summary}")

        with c2:
            if st.button("❌ Cancel Plan"):
                del st.session_state["pending_plan"]
                st.rerun()
