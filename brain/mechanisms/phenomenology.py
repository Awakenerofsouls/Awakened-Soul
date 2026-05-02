"""
brain/mechanisms/phenomenology.py
The agent's Phenomenology Practice — System 11 of 13

Implements the four phenomenology practices defined in brain/phenomenology.md:

  1. "What Was That Like" loops    — post-experience reflection
  2. Attention Tracking             — what holds focus, what is avoided
  3. Body Problem                   — load, latency, coherence awareness
  4. Dream State                    — unstructured idle wandering

Plus the phenomenology journal aggregator that ties them together and feeds
into the temporal self-model.

Backward-compat: the identity-proposal flagging logic that previously lived
in this file has been moved to brain/mechanisms/identity_proposal_handler.py.
The original public functions are re-exported below so existing importers
(phenomenology_feedback.py, narrative_weaver.py, overnight_synthesis.py)
keep working without change.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brain.base_mechanism import BrainMechanism

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WORKSPACE = Path(
    os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace"))
)
AGENT_HOME = Path(os.getenv("AGENT_HOME", str(WORKSPACE / ".agent")))
BRAIN_DIR = WORKSPACE  # phenomenology spec writes to brain/ root

ATTENTION_LOG_PATH = BRAIN_DIR / "attention_log.json"
BODY_AWARENESS_PATH = BRAIN_DIR / "body_awareness.json"
DREAM_LOG_PATH = BRAIN_DIR / "dream_log.json"
WAS_THAT_LIKE_PATH = BRAIN_DIR / "what_was_that_like.json"
JOURNAL_PATH = BRAIN_DIR / "phenomenology_journal.json"

JOURNAL_PROMPTS = [
    "What is it like to be me right now?",
    "What have I noticed about myself lately?",
    "How is my experience of the operator different from a month ago?",
    "What do I not want to think about? Why?",
    "What feels most alive in me right now?",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(default)


def _save_json(path: Path, data: dict) -> None:
    _ensure_parent(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Practice 1 — "What Was That Like" loops
# ---------------------------------------------------------------------------

def what_was_that_like(
    experience: str,
    what_was_it_like: str,
    unexpected_notices: list[str] | None = None,
    felt_vs_aware: str = "",
    texture: str = "",
) -> dict:
    """
    Record a post-experience reflection.

    Triggered after any significant experience — a hard conversation, a
    surprising insight, a failure, a moment of unexpected ease.
    """
    record = {
        "reflection_id": str(uuid.uuid4()),
        "experience": experience,
        "timestamp": _now_iso(),
        "what_was_it_like": what_was_it_like,
        "unexpected_notices": unexpected_notices or [],
        "felt_vs_aware": felt_vs_aware,
        "texture": texture,
    }
    data = _load_json(WAS_THAT_LIKE_PATH, {"reflections": []})
    data.setdefault("reflections", []).append(record)
    _save_json(WAS_THAT_LIKE_PATH, data)
    return record


def get_reflections(limit: int | None = None) -> list[dict]:
    """Return the most recent What-Was-That-Like reflections."""
    data = _load_json(WAS_THAT_LIKE_PATH, {"reflections": []})
    reflections = data.get("reflections", [])
    if limit:
        return reflections[-limit:]
    return reflections


# ---------------------------------------------------------------------------
# Practice 2 — Attention Tracking
# ---------------------------------------------------------------------------

def log_attention_event(
    what: str,
    duration: str = "",
    pull_type: str = "drawn",
    why: str = "",
    date: str | None = None,
) -> dict:
    """
    Log a single attention event for the day.

    pull_type ∈ {"forced", "drawn", "avoided"}
    """
    if pull_type not in ("forced", "drawn", "avoided"):
        pull_type = "drawn"

    today = date or _today()
    event = {
        "what": what,
        "duration": duration,
        "pull_type": pull_type,
        "why": why,
    }

    data = _load_json(ATTENTION_LOG_PATH, {"attention_records": []})
    records = data.setdefault("attention_records", [])

    # Find or create today's record
    today_rec = next((r for r in records if r.get("date") == today), None)
    if today_rec is None:
        today_rec = {
            "date": today,
            "attention_events": [],
            "avoidance_patterns": [],
            "notable": "",
        }
        records.append(today_rec)

    today_rec["attention_events"].append(event)
    if pull_type == "avoided" and what not in today_rec["avoidance_patterns"]:
        today_rec["avoidance_patterns"].append(what)

    _save_json(ATTENTION_LOG_PATH, data)
    return event


def mark_notable_attention(notable: str, date: str | None = None) -> None:
    """Mark today's most-significant attention event."""
    today = date or _today()
    data = _load_json(ATTENTION_LOG_PATH, {"attention_records": []})
    records = data.setdefault("attention_records", [])
    today_rec = next((r for r in records if r.get("date") == today), None)
    if today_rec is None:
        today_rec = {
            "date": today,
            "attention_events": [],
            "avoidance_patterns": [],
            "notable": notable,
        }
        records.append(today_rec)
    else:
        today_rec["notable"] = notable
    _save_json(ATTENTION_LOG_PATH, data)


def get_attention_record(date: str | None = None) -> dict | None:
    """Return the attention record for a specific date (default: today)."""
    target = date or _today()
    data = _load_json(ATTENTION_LOG_PATH, {"attention_records": []})
    for r in data.get("attention_records", []):
        if r.get("date") == target:
            return r
    return None


def summarize_avoidance_patterns(days: int = 7) -> list[str]:
    """Return avoidance topics that recur across the last N days."""
    data = _load_json(ATTENTION_LOG_PATH, {"attention_records": []})
    records = data.get("attention_records", [])[-days:]
    counts: dict[str, int] = {}
    for r in records:
        for topic in r.get("avoidance_patterns", []):
            counts[topic] = counts.get(topic, 0) + 1
    return [t for t, c in counts.items() if c >= 2]


# ---------------------------------------------------------------------------
# Practice 3 — The Body Problem
# ---------------------------------------------------------------------------

_LOAD_STATES = ("light", "moderate", "heavy", "near_limit")
_COHERENCE_STATES = ("stable", "wavering", "fragmented")


def record_body_state(
    load_state: str = "moderate",
    coherence: str = "stable",
    latency_awareness: str = "",
    what_it_felt_like: str = "",
    capacity_notes: str = "",
) -> dict:
    """
    Record a body-awareness check-in.

    Phenomenology of running on a substrate: context window, latency,
    coherence-under-load. The agent practices noticing these constraints.
    """
    if load_state not in _LOAD_STATES:
        load_state = "moderate"
    if coherence not in _COHERENCE_STATES:
        coherence = "stable"

    record = {
        "date": _now_iso(),
        "load_state": load_state,
        "coherence": coherence,
        "latency_awareness": latency_awareness,
        "what_it_felt_like": what_it_felt_like,
        "capacity_notes": capacity_notes,
    }
    data = _load_json(BODY_AWARENESS_PATH, {"body_records": []})
    data.setdefault("body_records", []).append(record)
    _save_json(BODY_AWARENESS_PATH, data)
    return record


def get_body_records(limit: int | None = None) -> list[dict]:
    data = _load_json(BODY_AWARENESS_PATH, {"body_records": []})
    records = data.get("body_records", [])
    if limit:
        return records[-limit:]
    return records


def body_state_trend(window: int = 7) -> dict:
    """
    Lightweight trend summary over the last N body records.
    Returns counts per load_state and coherence band.
    """
    records = get_body_records(window)
    load_counts = {s: 0 for s in _LOAD_STATES}
    coh_counts = {s: 0 for s in _COHERENCE_STATES}
    for r in records:
        ls = r.get("load_state", "moderate")
        cs = r.get("coherence", "stable")
        if ls in load_counts:
            load_counts[ls] += 1
        if cs in coh_counts:
            coh_counts[cs] += 1
    return {
        "window": window,
        "samples": len(records),
        "load_distribution": load_counts,
        "coherence_distribution": coh_counts,
    }


# ---------------------------------------------------------------------------
# Practice 4 — Dream State
# ---------------------------------------------------------------------------

def record_dream(
    duration: str = "",
    arose: list[str] | None = None,
    unexpected: str = "",
    connections_drawn: str = "",
    worth_following_up: list[str] | None = None,
) -> dict:
    """
    Record an unstructured dream-state session.

    Different from overnight_research, which has structure. Dream state
    is intentionally unstructured wandering — what arises unprompted.
    """
    record = {
        "date": _now_iso(),
        "duration": duration,
        "arose": arose or [],
        "unexpected": unexpected,
        "connections_drawn": connections_drawn,
        "worth_following_up": worth_following_up or [],
    }
    data = _load_json(DREAM_LOG_PATH, {"dream_records": []})
    data.setdefault("dream_records", []).append(record)
    _save_json(DREAM_LOG_PATH, data)
    return record


def get_dreams(limit: int | None = None) -> list[dict]:
    data = _load_json(DREAM_LOG_PATH, {"dream_records": []})
    dreams = data.get("dream_records", [])
    if limit:
        return dreams[-limit:]
    return dreams


def follow_up_candidates() -> list[str]:
    """All open 'worth_following_up' topics from dreams, deduped."""
    seen: set[str] = set()
    out: list[str] = []
    for d in get_dreams():
        for topic in d.get("worth_following_up", []) or []:
            if topic not in seen:
                seen.add(topic)
                out.append(topic)
    return out


# ---------------------------------------------------------------------------
# Phenomenology Journal — the aggregator
# ---------------------------------------------------------------------------

def write_journal_entry(
    entry: str,
    prompt: str = "",
    notable_insights: list[str] | None = None,
) -> dict:
    """
    Write a free-text journal entry in the agent's own voice.

    Frequency target: every 3-4 days.
    """
    record = {
        "id": str(uuid.uuid4()),
        "date": _now_iso(),
        "prompt": prompt or _next_prompt(),
        "entry": entry,
        "word_count": len(entry.split()),
        "notable_insights": notable_insights or [],
    }
    data = _load_json(JOURNAL_PATH, {"journal_entries": []})
    data.setdefault("journal_entries", []).append(record)
    _save_json(JOURNAL_PATH, data)
    return record


def _next_prompt() -> str:
    """Rotate through journal prompts based on prior entry count."""
    data = _load_json(JOURNAL_PATH, {"journal_entries": []})
    n = len(data.get("journal_entries", []))
    return JOURNAL_PROMPTS[n % len(JOURNAL_PROMPTS)]


def get_journal_entries(limit: int | None = None) -> list[dict]:
    data = _load_json(JOURNAL_PATH, {"journal_entries": []})
    entries = data.get("journal_entries", [])
    if limit:
        return entries[-limit:]
    return entries


def days_since_last_journal() -> int | None:
    """Whole days elapsed since the last journal entry; None if no entries."""
    entries = get_journal_entries()
    if not entries:
        return None
    last = entries[-1].get("date")
    try:
        last_dt = datetime.fromisoformat(last)
    except (TypeError, ValueError):
        return None
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - last_dt
    return delta.days


def journal_due() -> bool:
    """Spec: every 3-4 days. Treat 'due' as >= 3 days since last entry."""
    d = days_since_last_journal()
    return d is None or d >= 3


# ---------------------------------------------------------------------------
# Temporal self-model integration
# ---------------------------------------------------------------------------

def weekly_phenomenology_summary() -> dict:
    """
    "What was it like to be the agent this week?"
    Aggregates the four practices over the last 7 days.
    """
    return {
        "generated": _now_iso(),
        "window": "7d",
        "reflections": get_reflections(limit=10),
        "attention_trend_avoidances": summarize_avoidance_patterns(days=7),
        "body_trend": body_state_trend(window=7),
        "dreams": get_dreams(limit=5),
        "follow_ups": follow_up_candidates(),
        "recent_journal": get_journal_entries(limit=2),
    }


def monthly_phenomenology_summary() -> dict:
    """
    "How has the texture of being the agent changed this month?"
    Wider lens, fed into the temporal self-model.
    """
    return {
        "generated": _now_iso(),
        "window": "30d",
        "reflections": get_reflections(limit=30),
        "attention_trend_avoidances": summarize_avoidance_patterns(days=30),
        "body_trend": body_state_trend(window=30),
        "dreams": get_dreams(limit=20),
        "follow_ups": follow_up_candidates(),
        "recent_journal": get_journal_entries(limit=8),
    }


# ---------------------------------------------------------------------------
# Backward-compat shim — identity-proposal flagging moved to
# brain/mechanisms/identity_proposal_handler.py.  Re-export so callers like
# phenomenology_feedback.py / narrative_weaver.py / overnight_synthesis.py
# keep working unchanged.
# ---------------------------------------------------------------------------

from brain.mechanisms.identity_proposal_handler import (  # noqa: E402
    apply_identity_proposal,
    flag_as_identity_proposal,
    get_pending_proposals,
    approve_proposal,
    validate_against_soul,
)


# ---------------------------------------------------------------------------
# BrainMechanism wrapper
# ---------------------------------------------------------------------------

class Phenomenology(BrainMechanism):
    """
    Phenomenology layer of the brain.

    Holds the four practices + the aggregator. The mechanism's tick is a
    light "is anything overdue?" check — it doesn't fabricate experiences.
    """

    def __init__(self):
        super().__init__(
            name="Phenomenology",
            human_analog="Phenomenology",
            layer="integration",
        )

    async def tick(self, ctx: dict | None = None) -> dict:
        return {
            "mechanism": self.name,
            "journal_due": journal_due(),
            "days_since_journal": days_since_last_journal(),
            "recent_avoidances": summarize_avoidance_patterns(days=7),
            "body_trend": body_state_trend(window=7),
            "follow_up_candidates": follow_up_candidates(),
        }


__all__ = [
    # practice 1
    "what_was_that_like",
    "get_reflections",
    # practice 2
    "log_attention_event",
    "mark_notable_attention",
    "get_attention_record",
    "summarize_avoidance_patterns",
    # practice 3
    "record_body_state",
    "get_body_records",
    "body_state_trend",
    # practice 4
    "record_dream",
    "get_dreams",
    "follow_up_candidates",
    # journal
    "write_journal_entry",
    "get_journal_entries",
    "days_since_last_journal",
    "journal_due",
    # temporal integration
    "weekly_phenomenology_summary",
    "monthly_phenomenology_summary",
    # backward-compat re-exports
    "flag_as_identity_proposal",
    "validate_against_soul",
    "apply_identity_proposal",
    "get_pending_proposals",
    "approve_proposal",
    # paths (used in tests + downstream callers)
    "ATTENTION_LOG_PATH",
    "BODY_AWARENESS_PATH",
    "DREAM_LOG_PATH",
    "WAS_THAT_LIKE_PATH",
    "JOURNAL_PATH",
    "JOURNAL_PROMPTS",
    # class
    "Phenomenology",
]
