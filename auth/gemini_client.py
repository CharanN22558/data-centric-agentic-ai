"""
Google Gemini AI Integration Client Module.

Provides robust, production-grade Gemini integration:
1. Reads GEMINI_API_KEY and GEMINI_MODEL dynamically from environment.
2. Supports model listing & validation via https://generativelanguage.googleapis.com/v1beta/models.
3. Tests API connectivity without exposing secret keys in logs or errors.
4. Comprehensive error handling:
   - Missing API key
   - Invalid API key (HTTP 400 / 403 API_KEY_INVALID)
   - Rate limit exceeded (HTTP 429 RESOURCE_EXHAUSTED)
   - Unsupported model (HTTP 404 NOT_FOUND)
   - Network errors / timeout
5. Enforces privacy rules:
   - Rejects transmission of private user documents.
   - Allows only synthetic demonstration documents or explicitly consented prompts.
"""

import os
from typing import Dict, Any, Optional, List, Tuple
import httpx
from config import APP_MODE, IS_DEMO_MODE


# Currently recommended stable flash models for Google Gemini
STABLE_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-pro"
]

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def get_gemini_api_key() -> str:
    """Reads GEMINI_API_KEY from environment variables without logging or exposing it."""
    return os.getenv("GEMINI_API_KEY", "").strip()


def get_gemini_model() -> str:
    """Reads configured GEMINI_MODEL or defaults to gemini-2.5-flash."""
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL


def test_gemini_connection(api_key: Optional[str] = None, model: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Tests connectivity to Google Gemini API by querying the models list.
    Never prints or displays the raw API key.

    Returns:
    (is_successful, status_message, details_dict)
    """
    key = (api_key or get_gemini_api_key()).strip()
    target_model = (model or get_gemini_model()).strip()

    if not key:
        return False, "GEMINI_API_KEY is not configured.", {"error_type": "MISSING_KEY"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)

        if resp.status_code == 200:
            data = resp.json()
            available_models = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
            return True, f"Connected to Gemini API. Model '{target_model}' configured.", {
                "available_models_count": len(available_models),
                "model_configured": target_model,
                "supported": target_model in available_models if available_models else True
            }
        elif resp.status_code in (400, 403):
            # Inspect error message without exposing key
            try:
                err_data = resp.json()
                msg = err_data.get("error", {}).get("message", "Invalid API key.")
            except Exception:
                msg = "Invalid API key or unauthorized access."
            return False, f"Authentication failed: {msg}", {"status_code": resp.status_code, "error_type": "INVALID_KEY"}
        elif resp.status_code == 429:
            return False, "Rate limit exceeded (Quota/Rate limit reached on your Gemini account).", {"status_code": 429, "error_type": "RATE_LIMIT"}
        else:
            return False, f"Gemini API returned HTTP {resp.status_code}.", {"status_code": resp.status_code, "error_type": "API_ERROR"}

    except httpx.ConnectTimeout:
        return False, "Network error: Connection to Google Gemini API timed out.", {"error_type": "TIMEOUT"}
    except httpx.ConnectError:
        return False, "Network error: Failed to reach Google Gemini API (check internet connection).", {"error_type": "NETWORK_ERROR"}
    except Exception as e:
        return False, f"Unexpected error connecting to Gemini: {str(e)}", {"error_type": "UNKNOWN"}


def call_gemini_generate(
    prompt: str,
    system_instruction: str = "",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    user_approved_external_processing: bool = False,
    is_demo_document: bool = False
) -> Dict[str, Any]:
    """
    Sends a generation request to the Gemini API with strict privacy gating:
    - If user_approved_external_processing is False AND is_demo_document is False, external call is rejected.
    - Masks any potential secrets in error responses.

    Returns:
    {
        "success": bool,
        "text": str,
        "model_used": str,
        "error": Optional[str],
        "error_type": Optional[str]
    }
    """
    # Privacy Gating: Private user documents must never be transmitted unless explicit user consent is verified
    if not user_approved_external_processing and not is_demo_document:
        return {
            "success": False,
            "text": "",
            "model_used": "",
            "error": "Privacy Protection: Document transmission to Gemini requires explicit user consent in Settings / Chat.",
            "error_type": "PRIVACY_BLOCKED"
        }

    key = (api_key or get_gemini_api_key()).strip()
    target_model = (model or get_gemini_model()).strip()

    if not key:
        return {
            "success": False,
            "text": "",
            "model_used": target_model,
            "error": "GEMINI_API_KEY is not configured.",
            "error_type": "MISSING_KEY"
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}

    contents = []
    if system_instruction:
        contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {system_instruction}"}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow the instructions."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {"contents": contents}

    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, headers=headers, json=payload)

        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    answer_text = parts[0].get("text", "").strip()
                    return {
                        "success": True,
                        "text": answer_text,
                        "model_used": target_model,
                        "error": None,
                        "error_type": None
                    }
            return {
                "success": False,
                "text": "",
                "model_used": target_model,
                "error": "Gemini API returned an empty response.",
                "error_type": "EMPTY_RESPONSE"
            }
        elif resp.status_code == 404:
            return {
                "success": False,
                "text": "",
                "model_used": target_model,
                "error": f"Model '{target_model}' is not supported or not accessible with your API key. Try setting GEMINI_MODEL=gemini-2.5-flash or gemini-2.0-flash.",
                "error_type": "UNSUPPORTED_MODEL"
            }
        elif resp.status_code in (400, 403):
            return {
                "success": False,
                "text": "",
                "model_used": target_model,
                "error": "Invalid API key or permission denied by Google Gemini.",
                "error_type": "INVALID_KEY"
            }
        elif resp.status_code == 429:
            return {
                "success": False,
                "text": "",
                "model_used": target_model,
                "error": "Gemini API rate limit exceeded. Please wait a moment before querying again.",
                "error_type": "RATE_LIMIT"
            }
        else:
            return {
                "success": False,
                "text": "",
                "model_used": target_model,
                "error": f"Gemini API returned error code {resp.status_code}.",
                "error_type": "API_ERROR"
            }

    except httpx.ConnectTimeout:
        return {
            "success": False,
            "text": "",
            "model_used": target_model,
            "error": "Network timeout connecting to Gemini API.",
            "error_type": "TIMEOUT"
        }
    except httpx.ConnectError:
        return {
            "success": False,
            "text": "",
            "model_used": target_model,
            "error": "Network error: Unable to reach Gemini API. Please check your internet connection.",
            "error_type": "NETWORK_ERROR"
        }
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "model_used": target_model,
            "error": f"Unexpected error during Gemini generation: {str(e)}",
            "error_type": "UNKNOWN"
        }

