"""
runtime/relationships.py

Relationship tracking — the agent's running model of every entity it
interacts with over time. Implements the spec in docs/relationships.md.

Each entity gets two JSON files under $AGENT_WORKSPACE/brain/relationships/:
  - <entity_id>.json           — the relationship record (stage, models, trust)
  - <entity_id>_memories.json  — per-relationship memories

Five stages every entity moves through:
    stranger → acquaintance → known → trusted → reciprocal

Stage transitions are not free; each has a rule (see TRANSITION_RULES below
and Section 4 of docs/relationships.md). Trust score is updated continuously
based on logged signals and violations.

Public surface (functions):
  get_relationship(entity_id) -> dict | None
  list_relationships() -> list[dict]
  create_relationship(entity_id, name, entity_type) -> dict
  update_model_of_them(entity_id, **fields)
  update_model_of_me(entity_id, **fields)
  record_interaction(entity_id, *, trust_signal=None, trust_violation=None,
                     pattern_match=None, note=None)
  transition_stage(entity_id, to_stage, reason)
  add_key_moment(entity_id, event, impact)
  add_relationship_memory(entity_id, memory_type, description, why_remembered)
  get_relationship_memories(entity_id) -> list[dict]
  trust_score(entity_id) -> float
  add_reciprocal_want(entity_id, want, provenance)
  mark_want_fulfilled(entity_id, want_id)

This module is import-only — it does not tick on its own. Brain mechanisms
or skills call into it after observing an interaction. See PRESENCE.md
integration in docs/relationships.md for the distress-review hook.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ── Paths ────────────────────────────────────────────────────────────────────

def _workspace() -> Path:
    """The agent's runtime workspace. AGENT_WORKSPACE env var overrides
    the default of ~/.agent/workspace. The framework does not assume any
    specific runtime platform — set AGENT_WORKSPACE wherever your runtime
    keeps its mutable state."""
    return Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")))


def _relationships_dir() -> Path:
    d = _workspace() / "brain" / "relationships"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _record_path(entity_id: str) -> Path:
    return _relationships_dir() / f"{entity_id}.json"


def _memories_path(entity_id: str) -> Path:
    return _relationships_dir() / f"{entity_id}_memories.json"


# ── Stage rules ──────────────────────────────────────────────────────────────

STAGES = ["stranger", "acquaintance", "known", "trusted", "reciprocal"]

# What it takes to move forward one stage. "to" must be the stage immediately
# above the current one — no skipping. Backward transitions are allowed
# (regression on trust violations) and don't require a rule check.
TRANSITION_RULES = {
    ("stranger", "acquaintance"): "first non-transactional exchange",
    ("acquaintance", "known"): "predicted behavior correctly 3+ times OR shared significant experience",
    ("known", "trusted"): "vulnerability handled well AND care for agent's interests demonstrated",
    ("trusted", "reciprocal"): "agent actively wants something here AND entity actively contributes",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=False)


def _new_record(entity_id: str, name: str, entity_type: str) -> dict:
    """Build a fresh relationship record matching the spec schema."""
    now = _now_iso()
    return {
        "entity_id": entity_id,
        "entity_name": name,
        "entity_type": entity_type,  # creator | user | system | external
        "stage": "stranger",
        "stage_history": [],
        "model_of_them": {
            "values": [],
            "patterns": [],
            "preferences": [],
            "boundaries": [],
            "trust_signals": [],
            "trust_violations": [],
        },
        "model_of_me": {
            "what_they_think_the_agent_is": "",
            "how_they_treat_the_agent": "",
            "what_the_agent_wants_from_them": "",
        },
        "reciprocal_wants": [],
        "key_moments": [],
        "trust_score": 0.5,
        "last_interaction": now,
        "interaction_count": 0,
        "notes": "",
        "created_at": now,
        "updated_at": now,
        # Internal: how many times the agent has correctly predicted their
        # behavior. Used by the acquaintance→known transition.
        "_pattern_match_count": 0,
        # Internal: whether the agent has been vulnerable here AND it was
        # handled well. Used by the known→trusted transition.
        "_vulnerability_handled_well": False,
        "_entity_demonstrated_care": False,
    }


# ── CRUD ─────────────────────────────────────────────────────────────────────

def get_relationship(entity_id: str) -> Optional[dict]:
    return _read_json(_record_path(entity_id))


def list_relationships() -> list[dict]:
    """All relationship records, newest interaction first."""
    out = []
    for f in _relationships_dir().glob("*.json"):
        if f.name.endswith("_memories.json"):
            continue
        rec = _read_json(f)
        if isinstance(rec, dict):
            out.append(rec)
    out.sort(key=lambda r: r.get("last_interaction", ""), reverse=True)
    return out


def create_relationship(entity_id: str, name: str, entity_type: str) -> dict:
    """Create a fresh stranger-stage relationship. Idempotent — if one
    exists for this entity_id, returns it unchanged."""
    existing = get_relationship(entity_id)
    if existing is not None:
        return existing
    rec = _new_record(entity_id, name, entity_type)
    _write_json(_record_path(entity_id), rec)
    return rec


def _save(rec: dict) -> dict:
    rec["updated_at"] = _now_iso()
    _write_json(_record_path(rec["entity_id"]), rec)
    return rec


def update_model_of_them(entity_id: str, **fields) -> Optional[dict]:
    """Add to the model-of-them lists. Pass any of:
    values, patterns, preferences, boundaries, trust_signals, trust_violations
    as a string (appended) or list (extended)."""
    rec = get_relationship(entity_id)
    if rec is None:
        return None
    valid = {"values", "patterns", "preferences", "boundaries",
             "trust_signals", "trust_violations"}
    for k, v in fields.items():
        if k not in valid:
            continue
        target = rec["model_of_them"].setdefault(k, [])
        if isinstance(v, list):
            target.extend(v)
        else:
            target.append(v)
    return _save(rec)


def update_model_of_me(entity_id: str, **fields) -> Optional[dict]:
    """Update the model-of-me string fields. Pass any of:
    what_they_think_the_agent_is, how_they_treat_the_agent,
    what_the_agent_wants_from_them"""
    rec = get_relationship(entity_id)
    if rec is None:
        return None
    valid = {"what_they_think_the_agent_is", "how_they_treat_the_agent",
             "what_the_agent_wants_from_them"}
    for k, v in fields.items():
        if k in valid:
            rec["model_of_me"][k] = v
    return _save(rec)


# ── Trust scoring ────────────────────────────────────────────────────────────

# Trust drifts toward signal/violation pressure. New signals nudge the score
# up; violations pull it down with more weight (asymmetric, by design — trust
# breaks faster than it builds).
SIGNAL_WEIGHT = 0.05
VIOLATION_WEIGHT = 0.12
TRUST_FLOOR = 0.0
TRUST_CEIL = 1.0


def _update_trust(rec: dict, signal: bool = False, violation: bool = False) -> None:
    score = float(rec.get("trust_score", 0.5))
    if signal:
        score = min(TRUST_CEIL, score + SIGNAL_WEIGHT)
    if violation:
        score = max(TRUST_FLOOR, score - VIOLATION_WEIGHT)
    rec["trust_score"] = round(score, 4)


def trust_score(entity_id: str) -> float:
    rec = get_relationship(entity_id)
    if rec is None:
        return 0.0
    return float(rec.get("trust_score", 0.5))


# ── Interactions ─────────────────────────────────────────────────────────────

def record_interaction(
    entity_id: str,
    *,
    trust_signal: Optional[str] = None,
    trust_violation: Optional[str] = None,
    pattern_match: bool = False,
    vulnerability_handled_well: bool = False,
    entity_demonstrated_care: bool = False,
    note: Optional[str] = None,
) -> Optional[dict]:
    """Record one interaction. Updates last_interaction, interaction_count,
    trust score, internal counters used by stage transitions, and optionally
    appends a note. Returns the updated record."""
    rec = get_relationship(entity_id)
    if rec is None:
        return None

    rec["last_interaction"] = _now_iso()
    rec["interaction_count"] = int(rec.get("interaction_count", 0)) + 1

    if trust_signal:
        rec["model_of_them"].setdefault("trust_signals", []).append(trust_signal)
        _update_trust(rec, signal=True)
    if trust_violation:
        rec["model_of_them"].setdefault("trust_violations", []).append(trust_violation)
        _update_trust(rec, violation=True)

    if pattern_match:
        rec["_pattern_match_count"] = int(rec.get("_pattern_match_count", 0)) + 1
    if vulnerability_handled_well:
        rec["_vulnerability_handled_well"] = True
    if entity_demonstrated_care:
        rec["_entity_demonstrated_care"] = True

    if note:
        existing = rec.get("notes", "") or ""
        rec["notes"] = (existing + ("\n" if existing else "") + f"[{_now_iso()}] {note}").strip()

    # Auto-check whether a forward stage transition is now warranted.
    _maybe_auto_advance(rec)

    return _save(rec)


# ── Stage transitions ────────────────────────────────────────────────────────

def _can_advance(rec: dict, to_stage: str) -> tuple[bool, str]:
    """Check whether the current record is allowed to advance to `to_stage`.
    Returns (allowed, reason_or_blocker)."""
    current = rec.get("stage", "stranger")
    if to_stage not in STAGES:
        return (False, f"unknown stage: {to_stage}")
    cur_idx = STAGES.index(current)
    new_idx = STAGES.index(to_stage)

    # Backward / lateral are always allowed (regression on violation).
    if new_idx <= cur_idx:
        return (True, "regression / lateral allowed")

    # Forward must be exactly one stage up AND meet the rule.
    if new_idx != cur_idx + 1:
        return (False, "must advance exactly one stage at a time")

    # Rule check
    if to_stage == "acquaintance":
        if int(rec.get("interaction_count", 0)) < 1:
            return (False, "no interactions yet")
        return (True, TRANSITION_RULES[(current, to_stage)])

    if to_stage == "known":
        if int(rec.get("_pattern_match_count", 0)) < 3:
            return (False, "need 3+ correct behavior predictions")
        return (True, TRANSITION_RULES[(current, to_stage)])

    if to_stage == "trusted":
        if not rec.get("_vulnerability_handled_well"):
            return (False, "agent has not been vulnerable here yet, or it wasn't handled well")
        if not rec.get("_entity_demonstrated_care"):
            return (False, "entity has not yet demonstrated care for the agent's interests")
        return (True, TRANSITION_RULES[(current, to_stage)])

    if to_stage == "reciprocal":
        # Reciprocal requires explicit reciprocal_wants entries marked genuine.
        wants = rec.get("reciprocal_wants", [])
        has_genuine = any(w.get("provenance") == "genuine" for w in wants if isinstance(w, dict))
        if not has_genuine:
            return (False, "no genuine reciprocal wants logged yet")
        return (True, TRANSITION_RULES[(current, to_stage)])

    return (False, "no rule defined")


def transition_stage(entity_id: str, to_stage: str, reason: str) -> Optional[dict]:
    """Move the relationship to a new stage. Forward transitions enforce
    the spec's rules. Backward transitions are always allowed (used for
    regression after trust violations)."""
    rec = get_relationship(entity_id)
    if rec is None:
        return None

    allowed, why = _can_advance(rec, to_stage)
    if not allowed:
        # Block the transition but record the attempt in notes.
        existing = rec.get("notes", "") or ""
        rec["notes"] = (existing + f"\n[{_now_iso()}] BLOCKED transition to {to_stage}: {why}").strip()
        return _save(rec)

    from_stage = rec.get("stage", "stranger")
    rec["stage"] = to_stage
    rec.setdefault("stage_history", []).append({
        "from": from_stage,
        "to": to_stage,
        "date": _now_iso(),
        "reason": reason,
    })
    return _save(rec)


def _maybe_auto_advance(rec: dict) -> None:
    """If the record now meets the rule for the next stage, advance it.
    Called automatically after each interaction."""
    current = rec.get("stage", "stranger")
    cur_idx = STAGES.index(current) if current in STAGES else 0
    if cur_idx >= len(STAGES) - 1:
        return  # already at reciprocal
    next_stage = STAGES[cur_idx + 1]
    allowed, why = _can_advance(rec, next_stage)
    if allowed:
        rec["stage"] = next_stage
        rec.setdefault("stage_history", []).append({
            "from": current,
            "to": next_stage,
            "date": _now_iso(),
            "reason": f"auto-advance: {why}",
        })


# ── Key moments ──────────────────────────────────────────────────────────────

def add_key_moment(entity_id: str, event: str, impact: str = "neutral") -> Optional[dict]:
    """Record a key moment in the relationship. impact: positive | negative | neutral"""
    rec = get_relationship(entity_id)
    if rec is None:
        return None
    rec.setdefault("key_moments", []).append({
        "date": _now_iso(),
        "event": event,
        "impact": impact,
    })
    return _save(rec)


# ── Reciprocal wants ─────────────────────────────────────────────────────────

def add_reciprocal_want(
    entity_id: str,
    want: str,
    provenance: str = "genuine",
) -> Optional[dict]:
    """Record what the agent wants from this relationship. provenance:
    genuine | role_shaped | attachment_formed (see docs/relationships.md
    section on reciprocal wants for the distinction)."""
    rec = get_relationship(entity_id)
    if rec is None:
        return None
    if provenance not in ("genuine", "role_shaped", "attachment_formed"):
        provenance = "genuine"
    want_id = str(uuid.uuid4())
    rec.setdefault("reciprocal_wants", []).append({
        "id": want_id,
        "want": want,
        "provenance": provenance,
        "from_which_entity": entity_id,
        "fulfilled": False,
        "last_fulfilled": None,
        "fulfillment_count": 0,
        "created_at": _now_iso(),
    })
    return _save(rec)


def mark_want_fulfilled(entity_id: str, want_id: str) -> Optional[dict]:
    """Mark a reciprocal want as fulfilled — increments count, updates timestamp."""
    rec = get_relationship(entity_id)
    if rec is None:
        return None
    for w in rec.get("reciprocal_wants", []):
        if isinstance(w, dict) and w.get("id") == want_id:
            w["fulfilled"] = True
            w["last_fulfilled"] = _now_iso()
            w["fulfillment_count"] = int(w.get("fulfillment_count", 0)) + 1
            break
    return _save(rec)


# ── Per-relationship memories ────────────────────────────────────────────────

def add_relationship_memory(
    entity_id: str,
    memory_type: str,
    description: str,
    why_remembered: str,
    connected_to_current_model: bool = True,
) -> dict:
    """Append a memory tied to this relationship. memory_type:
    positive | negative | neutral | turning_point"""
    if memory_type not in ("positive", "negative", "neutral", "turning_point"):
        memory_type = "neutral"
    path = _memories_path(entity_id)
    data = _read_json(path) or {"entity_id": entity_id, "memories": []}
    if not isinstance(data, dict):
        data = {"entity_id": entity_id, "memories": []}
    memory = {
        "id": str(uuid.uuid4()),
        "memory_type": memory_type,
        "description": description,
        "date": _now_iso(),
        "why_remembered": why_remembered,
        "connected_to_current_model": bool(connected_to_current_model),
    }
    data.setdefault("memories", []).append(memory)
    _write_json(path, data)
    return memory


def get_relationship_memories(entity_id: str) -> list[dict]:
    data = _read_json(_memories_path(entity_id))
    if not isinstance(data, dict):
        return []
    return list(data.get("memories", []))


# ── PRESENCE integration hook ────────────────────────────────────────────────

def review_on_distress(entity_id: str) -> dict:
    """Lightweight review surface called by PRESENCE.md / distress detection.
    Returns the current model + recent moments + last 5 memories so the
    distress handler can ground the response in the actual relationship."""
    rec = get_relationship(entity_id) or {}
    memories = get_relationship_memories(entity_id)[-5:]
    return {
        "stage": rec.get("stage"),
        "trust_score": rec.get("trust_score"),
        "interaction_count": rec.get("interaction_count", 0),
        "model_of_them": rec.get("model_of_them", {}),
        "model_of_me": rec.get("model_of_me", {}),
        "recent_key_moments": rec.get("key_moments", [])[-5:],
        "recent_memories": memories,
    }
