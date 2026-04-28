#!/usr/bin/env python3
"""
heartbeat_base_activities.py — Canonical heartbeat activity template

Provides four base activities that run every heartbeat tick.
Each activity is isolated (try/except), and state is always saved in a finally
block regardless of whether the activity raised.

Activities:
  check_day_boundary  — detect UTC midnight, reset daily counters
  check_outbox        — process pending outbound items (generic stub)
  check_daily_checksum — verify identity file integrity
  run_user_interests  — load and evaluate interest vectors

State persistence: memory/heartbeat-state.json
  {
    "last_utc_day": "YYYY-MM-DD",
    "utc_day_count": int,
    "last_run": "ISO timestamp",
    "activities": {
      "check_day_boundary":  {"last": "ISO ts", "ok": bool, "detail": str},
      "check_outbox":        {"last": "ISO ts", "ok": bool, "detail": str},
      "check_daily_checksum":{"last": "ISO ts", "ok": bool, "detail": str},
      "run_user_interests":  {"last": "ISO ts", "ok": bool, "detail": str},
    }
  }

Extending check_outbox():
  Subclasses (or wrapper scripts) should read from memory/outbox.jsonl.
  Each line is a JSON object with at minimum a "type" field.
  The contract for extending check_outbox:
    1. Read memory/outbox.jsonl — each line: {"type": str, ...}
    2. Filter by supported "type" values
    3. Execute or queue each item
    4. Remove processed items from outbox (write remaining back)
    5. Log outcome

Extending run_user_interests():
  Loads interest vectors from memory/user_interests.jsonl.
  Each line: {"topic": str, "weight": float, "last_triggered": str?}
  The contract:
    1. Load all interest vectors from memory/user_interests.jsonl
    2. Evaluate which ones are due (based on last_triggered timestamp)
    3. Return list of due interest topic names
  This stub returns an empty list. Replace the body to activate.
"""

import json
import sys
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

# ── Paths ────────────────────────────────────────────────────────────────────

WORKSPACE    = Path(os.getenv("AGENT_WORKSPACE", os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace"))))
MEMORY_DIR   = WORKSPACE / "memory"
STATE_FILE   = MEMORY_DIR / "heartbeat-state.json"
OUTBOX_FILE  = MEMORY_DIR / "outbox.jsonl"
CHECKSUM_SCRIPT = WORKSPACE / "skills" / "checksum_guard.py"
AGENT_HOME    = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))

MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# ── State helpers ─────────────────────────────────────────────────────────────

def _load_state() -> Dict[str, Any]:
    """Load heartbeat state. Returns a fresh default if file is missing or corrupt."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return _fresh_state()


def _fresh_state() -> Dict[str, Any]:
    """Return a new empty heartbeat state."""
    return {
        "last_utc_day": "",
        "utc_day_count": 0,
        "last_run": "",
        "activities": {
            "check_day_boundary":   {"last": "", "ok": False, "detail": ""},
            "check_outbox":         {"last": "", "ok": False, "detail": ""},
            "check_daily_checksum": {"last": "", "ok": False, "detail": ""},
            "run_user_interests":    {"last": "", "ok": False, "detail": ""},
        },
    }


def _save_state(state: Dict[str, Any]) -> None:
    """Always save state, even if an activity raised."""
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except Exception as e:
        print(f"[heartbeat_base] FAILED to write state: {e}")


def _utc_today() -> str:
    """Current UTC date as YYYY-MM-DD string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _iso_now() -> str:
    """Current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# ── Activity: check_day_boundary ─────────────────────────────────────────────

def check_day_boundary(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect UTC midnight crossings.
    Increments utc_day_count on each new UTC day.
    Resets per-day counters in state.
    """
    today = _utc_today()
    last_day = state.get("last_utc_day", "")

    if today != last_day:
        state["utc_day_count"] = state.get("utc_day_count", 0) + 1
        state["last_utc_day"] = today
        detail = (
            f"UTC day boundary crossed: {last_day!r} -> {today!r} "
            f"(utc_day_count now {state['utc_day_count']})"
        )
        return {"ok": True, "detail": detail}
    return {"ok": True, "detail": "same UTC day, no boundary crossing"}


# ── Activity: check_outbox ────────────────────────────────────────────────────

def check_outbox(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic outbox processor stub.

    Reads memory/outbox.jsonl. Each line is a JSON object.
    This stub implementation:
      - Logs the count of pending items
      - Does NOT process or remove any items
      - Returns immediately

    To extend: replace the body with logic that:
      1. Reads OUTBOX_FILE line by line
      2. Parses each as JSON
      3. Handles known "type" values (e.g. "telegram_message", "webhook")
      4. Removes processed lines from the file (rewrite with remaining lines)
      5. Logs the outcome

    The outbox contract:
      - One JSON object per line, must include "type"
      - Supported types are defined by the implementing script
      - Lines that raise on parse should be logged and skipped
      - After processing, write back only unprocessed lines
    """
    if not OUTBOX_FILE.exists():
        return {"ok": True, "detail": "no outbox file present"}

    try:
        lines = OUTBOX_FILE.read_text().splitlines()
    except Exception as e:
        return {"ok": False, "detail": f"could not read outbox: {e}"}

    pending = sum(1 for line in lines if line.strip())
    if pending == 0:
        return {"ok": True, "detail": "outbox empty"}
    print(f"[heartbeat_base] check_outbox: {pending} pending item(s) in outbox")
    print(f"[heartbeat_base] check_outbox: STUB — no items processed")
    return {"ok": True, "detail": f"{pending} item(s) pending — stub, not processed"}


# ── Activity: check_daily_checksum ───────────────────────────────────────────

def check_daily_checksum(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run checksum_guard.py to verify identity file integrity.

    Calls checksum_guard.check() — which reads the SHA256 baseline and alerts
    via Telegram if SOUL.md or IDENTITY.md has changed unexpectedly.

    This stub calls the check function directly (not as a subprocess).
    If the baseline has not been initialised, logs a warning and returns ok=True
    (checksum failures should not hard-fail the heartbeat).
    """
    if not CHECKSUM_SCRIPT.exists():
        return {
            "ok": False,
            "detail": f"checksum_guard.py not found at {CHECKSUM_SCRIPT}",
        }

    try:
        # Import the module so we can call check() directly
        import importlib.util
        spec = importlib.util.spec_from_file_location("checksum_guard", CHECKSUM_SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # check() returns None — it writes alerts directly
        # It prints ok/mismatch lines itself.
        mod.check()
        return {"ok": True, "detail": "checksum_guard.check() completed"}

    except Exception as e:
        return {"ok": False, "detail": f"checksum_guard error: {e}"}


# ── Activity: run_user_interests ─────────────────────────────────────────────

def run_user_interests(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stub: load and evaluate interest vectors.

    Contract for extending:
      1. Read memory/user_interests.jsonl — one JSON object per line:
         {"topic": str, "weight": float, "last_triggered": "ISO str?"}
      2. Compute which interests are due (e.g. last_triggered > threshold)
      3. Return the list of due topic names

    This stub:
      - Checks if the interests file exists
      - Logs the count of loaded interests
      - Returns an empty due list (no activities triggered)

    To activate: replace the body with actual evaluation logic that
    returns a list of interest topic strings that should be acted on
    this heartbeat tick.
    """
    interests_file = MEMORY_DIR / "user_interests.jsonl"
    if not interests_file.exists():
        return {"ok": True, "detail": "no user_interests.jsonl file found"}

    try:
        lines = interests_file.read_text().splitlines()
        interests = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                interests.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        print(f"[heartbeat_base] run_user_interests: loaded {len(interests)} interest(s)")
        due = []  # STUB: no interests are considered due
        if due:
            print(f"[heartbeat_base] run_user_interests: due interests: {due}")
        return {"ok": True, "detail": f"{len(interests)} loaded, {len(due)} due"}
    except Exception as e:
        return {"ok": False, "detail": f"error loading interests: {e}"}


# ── Main run loop ─────────────────────────────────────────────────────────────

def run_all() -> None:
    """
    Run all base activities in order, with per-activity error isolation.
    State is always saved in a finally block after each activity.
    """
    state = _load_state()
    state["last_run"] = _iso_now()

    activities = [
        ("check_day_boundary",   check_day_boundary),
        ("check_outbox",         check_outbox),
        ("check_daily_checksum", check_daily_checksum),
        ("run_user_interests",   run_user_interests),
    ]

    for name, fn in activities:
        activity_state = state["activities"].setdefault(name, {"last": "", "ok": False, "detail": ""})
        activity_state["last"] = _iso_now()
        try:
            result = fn(state)
            activity_state["ok"] = result.get("ok", False)
            activity_state["detail"] = result.get("detail", "")
        except Exception as e:
            activity_state["ok"] = False
            activity_state["detail"] = f"UNHANDLED EXCEPTION: {e}"
            print(f"[heartbeat_base] {name} raised unhandled exception: {e}")
        finally:
            _save_state(state)

    print(f"[heartbeat_base] all activities complete — state saved to {STATE_FILE}")


if __name__ == "__main__":
    run_all()
