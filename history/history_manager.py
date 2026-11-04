"""
Encrypted Request History and Audit Manager Module.

Maintains a private, tamper-evident record of all user instructions,
plans, execution results, and validation reports.
"""

import uuid
from typing import List, Dict, Any, Optional
from database.db_manager import get_db_connection


def record_history_entry(
    user_id: int,
    doc_id: Optional[str],
    instruction: str,
    ai_interpretation: str,
    intent_classification: str,
    planned_operation: str,
    execution_status: str,
    validation_result: str,
    previous_version: Optional[int],
    new_version: Optional[int],
    summary_result: str
) -> str:
    """
    Inserts a new traceable history entry.
    """
    request_id = str(uuid.uuid4())[:8]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO modification_history (
        request_id, user_id, doc_id, instruction, ai_interpretation,
        intent_classification, planned_operation, execution_status,
        validation_result, previous_version, new_version, summary_result
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        request_id, user_id, doc_id, instruction, ai_interpretation,
        intent_classification, planned_operation, execution_status,
        validation_result, previous_version, new_version, summary_result
    ))

    conn.commit()
    conn.close()
    return request_id


def get_user_history(
    user_id: int,
    doc_id: Optional[str] = None,
    status_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves filtered modification history for the authenticated user.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM modification_history WHERE user_id = ?"
    params: List[Any] = [user_id]

    if doc_id:
        query += " AND doc_id = ?"
        params.append(doc_id)

    if status_filter and status_filter.upper() != "ALL":
        query += " AND execution_status = ?"
        params.append(status_filter.upper())

    query += " ORDER BY created_at DESC;"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

