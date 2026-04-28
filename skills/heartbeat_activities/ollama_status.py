"""
Heartbeat activity: ollama_status

Check local Ollama instance: available models, running state.
No API key needed — localhost by default. Endpoint configurable via state.

Activity contract:
  Input:  state dict (OLLAMA_ENDPOINT, etc.)
  Output: {"ok": bool, "status": "complete",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import json
import urllib.request
import urllib.error
import random
from pathlib import Path
from datetime import datetime, timezone

from .journal import write_to_journal
from .log import log_activity
SIGNAL_AFFINITY = {}


CATEGORY = "ollama_status"


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    endpoint = state.get("OLLAMA_ENDPOINT", "http://localhost:11434")

    print(f"[heartbeat] ollama_status: {endpoint}")

    try:
        models = _list_models(endpoint)
        tags = _list_tags(endpoint)
    except urllib.error.URLError as e:
        log_activity("ollama_status", f"Ollama unreachable: {e}", salience=0.5, tags="error,infrastructure")
        return _skip(f"ollama unreachable at {endpoint}")
    except Exception as e:
        log_activity("ollama_status", f"Ollama check failed: {e}", salience=0.3, tags="error")
        return _skip(f"ollama error: {e}")

    content = _format_status(endpoint, models, tags)

    write_to_journal(category="ollama_status", content=content,
                    workspace=workspace, state=state)

    return {
        "ok": True,
        "status": "complete",
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.08,
        "detail": f"{len(tags)} models available at {endpoint}",
    }


def _list_tags(endpoint: str) -> list:
    """GET /api/tags — list available models."""
    url = f"{endpoint}/api/tags"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("models", [])


def _list_models(endpoint: str) -> list:
    """GET /v1/models — alternative endpoint some deployments use."""
    url = f"{endpoint}/v1/models"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except Exception:
        return []


def _format_status(endpoint: str, models: list, tags: list) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"Ollama status — {endpoint} — {now}", ""]

    if tags:
        lines.append(f"Models available ({len(tags)}):")
        for m in tags:
            name = m.get("name", "?")
            size = m.get("size", 0)
            size_str = _format_size(size)
            modified = m.get("modified_at", "unknown")
            lines.append(f"  • {name} — {size_str} — modified {modified[:10]}")
    else:
        lines.append("No models loaded.")

    if models:
        lines.append(f"\nExtended model data: {len(models)} entries")

    lines.append(f"\nEndpoint: {endpoint}")
    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}