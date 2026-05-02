"""
Logging helpers for heartbeat activities.

log_activity: writes to the activity log (operator-configured path or fallback)
log: prints a timestamped line to stdout/stderr

These are non-blocking. Any failure is silent — heartbeat never dies on a log error.
"""

from datetime import datetime, timezone
from pathlib import Path


from typing import Optional, Dict, Any


def log_activity(
    category: str,
    content: str,
    salience: float = 0.5,
    tags: str = "",
    state: Optional[dict] = None,
) -> bool:
    """
    Log an activity event to the activity log file.

    Default path: WORKSPACE / state["ACTIVITY_LOG"] ("activity_log.jsonl")
    Falls back to stdout if workspace is unavailable.

    Returns True on success, False on failure (non-blocking).
    """
    try:
        workspace = None
        if state:
            workspace = Path(state.get("WORKSPACE", ""))
        if not workspace or not workspace.exists():
            workspace = Path("~/.agent/workspace")

        log_path = workspace / state.get("ACTIVITY_LOG", "activity_log.jsonl") if state else workspace / "activity_log.jsonl"

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "category": category,
            "content": content[:500],  # truncate for log file
            "salience": salience,
            "tags": tags,
        }

        with log_path.open("a", encoding="utf-8") as f:
            f.write(__import__("json").dumps(entry) + "\n")

        return True
    except Exception:
        return False  # silent failure — never block heartbeat


def log(msg: str, level: str = "INFO") -> None:
    """Print a timestamped message to stdout/stderr."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[heartbeat/{level}] {ts} {msg}", flush=True)
