"""
Logging helpers for heartbeat activities.

log_activity: writes to ACTIVITY_LOG.md in markdown format via
              skills.journal.log_activity (the canonical writer).
log: prints a timestamped line to stdout/stderr

Non-blocking. Any failure is silent — heartbeat never dies on a log error.

Why this delegates to skills.journal:
  Two log_activity implementations existed in the repo and they wrote to
  DIFFERENT files in DIFFERENT formats. This one wrote JSONL to a path
  built from `Path("~/.agent/workspace")` WITHOUT expanduser() — so the
  resolved path was the literal string "~/.agent/workspace" (not the home
  directory), the open silently failed, and the bare `except Exception`
  swallowed it. Meanwhile skills.journal wrote markdown to ACTIVITY_LOG.md,
  which is the file recent_activity_summary and search_activity actually
  read. From May 2 onward the daemon's autonomous loop produced content
  but nothing was persisted in the file the agent could later see.

  Delegating here keeps a single canonical write path so the visibility
  chain stays intact: activity → ACTIVITY_LOG.md → recent_activity_summary
  → RECENT_ACTIVITY.md + HEARTBEAT.md → dashboard chat-poll.
"""

from datetime import datetime, timezone
from pathlib import Path
import os

from typing import Optional


def log_activity(
    category: str,
    content: str,
    salience: float = 0.5,
    tags: str = "",
    state: Optional[dict] = None,
) -> bool:
    """
    Log an activity event to ACTIVITY_LOG.md in the canonical markdown
    format (parsed by recent_activity_summary, search_activity, etc.).

    Returns True on success, False on failure (non-blocking).
    """
    # Defer the journal import to call-time so a missing skills.journal
    # module never breaks heartbeat module import.
    try:
        from skills.journal import log_activity as journal_log_activity
    except Exception:
        return _fallback_jsonl(category, content, salience, tags, state)

    try:
        return bool(journal_log_activity(
            category=category,
            content=content,
            salience=salience,
            tags=tags,
        ))
    except Exception:
        return _fallback_jsonl(category, content, salience, tags, state)


def _fallback_jsonl(category, content, salience, tags, state) -> bool:
    """
    Last-resort JSONL writer used only if skills.journal is unreachable.
    Workspace path defaults follow the same env-var convention as
    skills.journal (AGENT_WORKSPACE, then ~/.agent/workspace expanded).
    """
    try:
        ws = None
        if state:
            ws_str = state.get("WORKSPACE", "") or ""
            if ws_str:
                ws = Path(ws_str).expanduser()
        if not ws or not ws.exists():
            ws = Path(os.getenv(
                "AGENT_WORKSPACE",
                str(Path.home() / ".agent" / "workspace"),
            )).expanduser()

        ws.mkdir(parents=True, exist_ok=True)
        log_path = ws / "activity_log.jsonl"

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "category": category,
            "content": (content or "")[:500],
            "salience": salience,
            "tags": tags,
        }

        with log_path.open("a", encoding="utf-8") as f:
            f.write(__import__("json").dumps(entry) + "\n")
        return True
    except Exception:
        return False


def log(msg: str, level: str = "INFO") -> None:
    """Print a timestamped message to stdout/stderr."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[heartbeat/{level}] {ts} {msg}", flush=True)
