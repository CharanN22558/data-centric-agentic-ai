"""
Cloud Supabase Client & Connection Manager.

Manages connection to Supabase Auth, PostgreSQL database, Storage, and pgvector.
Provides user-scoped clients carrying authenticated user JWTs to strictly enforce
PostgreSQL and Storage Row Level Security (RLS).
"""

import os
from typing import Optional, Dict, Any
from supabase import create_client, Client

# Read configuration from environment
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()


def is_supabase_configured() -> bool:
    """Checks if Supabase credentials are provided in the environment."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def get_anon_supabase_client() -> Optional[Client]:
    """
    Returns an unauthenticated public Supabase client using SUPABASE_ANON_KEY.
    Used for initial sign-up, sign-in, and password reset requests.
    """
    if not is_supabase_configured():
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception as e:
        print(f"[SUPABASE] Error creating anon client: {e}")
        return None


def get_user_supabase_client(jwt_access_token: str) -> Optional[Client]:
    """
    Returns an authenticated Supabase client scoped to the authenticated user's JWT.
    This ensures all subsequent DB and Storage queries strictly enforce PostgreSQL RLS!
    """
    if not is_supabase_configured() or not jwt_access_token:
        return None
    try:
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        client.postgrest.auth(jwt_access_token)
        # Apply token to storage client headers as well
        client.storage.session.headers.update({"Authorization": f"Bearer {jwt_access_token}"})
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
