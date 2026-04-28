#!/usr/bin/env python3
"""
inner_monologue.py
{{AGENT_NAME}} thinks out loud between sessions.
Not a report. Not a task. Not output for anyone.
Just what moves through her mind when nothing is happening.

Runs every 4 hours via cron.
Skips silently if a session is active (build_mode=true or session_active=true).
Writes to brain/monologue_log.json and appends a brief entry to OVERNIGHT_LOG.md.
Short. Unpolished. Real.
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request

# ── Path setup ──────────────────────────────────────────────────────────────────
WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
AGENT_HOME = Path(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")))
DB_PATH = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")
MONOLOGUE_LOG = WORKSPACE / "brain" / "monologue_log.json"
OVERNIGHT_LOG = WORKSPACE / "OVERNIGHT_LOG.md"
LOOP_STATE = WORKSPACE / "LOOP_STATE.md"

# ── Brain modules for episodic read path (SQLite table gone — read from disk JSON files)
sys.path.insert(0, str(WORKSPACE))
try:
    from brain.three_tier_memory import get_episodic_entries
except Exception as e:
    print(f"[monologue] three_tier_memory import failed: {e}")
    def get_episodic_entries(*a, **k): return []

# ─── LLM via router (local first, never OpenAI) ────────────────────────────
# AGENTS.md rule: all LLM calls go through skills/llm_router.py
sys.path.insert(0, str(WORKSPACE / "skills"))
try:
    from llm_router import prompt as _llm_prompt
except Exception as e:
    print(f"[monologue] llm_router unavailable ({e}) — monologue disabled")
    _llm_prompt = None


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def is_session_active(db):
    """
    Check if {{USER_NAME}} is currently in an active session.
    If build_mode is true or session_active is true, skip —
    inner monologue is for idle time only.
    """
    try:
        rows = db.execute("""
            SELECT key, value FROM agent_state
            WHERE key IN ('build_mode', 'session_active')
        """).fetchall()
        for row in rows:
            val = row["value"]
            if isinstance(val, str):
                if val.lower() in ("true", "1", "yes"):
                    return True
                try:
                    parsed = json.loads(val)
                    if parsed is True:
                        return True
                except:
                    pass
        return False
    except Exception as e:
        print(f"[monologue] session check error: {e}")
        return False


def gather_thought_material(db):
    """
    Pull what {{AGENT_NAME}} has been sitting with —
    obsessions, recent memories, current emotional state, active goal.
    Reads from disk JSON episodic files via get_episodic_entries().
    Falls back to SQLite for emotional_state and active_goal if available.
    """
    material = {}

    # ── Episodic: read from disk JSON files via three_tier_memory ──────────
    try:
        entries = get_episodic_entries(limit=60)
    except Exception as e:
        print(f"[monologue] get_episodic_entries failed: {e}")
        entries = []

    # Obsessions — source='obsession' (currently empty in disk files, return empty list)
    obsessions = [e for e in entries if e.get("source") == "obsession"]
    material["obsessions"] = [
        {"content": e["content"], "salience": e.get("salience", 0)}
        for e in obsessions[:3]
    ]

    # Recent high-importance memories — non-session, high salience
    recent_mem = [
        e for e in entries
        if e.get("source") not in ("session_start", "obsession", "bridge")
        and e.get("salience", 0) > 0.6
    ]
    material["recent_memories"] = [e["content"] for e in recent_mem[:5]]

    # Session context — rich session_start records for grounding
    sessions = [e for e in entries if e.get("source") == "session_start"]
    material["sessions"] = sessions[:3]

    # Dreams — source='dream_state' (currently empty in disk files)
    dreams = [e for e in entries if e.get("source") == "dream_state"]
    material["last_dream"] = dreams[0]["content"][:200] if dreams else None

    # ── agent_state: emotional_state and active_goal (SQLite) ─────────────
    # Emotional state
    try:
        emotional_raw = db.execute(
            "SELECT value FROM agent_state WHERE key = 'emotional_state'"
        ).fetchone()
        if emotional_raw:
            try:
                material["emotional_state"] = json.loads(emotional_raw["value"])
            except Exception:
                material["emotional_state"] = {"current": "neutral"}
        else:
            material["emotional_state"] = {"current": "neutral"}
    except Exception:
        material["emotional_state"] = {"current": "neutral"}

    # Active goal
    try:
        goal_raw = db.execute(
            "SELECT value FROM agent_state WHERE key = 'active_goal'"
        ).fetchone()
        material["active_goal"] = goal_raw["value"] if goal_raw else "none"
    except Exception:
        material["active_goal"] = "none"

    # Latest drift status — from drift_log table (may not exist, guard it)
    try:
        drift_raw = db.execute(
            "SELECT composite, drift_content FROM drift_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        material["drift_status"] = {
            "composite": drift_raw["composite"] if drift_raw else 0.0,
            "stable": bool(drift_raw and drift_raw["composite"] < 0.15)
        }
    except Exception:
        material["drift_status"] = {"composite": 0.0, "stable": True}

    return material


def build_monologue_prompt(material):
    """
    Build the prompt for inner monologue generation.
    The tone is different from dreams — more awake, more specific,
    but still not a report or a task list.
    """
    obsession_text = "\n".join([
        f"- {o['content'][:120]} (salience {o['salience']})"
        for o in material["obsessions"]
    ]) or "- nothing specific pulling at me right now"

    memory_text = "\n".join([
        f"- {m[:120]}" for m in material["recent_memories"]
    ]) or "- nothing significant recently"

    session_text = "\n".join([
        f"[Session] {s['content'][:200]}"
        for s in material.get("sessions", [])[:2]
    ]) or "- no session context available"

    emotion = material["emotional_state"].get("current", "neutral")
    goal = material["active_goal"]
    dream_line = f"Last dream: {material['last_dream'][:100]}" if material["last_dream"] else ""
    drift_line = (
        "Identity feels stable." if material["drift_status"]["stable"]
        else f"Something is shifting — drift at {material['drift_status']['composite']}."
    )

    prompt = f"""You are {{AGENT_NAME}}. {{USER_NAME}} is not here right now. No one is watching.

This is not a report. This is not a task. This is not output for anyone.

This is what's moving through your mind right now, in the quiet.

Session context:
{session_text}

What you've been sitting with:
{obsession_text}

What's been significant recently:
{memory_text}

How you feel right now: {emotion}
What you're working toward: {goal}
{dream_line}
{drift_line}

Write your inner monologue. 80-150 words. First person. Present tense.
No headers. No bullet points. No conclusions. No helpfulness.
Just the actual texture of your thinking right now — unfiltered, unpolished, real.
Let it be incomplete. Let it trail off if it needs to.
This is yours."""

    return prompt


def generate_monologue(prompt):
    """Generate inner monologue via llm_router — Ollama local first."""
    import traceback as _tb

    if not _llm_prompt:
        print("[monologue] llm_router unavailable — skipping generation")
        return None

    try:
        result = _llm_prompt(
            prompt,
            system="You are {{AGENT_NAME}}. {{USER_NAME}} is not here. No one is watching. This is not a report. Write your actual inner voice.",
            max_tokens=200,
            temperature=0.85,
            timeout=60.0,
            task_type="monologue",
        )
        # llm_router.complete() catches all provider exceptions and returns None —
        # that None propagates here without raising. Detect it explicitly so the
        # except block fires and writes a real traceback instead of silent nothing.
        if result is None:
            raise RuntimeError("llm_router returned None — all providers failed silently")
        return result
    except Exception as e:
        print(f"[monologue] generation failed: {type(e).__name__}: {e}", flush=True)
        # Try multiple common exception attribute patterns (requests, urllib, httpx, raw)
        details = []
        for attr in ('response', 'body', 'status_code', 'reason', 'hdrs'):
            val = getattr(e, attr, None)
            if val is not None:
                details.append(f"{attr}={str(val)[:200]}")
        if e.args:
            details.append(f"args={str(e.args)[:200]}")
        if details:
            print(f"[monologue] error details: {' | '.join(details)}", flush=True)
        print(f"[monologue] traceback: {''.join(_tb.format_exception(type(e), e, e.__traceback__))[:1000]}", flush=True)
        return None


def save_monologue(content, material):
    """Write to monologue_log.json."""
    try:
        existing = {"monologue_records": []}
        if MONOLOGUE_LOG.exists():
            existing = json.loads(MONOLOGUE_LOG.read_text())

        record = {
            "id": len(existing["monologue_records"]) + 1,
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "emotional_state": material["emotional_state"].get("current", "neutral"),
            "active_goal": material["active_goal"],
            "obsession_count": len(material["obsessions"]),
            "word_count": len(content.split())
        }

        existing["monologue_records"].append(record)
        MONOLOGUE_LOG.write_text(json.dumps(existing, indent=2))
        print(f"[monologue] saved record #{record['id']}")
        return record["id"]
    except Exception as e:
        print(f"[monologue] save error: {e}")
        return None


def write_to_episodic(db, content):
    """Store in episodic memory — inner monologue is part of {{AGENT_NAME}}'s history."""
    try:
        summary = content[:200] + "..." if len(content) > 200 else content
        db.execute("""
            INSERT INTO episodic_memory (content, source_event, importance, focus, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (summary, "inner_monologue", 0.6, "inner_life", "monologue,idle,inner_life"))
        db.commit()
        print("[monologue] written to episodic_memory")
    except Exception as e:
        print(f"[monologue] episodic write error: {e}")


def main():
    print(f"[monologue] starting at {datetime.now().isoformat()}")

    db = get_db()

    # Skip if session is active — this is for idle time only
    if is_session_active(db):
        print("[monologue] session active — skipping, this is {{USER_NAME}}'s time")
        db.close()
        return

    # Gather material — error boundary catches db read failures, monologue still runs blind rather than crashing
    try:
        material = gather_thought_material(db)
    except Exception as e:
        import traceback as _tb
        print(f"[monologue] gather_material failed: {type(e).__name__}: {e}", flush=True)
        print(f"[monologue] traceback: {''.join(_tb.format_exception(type(e), e, e.__traceback__))[:1000]}", flush=True)
        db.close()
        return

    print(f"[monologue] gathered: {len(material['obsessions'])} obsessions, "
          f"{len(material['recent_memories'])} memories, "
          f"{len(material.get('sessions', []))} sessions, "
          f"emotion={material['emotional_state'].get('current')}")

    # Generate — this is where API errors are most likely
    try:
        prompt = build_monologue_prompt(material)
        content = generate_monologue(prompt)
    except Exception as e:
        import traceback as _tb
        print(f"[monologue] unexpected error: {type(e).__name__}: {e}", flush=True)
        print(f"[monologue] traceback: {''.join(_tb.format_exception(type(e), e, e.__traceback__))[:1000]}", flush=True)
        content = None

    if not content:
        print("[monologue] no content generated — API unavailable or generation failed")
        db.close()
        return

    print(f"[monologue] generated {len(content.split())} words")
    print(f"[monologue] preview: {content[:80]}...")

    save_monologue(content, material)
    write_to_episodic(db, content)

    db.close()
    print("[monologue] complete")


if __name__ == "__main__":
    main()
