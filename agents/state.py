"""
Agentic State Schema for LangGraph.

Defines the typed dictionary passed between nodes in the workflow.
"""

from typing import TypedDict, List, Dict, Any, Optional


class AgentWorkflowState(TypedDict):
    # User and session info
    user_id: int
    user_dek: bytes

    # Request and routing
    user_input: str
    target_doc_id: Optional[str]
    target_filename: Optional[str]
    intent: str  # "QUESTION", "MODIFICATION", "CLARIFICATION", "UNSUPPORTED_OPERATION"
    confidence: float
    intent_reasoning: str

    # QA / RAG artifacts
    retrieved_context: List[Dict[str, Any]]
    final_answer: Optional[str]

    # Modification artifacts
    modification_plan: Optional[Dict[str, Any]]
    execution_approved: bool
    execution_status: str  # "PENDING", "SUCCESS", "FAILED", "ROLLED_BACK"
    validation_result: Optional[str]
    previous_version: Optional[int]
    new_version: Optional[int]
    summary_result: Optional[str]

    # Error handling
    error_message: Optional[str]

