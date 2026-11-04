# Final Deployment & Infrastructure Report
**Project:** DATA CENTRIC AGENTIC AI  
**Cloud Hosting Provider:** Render  
**Database & Object Storage:** Supabase  
**Service Name:** `data-centric-agentic-ai`  
**Web URL:** [https://data-centric-agentic-ai-fcsl.onrender.com](https://data-centric-agentic-ai-fcsl.onrender.com)  
**Git Repository:** [https://github.com/CharanN22558/data-centric-agentic-ai](https://github.com/CharanN22558/data-centric-agentic-ai)  

---

## 1. Production Architecture Overview

The system runs on Render using a dual-process architecture managed by `start.py`:

```
               [ Internet / User Browser ]
                            │
                            ▼
              [ Cloudflare CDN & SSL Edge ]
                            │
                            ▼
              [ FastAPI Proxy (Port $PORT) ]
                ├── /health -> HTTP 200 JSON
                └── Reverse Proxy / Websocket Tunnel
                            │
                            ▼
           [ Streamlit Core Server (Port 8501) ]
           ├── UI Components (ui/*.py)
           ├── Agent Orchestrator (agents/*.py)
           └── Document Processors (processors/*.py)
                    │                    │
                    ▼                    ▼
     [ Supabase Auth & PostgreSQL ]  [ Supabase Private Storage ]
         - Row-Level Security            - Encrypted bucket 'user-documents'
         - pgvector (384 dim)            - Isolated paths: {user_id}/{doc_id}/*
```

---

## 2. Environment Variables Summary

The following environment variables are configured on Render:

| Variable | Description |
|----------|-------------|
| `APP_MODE` | Set to `cloud` to enable Supabase multi-user architecture |
| `SUPABASE_URL` | `https://ftyvumxamwdalqhwcmow.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | Public anonymous key used for client authentication |
| `SUPABASE_ANON_KEY` | Fallback alias matching the publishable key |
| `APP_ENCRYPTION_MASTER_KEY` | 256-bit cryptographically secure master key for DEK encryption |
| `PORT` | Dynamic port assigned by Render |

---

## 3. Git Branches & Deployment Status

- **Main Branch**: `main` (commit `c6b5f6a`)
- **Mirror Branch**: `master` (commit `c6b5f6a`)
- **Deployment Status**: Automatic continuous deployment enabled on Render.
- **HTTP Status**: Verified live at `https://data-centric-agentic-ai-fcsl.onrender.com` returning HTTP 200 OK.
