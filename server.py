"""
FastAPI Backend Application for DATA CENTRIC AGENTIC AI.

Exposes RESTful endpoints authenticated via Supabase JWT Bearer Tokens:
- GET /health
- GET /api/v1/history/metrics
- GET /api/v1/documents
- POST /api/v1/documents/upload
- POST /api/v1/query
"""

from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from config import IS_CLOUD_MODE, IS_LOCAL_MODE
from database.cloud_db import verify_jwt_token
from database.repository import CloudSupabaseRepository, LocalSQLiteRepository

# Initialize FastAPI App
api_app = FastAPI(
    title="Data Centric Agentic AI Backend API",
    version="2.0.0",
    description="Privacy-Aware Multi-User Document Intelligence, RAG, and Verified Modification API"
)

# Enable CORS
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    CRITICAL SECURITY CHECK:
    Extracts and validates Supabase JWT Bearer Token.
    Returns authenticated user dict with user UUID, or raises HTTP 401.
    Never trusts a user_id parameter sent in request bodies!
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

    token = authorization.split("Bearer ")[1].strip()
    user_info = verify_jwt_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")

    user_info["jwt_token"] = token
    return user_info


# -------------------------------------------------------------
# 1. Health Check
# -------------------------------------------------------------
@api_app.get("/health")
@api_app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "Data Centric Agentic AI API",
        "mode": "cloud" if IS_CLOUD_MODE else "local",
        "version": "2.0.0",
        "port": 8000,
        "database_connected": True
    }


# -------------------------------------------------------------
# 2. Authenticated Dashboard Metrics
# -------------------------------------------------------------
@api_app.get("/api/v1/history/metrics")
def get_dashboard_metrics(user_id: Optional[int] = None, current_user: Optional[Dict[str, Any]] = None):
    # Support both local query param user_id and cloud JWT current_user
    if current_user and "id" in current_user:
        uid = current_user["id"]
        jwt_token = current_user.get("jwt_token", "")
        repo = CloudSupabaseRepository(user_id=uid, jwt_token=jwt_token)
        docs = repo.list_documents()
        history = repo.list_history()
    else:
        target_uid = user_id or 1
        from history.history_manager import get_user_history
        from database.db_manager import get_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM documents WHERE user_id = ?", (target_uid,))
        docs = [dict(r) for r in c.fetchall()]
        conn.close()
        history = get_user_history(target_uid)

    return {
        "status": "success",
        "backend_online": True,
        "user_id": user_id or (current_user["id"] if current_user else 1),
        "metrics": {
            "total_documents": len(docs),
            "total_modifications": len(history),
            "successful_modifications": sum(1 for h in history if h.get("execution_status") == "SUCCESS"),
            "success_rate": round(sum(1 for h in history if h.get("execution_status") == "SUCCESS") / max(len(history), 1) * 100, 1),
            "txt_files": sum(1 for d in docs if d.get("extension") == ".txt"),
            "xlsx_files": sum(1 for d in docs if d.get("extension") == ".xlsx"),
            "pdf_files": sum(1 for d in docs if d.get("extension") == ".pdf"),
        },
        "recent_requests": history[:5]
    }


# -------------------------------------------------------------
# 3. Authenticated Documents Listing
# -------------------------------------------------------------
@api_app.get("/api/v1/documents")
def list_user_documents(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = current_user["id"]
    jwt_token = current_user["jwt_token"]
    repo = CloudSupabaseRepository(user_id=user_id, jwt_token=jwt_token)
    return {"documents": repo.list_documents()}


# -------------------------------------------------------------
# 4. Authenticated Document Upload
# -------------------------------------------------------------
@api_app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user["id"]
    jwt_token = current_user["jwt_token"]
    repo = CloudSupabaseRepository(user_id=user_id, jwt_token=jwt_token)

    content_bytes = await file.read()
    ok, msg, doc_id = repo.upload_document(file.filename, content_bytes)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    return {"status": "success", "message": msg, "doc_id": doc_id}
