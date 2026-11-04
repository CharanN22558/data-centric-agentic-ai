"""
UI Document Modification Studio Component.
Handles natural-language modification requests, preview plan, confirmation, and version download.
"""

import streamlit as st
from database.db_manager import get_db_connection
from agents.graph import agent_graph
from modifications.planner import generate_structured_plan


def render_modifications(user_id: int, user_dek: bytes, execution_mode: str):
    st.markdown("## ✏️ Natural-Language Document Modification Studio")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT doc_id, original_filename, extension, current_version FROM documents WHERE user_id = ?;", (user_id,))
    docs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not docs:
        st.info("No documents found in this workspace. Upload a file to enable modifications.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        doc_choice = st.selectbox(
            "Select Target Document:",
            docs,
            format_func=lambda d: f"{d['original_filename']} (v{d['current_version']})"
        )
        st.info(f"Target format: `{doc_choice['extension'].upper()}` | Current Version: `v{doc_choice['current_version']}`")

    with col2:
        instruction = st.text_area(
            "Enter Natural Language Modification Instruction:",
            placeholder="e.g. 'Remove duplicate entries' or 'Update cell B2 with 90000' or 'Append notes: Reviewed by Lead'"
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

    # Display Plan and Approval
    if "pending_plan" in st.session_state and st.session_state.get("pending_doc", {}).get("doc_id") == doc_choice["doc_id"]:
        plan = st.session_state["pending_plan"]
        st.markdown("---")
        st.markdown("### 📋 Structured Execution Plan")
        st.json(plan)
        st.markdown(f"**Proposed Action**: {plan.get('description', '')}")

        # Check execution mode
        is_auto = (execution_mode == "AUTOMATIC")
        if is_auto:
            st.warning("⚡ Automatic Execution Mode is active: Changes will execute immediately without confirmation.")

        c_confirm, c_cancel = st.columns([1, 1])
        with c_confirm:
            btn_label = "Confirm & Execute Modification" if not is_auto else "Execute Automatically"
            if st.button(f"✅ {btn_label}", type="primary"):
                with st.spinner("Executing modification, running validation, and saving new version..."):
                    # Invoke LangGraph
                    init_state = {
                        "user_id": user_id,
                        "user_dek": user_dek,
                        "user_input": st.session_state["pending_instruction"],
                        "target_doc_id": doc_choice["doc_id"],
                        "target_filename": doc_choice["original_filename"],
                        "execution_approved": True,  # Approved by user confirmation
                        "modification_plan": plan
                    }
                    res = agent_graph.invoke(init_state)

                    if res.get("execution_status") == "SUCCESS":
                        st.success(res.get("final_answer"))
                        del st.session_state["pending_plan"]
                        st.rerun()
                    else:
                        st.error(res.get("final_answer") or res.get("error_message"))

        with c_cancel:
            if st.button("❌ Cancel Request"):
                del st.session_state["pending_plan"]
                st.info("Modification request cancelled.")
                st.rerun()

