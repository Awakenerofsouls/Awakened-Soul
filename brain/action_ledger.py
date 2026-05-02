"""
brain/action_ledger.py — Per-turn tool-call ledger

When a tool is invoked, the wrapper calls `record(tool_name, args, result, status)`.
The agent's runtime can then query `actions_this_turn()` before responding to verify
that any action-claim it makes (e.g. "I posted to molty") corresponds to a real call.

The check itself lives in brain/epistemic_check.py.

Ledger is per-turn (in-memory) plus a persistent rolling tail on disk for diagnostics.
"""
from __future__ import annotations

import json
import os
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")))
LEDGER_DIR = WORKSPACE / "brain" / "action_ledger"

# NOTE: do NOT create the ledger directory at import time. Importing
# brain.action_ledger should be a no-op on disk. The directory is created
# lazily on the first write so smoke tests / introspection don't pollute
# whatever workspace the env points at.

_lock = threading.Lock()
_current_turn: Dict[str, List[Dict[str, Any]]] = {"actions": []}


def _today_file() -> Path:
    """Resolve the per-day ledger file. Computed lazily so the date rolls
    over correctly across midnight."""
    return LEDGER_DIR / time.strftime("%Y-%m-%d.jsonl")


def begin_turn(turn_id: Optional[str] = None) -> str:
    """Reset the in-memory turn ledger. Call at the start of each agent turn."""
    with _lock:
        _current_turn["turn_id"] = turn_id or time.strftime("%Y%m%dT%H%M%S")
        _current_turn["started_at"] = time.time()
        _current_turn["actions"] = []
    return _current_turn["turn_id"]


def record(
    tool_name: str,
    args: Optional[Dict[str, Any]] = None,
    result: Any = None,
    status: str = "ok",
) -> Dict[str, Any]:
    """
    Record a tool call. Call from inside the tool wrapper after the call completes.

    Args:
        tool_name: e.g. "molty_post", "calendar_check", "file_write"
        args:      the arguments the tool was called with
        result:    short summary or first 200 chars of the result
        status:    "ok" | "error" | "skipped"
    """
    entry = {
        "ts": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": tool_name,
        "args": _clip(args, 400),
        "result": _clip(result, 400),
        "status": status,
    }
    with _lock:
        _current_turn.setdefault("actions", []).append(entry)
        try:
            LEDGER_DIR.mkdir(parents=True, exist_ok=True)
            with open(_today_file(), "a") as fp:
                fp.write(json.dumps(entry) + "\n")
        except Exception:
            pass
    return entry


def actions_this_turn() -> List[Dict[str, Any]]:
    """Return the list of tool calls recorded since the last begin_turn()."""
    with _lock:
        return list(_current_turn.get("actions", []))


def turn_summary() -> Dict[str, Any]:
    """Compact summary of the current turn — what tools fired, statuses, count."""
    with _lock:
        actions = list(_current_turn.get("actions", []))
        tools_fired = sorted({a["tool"] for a in actions})
        return {
            "turn_id": _current_turn.get("turn_id"),
            "started_at": _current_turn.get("started_at"),
            "action_count": len(actions),
            "tools": tools_fired,
            "ok_count": sum(1 for a in actions if a["status"] == "ok"),
            "error_count": sum(1 for a in actions if a["status"] == "error"),
        }


def has_action(predicate: str) -> bool:
    """
    Return True if any action this turn matches the predicate substring
    (case-insensitive) against tool name or args. Used by the epistemic check.
    """
    needle = predicate.lower()
    for a in actions_this_turn():
        if needle in a["tool"].lower():
            return True
        if needle in json.dumps(a.get("args", "")).lower():
            return True
    return False


def find_actions(predicate: str) -> List[Dict[str, Any]]:
    """Return ledger entries whose tool name or args contain the predicate."""
    needle = predicate.lower()
    return [
        a for a in actions_this_turn()
        if needle in a["tool"].lower()
        or needle in json.dumps(a.get("args", "")).lower()
    ]


def _clip(value: Any, max_len: int) -> Any:
    """Clip strings/dicts to a max representation length so the ledger stays small."""
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, dict):
        try:
            s = json.dumps(value, default=str)
        except Exception:
            s = str(value)
    elif isinstance(value, (list, tuple)):
        try:
            s = json.dumps(list(value), default=str)
        except Exception:
            s = str(value)
    else:
        s = str(value)
    return s if len(s) <= max_len else s[:max_len] + "...<truncated>"


# Initialize a default turn so `actions_this_turn()` always returns a list
begin_turn("default")
