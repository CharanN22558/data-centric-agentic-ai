# CLOUD SETUP & SUPABASE CONFIGURATION GUIDE

**Project:** DATA CENTRIC AGENTIC AI  
**Deployment Platform:** Render (Web Service)  
**Database & Storage:** Supabase (PostgreSQL + pgvector + Auth + Private Storage)  
**Live Application URL:** `https://data-centric-agentic-ai-fcsl.onrender.com`  

---

## 1. Quick Overview

This guide explains how to set up your free Supabase cloud backend and connect it to your Render web service in 5 minutes.

---

## 2. Step 1: Create a Free Supabase Project

1. Navigate to **[https://supabase.com/dashboard](https://supabase.com/dashboard)** (or sign in with GitHub).
2. Click **New Project**.
3. Fill in:
   - **Name:** `data-centric-agentic-ai`
   - **Database Password:** *(Choose a strong password or generate one)*
   - **Region:** Choose the region nearest to you (e.g., *Central India* or *Singapore*).
   - **Pricing Plan:** **Free**.
4. Click **Create new project** and wait 1–2 minutes for the database to provision.

---

## 3. Step 2: Run the Database & Storage Migration

1. In your Supabase project dashboard, click on the **SQL Editor** tab (icon with `>_` on the left sidebar).
2. Click **New Query**.
3. Copy the entire contents of [`supabase/migrations/0001_initial_schema.sql`](file:///c:/Users/DSP%20LAB/Desktop/PROJECT-1/supabase/migrations/0001_initial_schema.sql) from this project.
4. Paste the SQL into the editor and click **Run** (green button).
5. Verify output shows: `Success. No rows returned`.

> **What this does:**
> - Enables `vector` (pgvector 384 dimensions for RAG), `uuid-ossp`, and `pgcrypto`.
> - Creates `user_profiles`, `documents`, `document_versions`, `modification_requests`, and `document_chunks`.
> - Enables **Row Level Security (RLS)** on all tables so users cannot read or modify another user's files.
> - Creates the private storage bucket `user-documents` with strict folder-level RLS policies.
> - Deploys the `match_document_chunks()` secure vector search function.

---

## 4. Step 3: Copy Your Supabase API Credentials

1. In Supabase, click **Project Settings** (gear icon at bottom left).
2. Click on **API** in the settings menu.
3. Find and copy:
   - **Project URL:** e.g., `https://xyzcompany.supabase.co`
   - **anon / public key:** Long key string starting with `eyJhbGciOiJIUzI1Ni...`

*(Note: Never use or share the `service_role` secret key! The application only needs the publishable `anon` key).*

---

## 5. Step 4: Configure Render Environment Variables

1. Go to your **[Render Dashboard](https://dashboard.render.com)**.
2. Click on your existing web service: **`data-centric-agentic-ai`**.
3. Click on the **Environment** tab on the left.
4. Add the following environment variables:

| Variable Name | Value |
| :--- | :--- |
| `APP_MODE` | `cloud` |
| `SUPABASE_URL` | *(Paste your Supabase Project URL from Step 3)* |
| `SUPABASE_ANON_KEY` | *(Paste your anon / public key from Step 3)* |
| `APP_ENCRYPTION_MASTER_KEY` | *(Render auto-generates or enter any 32+ character random string)* |
| `GEMINI_API_KEY` | *(Optional: paste your Google Gemini key for cloud LLM features)* |

5. Click **Save Changes**.

---

## 6. Step 5: Automatic Redeployment

Render will immediately trigger a clean rebuild and deploy with the new environment variables.

Once complete:
- Visit `https://data-centric-agentic-ai-fcsl.onrender.com`.
- The SQLite table error will be completely gone.
- Anyone can now create their personal account, verify email, upload documents, search using RAG, and modify documents with full isolation!

