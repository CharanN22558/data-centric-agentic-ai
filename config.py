"""
Central Configuration Module.

Loads environment variables, enforces privacy modes (LOCAL vs DEMO),
and initializes storage directories.
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

# Application Modes: 'local' (private) or 'demo' (public demonstration)
# Never silently enable local private mode on Render or public networks.
APP_MODE = os.getenv("APP_MODE", "local").strip().lower()
IS_DEMO_MODE = (APP_MODE == "demo")

# Execution Mode: 'CONFIRMATION' (requires user approval before executing modifications) or 'AUTOMATIC'
DEFAULT_EXECUTION_MODE = os.getenv("EXECUTION_MODE", "CONFIRMATION").upper()

# AI / Gemini Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

# Local Security & Storage Directories
USER_DATA_DIR = DATA_DIR / "users"
DATABASE_PATH = DATA_DIR / "app_metadata.db"
DEMO_DATA_DIR = SAMPLE_DATA_DIR

# Allowed extensions
ALLOWED_EXTENSIONS = {".txt", ".xlsx", ".pdf"}

# Ensure required local directories exist
if not IS_DEMO_MODE:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

