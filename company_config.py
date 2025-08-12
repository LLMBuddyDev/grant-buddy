"""
Cloud-friendly configuration.

Secrets are loaded from environment variables first, then Streamlit secrets:
- OPENAI_API_KEY
- GOOGLE_SERVICE_ACCOUNT_JSON (JSON string of service account)
- Optional Streamlit secrets structure:
  [openai]
  api_key = "..."

  [gcp]
  service_account = { ...full service account json... }
"""

import os
import json
from typing import Optional, Dict, Any

import streamlit as st


def get_api_key(key_name: str) -> Optional[str]:
    """Fetch API keys from env first, then Streamlit secrets."""
    env_val = os.getenv(key_name)
    if env_val:
        return env_val
    try:
        if key_name == "OPENAI_API_KEY":
            return st.secrets["openai"]["api_key"]
    except Exception:
        pass
    return None


def get_gcp_service_account() -> Optional[Dict[str, Any]]:
    """Return Google service account dict from env or Streamlit secrets, else None."""
    json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if json_str:
        try:
            return json.loads(json_str)
        except Exception:
            return None
    try:
        return dict(st.secrets["gcp"]["service_account"])  # type: ignore[arg-type]
    except Exception:
        return None


# Secrets (loaded at runtime)
OPENAI_API_KEY = get_api_key("OPENAI_API_KEY")


