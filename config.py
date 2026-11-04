"""
Central Configuration Module.

Loads environment variables, enforces privacy modes:
- 'local' : Local private mode with Argon2id auth, local AES-256-GCM, SQLite, ephemeral ChromaDB.
- 'cloud' : Public multi-user cloud mode using Supabase (PostgreSQL, Supabase Auth, pgvector, Private Storage).
- 'demo'  : Demonstration fallback mode.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if available
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

# Application Mode: 'cloud', 'local', or 'demo'
APP_MODE = os.getenv("APP_MODE", "cloud").strip().lower()
IS_CLOUD_MODE = (APP_MODE == "cloud")
IS_LOCAL_MODE = (APP_MODE == "local")
IS_DEMO_MODE = (APP_MODE == "demo")

# Supabase Credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()

# Cloud Master Encryption Key (Used to derive per-user AES-256-GCM at rest keys)
APP_ENCRYPTION_MASTER_KEY = os.getenv("APP_ENCRYPTION_MASTER_KEY", "").strip()

# Default Execution Mode for Modifications: 'CONFIRMATION' (default) or 'AUTOMATIC'
DEFAULT_EXECUTION_MODE = os.getenv("EXECUTION_MODE", "CONFIRMATION").upper()

# AI / Gemini Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

# Local Security & Storage Directories
USER_DATA_DIR = DATA_DIR / "users"
DATABASE_PATH = DATA_DIR / "app_metadata.db"
DEMO_DATA_DIR = SAMPLE_DATA_DIR

# Allowed extensions & Upload Quotas
ALLOWED_EXTENSIONS = {".txt", ".xlsx", ".pdf"}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
USER_STORAGE_QUOTA_MB = int(os.getenv("USER_STORAGE_QUOTA_MB", "100"))

# Ensure required local directories exist when running locally
if IS_LOCAL_MODE:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
