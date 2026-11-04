"""
FastAPI Backend Application for DATA CENTRIC AGENTIC AI.

Exposes RESTful endpoints for:
- Health check: GET /health and GET /
- Dashboard Metrics: GET /api/v1/history/metrics
- History Query: GET /api/v1/history
- Document Listing & Upload: GET/POST /api/v1/documents
- Ask AI Query: POST /api/v1/query
- Document Modification: POST /api/v1/modify

Enables Streamlit (port 8501) and any client to communicate with the Python backend on port 8000.
"""

from fastapi import FastAPI, HTTPException, Header, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from database.db_manager import get_db_connection, init_database
from history.history_manager import get_user_history, record_history_entry
from config import APP_MODE, IS_DEMO_MODE

# Initialize FastAPI App
api_app = FastAPI(
    title="Data Centric Agentic AI Backend API",
    version="1.0.0",
    description="Privacy-Aware Document Intelligence, RAG, and Verified Document Modification API"
)

# Enable CORS so Streamlit on port 8501 can communicate with port 8000
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup hook to initialize database tables
@api_app.on_event("startup")
def startup_event():
    init_database()


# -------------------------------------------------------------
# 1. Health Check Endpoints
# -------------------------------------------------------------
@api_app.get("/health")
@api_app.get("/")
def health_check():
    """
    Standard health check endpoint to verify backend status.
    """
    return {
        "status": "healthy",
        "service": "Data Centric Agentic AI Backend",
        "port": 8000,
        "app_mode": APP_MODE,
        "database_connected": True
    }


# -------------------------------------------------------------
# 2. Dashboard Metrics Endpoint (/api/v1/history/metrics)
# -------------------------------------------------------------
@api_app.get("/api/v1/history/metrics")
def get_dashboard_metrics(
    user_id: Optional[int] = Query(default=None, description="Optional user ID filter"),
    x_user_id: Optional[str] = Header(default=None)
):
    """
    Returns high-level statistics for the dashboard:
    - total_documents: Count of uploaded documents
    - total_versions: Count of committed versions
    - successful_modifications: Count of successful modifications
    - failed_modifications: Count of failed modifications
    - recent_requests: List of recent audit log entries
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Determine user filter if passed
    effective_user_id = user_id
    if effective_user_id is None and x_user_id and x_user_id.isdigit():
        effective_user_id = int(x_user_id)

    if effective_user_id is not None:
        cursor.execute("SELECT COUNT(*) as count FROM documents WHERE user_id = ?;", (effective_user_id,))
        doc_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM document_versions WHERE user_id = ?;", (effective_user_id,))
        version_count = cursor.fetchone()["count"]

        history = get_user_history(effective_user_id)
    else:
        # Global metrics across the system
        cursor.execute("SELECT COUNT(*) as count FROM documents;")
        doc_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM document_versions;")
        version_count = cursor.fetchone()["count"]

        cursor.execute("SELECT * FROM modification_history ORDER BY created_at DESC LIMIT 20;")
        history = [dict(r) for r in cursor.fetchall()]

    conn.close()

    success_count = sum(1 for h in history if h.get("execution_status") == "SUCCESS")
    failed_count = sum(1 for h in history if h.get("execution_status") == "FAILED")

    return {
        "status": "success",
        "backend_online": True,
        "metrics": {
            "total_documents": doc_count,
            "total_versions": version_count,
            "successful_modifications": success_count,
            "failed_modifications": failed_count,
            "total_requests": len(history)
        },
        "recent_requests": history[:5]
    }


# -------------------------------------------------------------
# 3. Modification History Endpoints (/api/v1/history)
# -------------------------------------------------------------
@api_app.get("/api/v1/history")
def get_history(
    user_id: int = Query(default=1, description="Authenticated user ID"),
    doc_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default="ALL")
):
    """
    Returns modification request audit trail for the user.
    """
    history_entries = get_user_history(user_id=user_id, doc_id=doc_id, status_filter=status)
    return {
        "status": "success",
        "count": len(history_entries),
        "history": history_entries
    }


# -------------------------------------------------------------
# 4. Document Listing Endpoint (/api/v1/documents)
# -------------------------------------------------------------
@api_app.get("/api/v1/documents")
def list_documents(user_id: int = Query(default=1)):
    """
    Lists documents belonging to the user.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT doc_id, user_id, original_filename, extension, current_version, file_size_bytes, uploaded_at
    FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC;
    """, (user_id,))
    docs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"status": "success", "total": len(docs), "documents": docs}


# -------------------------------------------------------------
# 5. Query / RAG Endpoint (/api/v1/query)
# -------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    user_id: int = 1
    target_doc_id: Optional[str] = None

@api_app.post("/api/v1/query")
def api_query_documents(payload: QueryRequest):
    """
    Performs semantic retrieval across document chunks and returns grounded response.
    """
    from rag.retrieval import retrieve_context, generate_rag_answer
    chunks = retrieve_context(
        user_id=payload.user_id,
        query=payload.query,
        target_doc_id=payload.target_doc_id,
        top_k=4
    )
    res = generate_rag_answer(payload.query, chunks)
    return {
        "status": "success",
        "query": payload.query,
        "answer": res["answer"],
        "citations": res["citations"],
        "source_count": res["source_count"]
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 65)
    print("  Starting Data Centric Agentic AI - FastAPI Backend")
    print("  Listening on: http://127.0.0.1:8000")
    print("  Health check: http://127.0.0.1:8000/health")
    print("  Metrics API : http://127.0.0.1:8000/api/v1/history/metrics")
    print("=" * 65)
    uvicorn.run("server:api_app", host="127.0.0.1", port=8000, reload=False)

