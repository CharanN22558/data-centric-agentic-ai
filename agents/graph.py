"""
LangGraph Agent Workflow Module.

Assembles the full multi-node graph:
1. receive_input
2. classify_intent
3. identify_target_document
4. Conditional branch:
   - If QUESTION -> retrieve_context -> generate_answer
   - If MODIFICATION -> generate_plan -> check_approval -> execute_operation -> validate -> commit -> record_history
   - If CLARIFICATION / UNSUPPORTED -> return explanation
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from agents.state import AgentWorkflowState
from agents.router import classify_user_intent
from rag.retrieval import retrieve_context, generate_rag_answer
from modifications.planner import generate_structured_plan
from modifications.executor import execute_plan
from modifications.validator import validate_modification_output
from modifications.version_control import read_decrypted_document, commit_new_version
from history.history_manager import record_history_entry


def node_receive_input(state: AgentWorkflowState) -> Dict[str, Any]:
    """Receives user input and initializes processing parameters."""
    return {"error_message": None}


def node_classify_intent(state: AgentWorkflowState) -> Dict[str, Any]:
    """Classifies user request into Question, Modification, Clarification, or Unsupported."""
    res = classify_user_intent(state["user_input"])
    return {
        "intent": res["intent"],
        "confidence": res["confidence"],
        "intent_reasoning": res["reasoning"]
    }


def route_intent_decision(state: AgentWorkflowState) -> str:
    """Conditional edge router based on intent classification."""
    intent = state.get("intent", "QUESTION")
    if intent == "QUESTION":
        return "node_rag_pipeline"
    elif intent == "MODIFICATION":
        return "node_plan_modification"
    elif intent == "CLARIFICATION":
        return "node_clarification_response"
    else:
        return "node_unsupported_response"


def node_rag_pipeline(state: AgentWorkflowState) -> Dict[str, Any]:
    """Retrieves evidence from ephemeral ChromaDB and generates answer."""
    chunks = retrieve_context(
        user_id=state["user_id"],
        query=state["user_input"],
        target_doc_id=state.get("target_doc_id"),
        top_k=4
    )
    res = generate_rag_answer(state["user_input"], chunks)
    return {
        "retrieved_context": chunks,
        "final_answer": res["answer"],
        "summary_result": f"Answered question using {res['source_count']} citations."
    }


def node_plan_modification(state: AgentWorkflowState) -> Dict[str, Any]:
    """Generates structured execution plan for target document."""
    fname = state.get("target_filename") or "document.txt"
    plan = generate_structured_plan(state["user_input"], fname)
    return {"modification_plan": plan}


def route_approval_decision(state: AgentWorkflowState) -> str:
    """Checks if modification execution has been approved by the user."""
    if state.get("execution_approved", False):
        return "node_execute_modification"
    return "node_await_confirmation"


def node_await_confirmation(state: AgentWorkflowState) -> Dict[str, Any]:
    """Halts execution so user can review the proposed plan in the UI."""
    return {
        "execution_status": "PENDING_CONFIRMATION",
        "final_answer": f"Modification plan generated: {state.get('modification_plan', {}).get('description', '')}. Awaiting user confirmation."
    }


def node_execute_modification(state: AgentWorkflowState) -> Dict[str, Any]:
    """Decrypts working copy, executes tool, validates, commits new version."""
    user_id = state["user_id"]
    user_dek = state["user_dek"]
    doc_id = state["target_doc_id"]
    plan = state["modification_plan"]

    try:
        # 1. Decrypt working copy
        orig_bytes, filename, prev_ver = read_decrypted_document(user_id, user_dek, doc_id)

        # 2. Execute plan
        mod_bytes, summary = execute_plan(plan, orig_bytes)

        # 3. Validate output
        valid, val_msg = validate_modification_output(filename, orig_bytes, mod_bytes)
        if not valid:
            record_history_entry(
                user_id=user_id,
                doc_id=doc_id,
                instruction=state["user_input"],
                ai_interpretation=plan.get("description", ""),
                intent_classification="MODIFICATION",
                planned_operation=plan.get("action", ""),
                execution_status="FAILED",
                validation_result=val_msg,
                previous_version=prev_ver,
                new_version=None,
                summary_result="Validation failed."
            )
            return {
                "execution_status": "FAILED",
                "validation_result": val_msg,
                "error_message": val_msg,
                "final_answer": f"Modification rejected: {val_msg}"
            }

        # 4. Commit as new version
        new_ver, commit_msg = commit_new_version(
            user_id=user_id,
            user_dek=user_dek,
            doc_id=doc_id,
            filename=filename,
            new_bytes=mod_bytes,
            comment=f"Agent: {plan.get('description', '')}"
        )

        # 5. Record history
        record_history_entry(
            user_id=user_id,
            doc_id=doc_id,
            instruction=state["user_input"],
            ai_interpretation=plan.get("description", ""),
            intent_classification="MODIFICATION",
            planned_operation=plan.get("action", ""),
            execution_status="SUCCESS",
            validation_result=val_msg,
            previous_version=prev_ver,
            new_version=new_ver,
            summary_result=summary
        )

        return {
            "execution_status": "SUCCESS",
            "validation_result": val_msg,
            "previous_version": prev_ver,
            "new_version": new_ver,
            "summary_result": summary,
            "final_answer": f"Modification executed successfully! Saved as Version {new_ver}. ({summary})"
        }

    except Exception as e:
        return {
            "execution_status": "FAILED",
            "error_message": str(e),
            "final_answer": f"Execution error: {str(e)}"
        }


def node_clarification_response(state: AgentWorkflowState) -> Dict[str, Any]:
    return {
        "final_answer": f"Clarification required: {state.get('intent_reasoning', '')}",
        "execution_status": "CLARIFICATION_NEEDED"
    }


def node_unsupported_response(state: AgentWorkflowState) -> Dict[str, Any]:
    return {
        "final_answer": f"Operation rejected: {state.get('intent_reasoning', '')}",
        "execution_status": "REJECTED"
    }


def build_agent_graph() -> StateGraph:
    """Constructs the complete compiled LangGraph workflow."""
    workflow = StateGraph(AgentWorkflowState)

    # Add Nodes
    workflow.add_node("receive_input", node_receive_input)
    workflow.add_node("classify_intent", node_classify_intent)
    workflow.add_node("node_rag_pipeline", node_rag_pipeline)
    workflow.add_node("node_plan_modification", node_plan_modification)
    workflow.add_node("node_await_confirmation", node_await_confirmation)
    workflow.add_node("node_execute_modification", node_execute_modification)
    workflow.add_node("node_clarification_response", node_clarification_response)
    workflow.add_node("node_unsupported_response", node_unsupported_response)

    # Set Entry Point
    workflow.set_entry_point("receive_input")
    workflow.add_edge("receive_input", "classify_intent")

    # Conditional Branching on Intent
    workflow.add_conditional_edges(
        "classify_intent",
        route_intent_decision,
        {
            "node_rag_pipeline": "node_rag_pipeline",
            "node_plan_modification": "node_plan_modification",
            "node_clarification_response": "node_clarification_response",
            "node_unsupported_response": "node_unsupported_response",
        }
    )

    # Conditional Branching on User Confirmation Approval
    workflow.add_conditional_edges(
        "node_plan_modification",
        route_approval_decision,
        {
            "node_await_confirmation": "node_await_confirmation",
            "node_execute_modification": "node_execute_modification",
        }
    )

    # Terminal Edges
    workflow.add_edge("node_rag_pipeline", END)
    workflow.add_edge("node_await_confirmation", END)
    workflow.add_edge("node_execute_modification", END)
    workflow.add_edge("node_clarification_response", END)
    workflow.add_edge("node_unsupported_response", END)

    return workflow.compile()


# Global compiled agent graph
agent_graph = build_agent_graph()

