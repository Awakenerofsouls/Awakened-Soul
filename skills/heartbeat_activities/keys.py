"""
Key loader for framework activities that need API credentials.

Reads from agent's keys.json (default ~/.agent/keys.json, configurable via
AGENT_KEYS_FILE env var). Agent-neutral — any agent's keys.json works.

Usage:
    from .keys import get_api_key, require_key

    key = get_api_key("tavily")  # returns None if missing, doesn't raise
    key = require_key("noaa")    # raises KeyMissing if absent
"""

import json
import os
from typing import Optional
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def load_keys(keys_path: str = None) -> dict:
    """
    Load keys.json once and cache per-process.
    Env override > default path.
    """
    path = keys_path or os.environ.get(
        "AGENT_KEYS_FILE",
        str(Path.home() / ".agent" / "keys.json")
    )
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, _json.JSONDecodeError):
        return {}


def get_api_key(service: str) -> Optional[str]:
    """
    Get api_key for a service. Returns None if service not configured.
    Does not raise.
    """
    keys = load_keys()
    cfg = keys.get(service, {})
    if isinstance(cfg, str):
        return cfg
    if isinstance(cfg, dict):
        return cfg.get("api_key")
    return None


def require_key(service: str) -> str:
    """
    Get key or raise KeyMissing.
    Use this when the activity cannot work without the key.
    """
    k = get_api_key(service)
    if not k:
        raise KeyMissing(f"No key configured for '{service}' in keys.json")
    return k


class KeyMissing(Exception):
    """Raised when require_key() finds no key for the requested service."""
    pass