"""
Cloud Supabase Client & Connection Manager.

Manages connection to Supabase Auth, PostgreSQL database, Storage, and pgvector.
Provides user-scoped clients carrying authenticated user JWTs to strictly enforce
PostgreSQL and Storage Row Level Security (RLS).
"""

import os
from typing import Optional, Dict, Any
from supabase import create_client, Client

# Read configuration from environment: prefer SUPABASE_PUBLISHABLE_KEY, fallback to SUPABASE_ANON_KEY
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_PUBLISHABLE_KEY = (
    os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    or os.getenv("SUPABASE_ANON_KEY", "").strip()
)
SUPABASE_ANON_KEY = SUPABASE_PUBLISHABLE_KEY


def is_supabase_configured() -> bool:
    """Checks if Supabase credentials are provided in the environment."""
    url = os.getenv("SUPABASE_URL", "").strip() or SUPABASE_URL
    key = (
        os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
        or SUPABASE_PUBLISHABLE_KEY
    )
    return bool(url and key)


def get_anon_supabase_client() -> Optional[Client]:
    """
    Returns an unauthenticated public Supabase client using SUPABASE_PUBLISHABLE_KEY / SUPABASE_ANON_KEY.
    Used for initial sign-up, sign-in, and password reset requests.
    """
    url = os.getenv("SUPABASE_URL", "").strip() or SUPABASE_URL
    key = (
        os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
        or SUPABASE_PUBLISHABLE_KEY
    )
    if not (url and key):
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        print(f"[SUPABASE] Error creating anon client: {e}")
        return None


def get_user_supabase_client(jwt_access_token: str) -> Optional[Client]:
    """
    Returns an authenticated Supabase client scoped to the authenticated user's JWT.
    Passes custom Authorization header so that PostgREST, Auth, and Storage
    requests all carry the user's Bearer token and strictly enforce PostgreSQL & Storage RLS!
    """
    url = os.getenv("SUPABASE_URL", "").strip() or SUPABASE_URL
    key = (
        os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
        or SUPABASE_PUBLISHABLE_KEY
    )
    if not (url and key) or not jwt_access_token:
        return None
    try:
        # Create standard client with clean headers (avoiding duplicate apikey headers)
        client = create_client(url, key)
        bearer_token = f"Bearer {jwt_access_token}"
        
        # Authenticate PostgREST client with user JWT
        client.postgrest.auth(jwt_access_token)
        
        # Set user Bearer token for Storage client
        if hasattr(client, "storage") and hasattr(client.storage, "_headers"):
            client.storage._headers["Authorization"] = bearer_token
            if hasattr(client.storage, "session") and hasattr(client.storage.session, "headers"):
                client.storage.session.headers["Authorization"] = bearer_token

        return client
    except Exception as e:
        print(f"[SUPABASE] Error creating user-scoped client: {e}")
        return None


def verify_jwt_token(jwt_access_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a user's JWT bearer token with Supabase Auth.
    Returns user dictionary containing 'id', 'email', etc., or None if invalid/expired.
    """
    if not is_supabase_configured() or not jwt_access_token:
        return None
    try:
        client = get_anon_supabase_client()
        if not client:
            return None
        user_response = client.auth.get_user(jwt_access_token)
        if user_response and user_response.user:
            return {
                "id": str(user_response.user.id),
                "email": user_response.user.email,
                "role": user_response.user.role,
                "metadata": user_response.user.user_metadata
            }
    except Exception as e:
        print(f"[SUPABASE] JWT Verification failed: {e}")
    return None

