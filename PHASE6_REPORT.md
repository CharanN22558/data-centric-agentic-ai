# PHASE 6 REPORT: RENDER DEPLOYMENT & CLOUD ARCHITECTURE

**Project Name:** DATA CENTRIC AGENTIC AI  
**GitHub Repository:** [https://github.com/CharanN22558/data-centric-agentic-ai](https://github.com/CharanN22558/data-centric-agentic-ai)  
**Branch:** `main`  
**Latest Deployed Commit:** `b81c918` (`feat: add Render supervisor script and blueprint configuration for public demo deployment`)  
**Target Platform:** Render Web Service (Free Tier)  
**Execution Mode:** `APP_MODE=demo` (Strict Synthetic Demonstration Mode)  

---

## 1. Cloud Architecture & Supervisor Implementation

To deploy both the **Streamlit Frontend** and **FastAPI Backend** inside Render's single-port container environment:

1. **Process Supervisor ([`start.py`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/start.py)):**
   - Automatically boots the FastAPI backend on internal loopback `127.0.0.1:8000`.
   - Polls `/health` until HTTP 200 is verified.
   - Launches Streamlit dynamically bound to `0.0.0.0:$PORT` (Render's assigned public HTTP port).
   - Manages signal traps (`SIGINT`, `SIGTERM`) to cleanly terminate child processes during redeploys or shutdowns.
2. **Render Blueprint Specification ([`render.yaml`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/render.yaml)):**
   - `type: web`
   - `plan: free`
   - `runtime: python` (pinned to `PYTHON_VERSION: 3.11.9`)
   - `buildCommand: pip install --upgrade pip && pip install -r requirements.txt`
   - `startCommand: python start.py`
   - `APP_MODE: demo`

---

## 2. Public Demonstration Mode Privacy Safeguards

The deployment enforces strict boundaries for public cloud instances:
- **Zero Real Uploads:** Personal document uploads are completely disabled in the UI.
- **Zero Real Accounts:** User registration is disabled; users enter a sandbox session populated exclusively with synthetic sample documents:
  - `sample_employees.xlsx`
  - `sample_notes.txt`
  - `sample_report.pdf`
- **Zero Cloud Leakage:** All vector search runs locally in memory via ChromaDB and SentenceTransformers.
- **Gemini Gating:** Gemini synthesis operates only when an optional `GEMINI_API_KEY` is provided in Render environment variables; otherwise, the system seamlessly uses the local offline answer generator.

---

## 3. Render Dashboard Deployment Guide

I have opened the Render Blueprint creation page in your browser:
👉 **[https://dashboard.render.com/blueprints/new](https://dashboard.render.com/blueprints/new)**

1. **Connect Repository:**
   - Under *Connect a repository*, select your repository: **`CharanN22558/data-centric-agentic-ai`**.
   - *(If your repository does not appear, click **Configure GitHub App** on Render to grant access to the `data-centric-agentic-ai` repository).*
2. **Apply Blueprint:**
   - Render will read [`render.yaml`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/render.yaml) automatically.
   - Blueprint Name: `data-centric-agentic-ai`
   - Service: `data-centric-agentic-ai` (Web Service on Free plan)
3. **Optional Environment Variables:**
   - `GEMINI_API_KEY`: *(Optional — paste your Gemini key in Render environment settings if you want cloud LLM responses; otherwise leave empty for local offline mode).*
4. **Deploy:**
   - Click **Apply** or **Create Web Service**.
   - Render will build and deploy your application.

Once the build finishes, Render will provide your public URL:
`https://data-centric-agentic-ai.onrender.com` (or similar).
