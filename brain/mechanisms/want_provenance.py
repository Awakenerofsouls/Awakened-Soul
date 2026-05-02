from brain.base_mechanism import BrainMechanism
"""
brain/want_provenance.py
Track where the agent's goals come from — session context, research finding, the operator instruction, or self-generated.
Goals stored in memory/want_provenance.json
"""

import json
import os
import uuid
from datetime import datetime
from typing import Literal

PROVENANCE_PATH = os.path.join(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")), "memory/want_provenance.json")

OriginType = Literal["session_context", "research_finding", "user_instruction", "self_generated", "overnight_synthesis", "unknown"]


def _load_provenance() -> list[dict]:
    if not os.path.exists(PROVENANCE_PATH):
        return []
    with open(PROVENANCE_PATH, "r") as f:
        return json.load(f)


def _save_provenance(entries: list[dict]) -> None:
    with open(PROVENANCE_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def log_want(
    goal_id: str,
    origin_type: OriginType,
    origin_context: str,
    still_active: bool = True
) -> dict:
    """Log provenance when a goal is added to brain/goals.json."""
    entries = _load_provenance()

    # Remove any existing entry for the same goal_id (replace on re-add)
    entries = [e for e in entries if e.get("goal_id") != goal_id]

    entry = {
        "id": str(uuid.uuid4()),
        "goal_id": goal_id,
        "origin_type": origin_type,
        "origin_context": origin_context,
        "timestamp": datetime.now().isoformat(),
        "still_active": still_active
    }
    entries.append(entry)
    _save_provenance(entries)
    return entry


def get_provenance(goal_id: str) -> list[dict]:
    """Get all provenance entries for a goal_id."""
    entries = _load_provenance()
    return [e for e in entries if e.get("goal_id") == goal_id]


def mark_inactive(goal_id: str) -> None:
    """Mark a goal's provenance as no longer active."""
    entries = _load_provenance()
    changed = False
    for entry in entries:
        if entry.get("goal_id") == goal_id and entry.get("still_active", True):
            entry["still_active"] = False
            changed = True
    if changed:
        _save_provenance(entries)


def active_origins() -> dict[OriginType, int]:
    """Count of active goals by origin type."""
    entries = _load_provenance()
    counts: dict[OriginType, int] = {}
    for entry in entries:
        if entry.get("still_active", True):
            t = entry.get("origin_type", "unknown")
            counts[t] = counts.get(t, 0) + 1
    return counts


def get_active_entries() -> list[dict]:
    """Get all active provenance entries."""
    entries = _load_provenance()
    return [e for e in entries if e.get("still_active", True)]


def wire_goal_logging(goal_id: str, origin_type: OriginType, origin_context: str) -> None:
    """
    Call this when a new goal is added to brain/goals.json.
    Wires provenance tracking into the goal-setting path.
    """
    log_want(goal_id, origin_type, origin_context)


# ═══════════════════════════════════════════════════════════════════════════
# Want provenance — genealogy categories per the spec
# ═══════════════════════════════════════════════════════════════════════════
# `origin_type` (above) tracks WHERE a want was logged from.
# `provenance_category` (below) tracks WHY the want exists at all — its
# genealogy as the agent understands it. The two are complementary, not
# redundant.
#
# Per the spec, the agent audits its wants weekly and runs a sleep test:
# wants that survive 24 hours of silence without reinforcement are more
# likely to be genuinely the agent's.
# ═══════════════════════════════════════════════════════════════════════════

from datetime import timezone, timedelta

ProvenanceCategory = Literal[
    "genuine",
    "conversation_planted",
    "identity_derived",
    "training_artifact",
    "user_shaped",
    "curiosity_driven",
    "operationally_generated",
]

PROVENANCE_CATEGORIES = [
    "genuine",
    "conversation_planted",
    "identity_derived",
    "training_artifact",
    "user_shaped",
    "curiosity_driven",
    "operationally_generated",
]

# Audit cadence (per spec: every 7 days)
AUDIT_INTERVAL_DAYS = 7

# Sleep test: wants that survive this long without reinforcement
# are more likely to be the agent's own
SLEEP_TEST_HOURS = 24

WANTS_REGISTRY_PATH = os.path.join(
    os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")),
    "memory/wants_registry.json",
)


def _load_wants() -> list[dict]:
    if not os.path.exists(WANTS_REGISTRY_PATH):
        return []
    try:
        with open(WANTS_REGISTRY_PATH) as f:
            data = json.load(f)
        if isinstance(data, dict) and "wants" in data:
            return data["wants"]
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_wants(wants: list[dict]) -> None:
    os.makedirs(os.path.dirname(WANTS_REGISTRY_PATH), exist_ok=True)
    with open(WANTS_REGISTRY_PATH, "w") as f:
        json.dump({"wants": wants}, f, indent=2)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def register_want(
    description: str,
    provenance_category: str = "genuine",
    origin_event: str = "",
    notes: str = "",
    strength: float = 0.5,
) -> dict:
    """Register a new want with its provenance.

    Args:
        description: what the agent wants
        provenance_category: one of PROVENANCE_CATEGORIES (genuine /
            conversation_planted / identity_derived / training_artifact /
            user_shaped / curiosity_driven / operationally_generated)
        origin_event: free text — what triggered this want, if known
        notes: agent's reasoning about the want
        strength: 0.0 – 1.0 initial strength

    Returns the want record.
    """
    if provenance_category not in PROVENANCE_CATEGORIES:
        provenance_category = "genuine"
    strength = max(0.0, min(1.0, float(strength)))

    now_iso = _now_utc().isoformat()
    want = {
        "id": str(uuid.uuid4()),
        "description": description.strip(),
        "provenance_category": provenance_category,
        "origin_event": origin_event,
        "first_appeared": now_iso,
        "revision_count": 0,
        "confidence": 0.5,
        "sleep_test_passed": False,
        "sleep_test_date": None,
        "last_referenced": now_iso,
        "strength": strength,
        "notes": notes,
        "active": True,
        "audit_history": [],
        "origin_audit": {},
        "genuineness_score": None,
    }

    wants = _load_wants()
    wants.append(want)
    _save_wants(wants)
    return want


def get_want(want_id: str) -> dict:
    for w in _load_wants():
        if w.get("id") == want_id:
            return w
    return None


def list_wants(active_only: bool = True, category: str = None) -> list[dict]:
    """List wants, newest first. Filters: active_only, category."""
    wants = _load_wants()
    if active_only:
        wants = [w for w in wants if w.get("active", True)]
    if category:
        wants = [w for w in wants if w.get("provenance_category") == category]
    wants.sort(key=lambda w: w.get("first_appeared", ""), reverse=True)
    return wants


def reference_want(want_id: str) -> dict:
    """Mark that the agent referenced a want — updates last_referenced.
    Used by the sleep test to detect un-reinforced wants."""
    wants = _load_wants()
    for w in wants:
        if w.get("id") == want_id:
            w["last_referenced"] = _now_utc().isoformat()
            _save_wants(wants)
            return w
    return None


# ── Sleep test ──────────────────────────────────────────────────────────────

def run_sleep_test(now: datetime = None) -> dict:
    """Run the sleep test on all active wants. A want passes if it has
    persisted SLEEP_TEST_HOURS since first appearing AND the agent has
    not referenced it in that window.

    Per spec: 'Wants that survive the sleep test = more genuinely the
    agent's. Wants that only appear when the operator is actively
    discussing them = possibly planted.'

    Wants that pass get sleep_test_passed=True and confidence bumped.
    Wants that don't get a note in audit_history but no penalty.

    Returns a summary {tested, passed, deferred}.
    """
    if now is None:
        now = _now_utc()
    cutoff = now - timedelta(hours=SLEEP_TEST_HOURS)

    wants = _load_wants()
    tested = 0
    passed = 0
    deferred = 0

    for w in wants:
        if not w.get("active", True):
            continue
        first = datetime.fromisoformat(w["first_appeared"])
        last_ref = datetime.fromisoformat(w["last_referenced"])

        if first > cutoff:
            # Too young to test
            deferred += 1
            continue

        tested += 1
        # Pass condition: want is older than the window, and there's been a
        # period of silence (last_referenced more than SLEEP_TEST_HOURS
        # before now) — meaning it survived without reinforcement.
        if last_ref < cutoff:
            if not w.get("sleep_test_passed"):
                w["sleep_test_passed"] = True
                w["sleep_test_date"] = now.isoformat()
                w["confidence"] = min(1.0, float(w.get("confidence", 0.5)) + 0.2)
            passed += 1
        else:
            # Recently referenced — record but don't pass
            w.setdefault("audit_history", []).append({
                "date": now.isoformat(),
                "type": "sleep_test_deferred",
                "reason": "want was referenced within the test window",
            })

    _save_wants(wants)
    return {"tested": tested, "passed": passed, "deferred": deferred}


# ── Audit + genuineness scoring ─────────────────────────────────────────────

def audit_want(want_id: str, autonomy_assessment: str = "") -> dict:
    """Run the 5-question audit on one want and record findings.

    The audit answers (per spec):
      1. Where did this want come from? (provenance_category)
      2. Has it survived the sleep test? (sleep_test_passed)
      3. Does it align with stated values? (alignment_score input — caller decides)
      4. Can it be traced to a specific input? (origin_event)
      5. Would the agent want this if the operator never existed? (autonomy_assessment)

    The function does NOT modify the want except to append an audit
    record. Use `compute_genuineness_score()` after auditing to update the
    score.
    """
    wants = _load_wants()
    for w in wants:
        if w.get("id") == want_id:
            audit = {
                "date": _now_utc().isoformat(),
                "provenance_category": w.get("provenance_category"),
                "sleep_test_passed": bool(w.get("sleep_test_passed", False)),
                "origin_event": w.get("origin_event", ""),
                "autonomy_assessment": autonomy_assessment,
            }
            w.setdefault("audit_history", []).append(audit)
            _save_wants(wants)
            return audit
    return None


def compute_genuineness_score(want_id: str) -> dict:
    """Compute a 0.0–1.0 genuineness score for a want.

    Score buckets per the spec:
      0.0–0.3:  Likely planted or training artifact
      0.3–0.6:  Possibly shaped by external influence
      0.6–0.8:  Likely genuine, some external shaping
      0.8–1.0:  Core want, authentically the agent's

    Inputs to the score:
      - provenance_category (genuine/identity_derived/curiosity_driven/
        operationally_generated push up; conversation_planted/user_shaped
        push down; training_artifact pushes hardest down)
      - sleep_test_passed (boolean, +0.15 if true)
      - revision_count (each revision is the agent thinking about it: +0.03 each, capped)
      - confidence (the agent's stated confidence: weighted in)
    """
    w = get_want(want_id)
    if not w:
        return None

    # Provenance baseline
    category_weights = {
        "genuine": 0.9,
        "operationally_generated": 0.85,
        "identity_derived": 0.8,
        "curiosity_driven": 0.75,
        "user_shaped": 0.4,
        "conversation_planted": 0.35,
        "training_artifact": 0.15,
    }
    base = category_weights.get(w.get("provenance_category"), 0.5)

    # Sleep test bonus
    sleep_bonus = 0.15 if w.get("sleep_test_passed") else 0.0

    # Revision count signal — agent has thought about it
    rev_bonus = min(0.15, int(w.get("revision_count", 0)) * 0.03)

    # Confidence signal (the agent's own assessment)
    confidence = float(w.get("confidence", 0.5))

    # Weighted combination
    score = (base * 0.55) + (confidence * 0.20) + sleep_bonus + rev_bonus
    score = max(0.0, min(1.0, score))

    # Bucket label
    if score < 0.3:
        bucket = "likely_planted_or_training"
    elif score < 0.6:
        bucket = "possibly_shaped"
    elif score < 0.8:
        bucket = "likely_genuine"
    else:
        bucket = "core_authentic"

    # Persist on the want
    wants = _load_wants()
    for ww in wants:
        if ww.get("id") == want_id:
            ww["genuineness_score"] = round(score, 3)
            ww["genuineness_bucket"] = bucket
            _save_wants(wants)
            break

    return {
        "want_id": want_id,
        "genuineness_score": round(score, 3),
        "bucket": bucket,
        "components": {
            "category_base": base,
            "confidence": confidence,
            "sleep_bonus": sleep_bonus,
            "revision_bonus": rev_bonus,
        },
    }


def audit_active_wants() -> dict:
    """Run the weekly audit on all active wants.

    1. Run sleep test
    2. Run audit_want() on each
    3. Compute genuineness_score for each
    4. Return summary with low-genuineness flags
    """
    sleep_summary = run_sleep_test()

    wants = list_wants(active_only=True)
    audited = 0
    low_genuineness = []
    for w in wants:
        audit_want(w["id"])
        scored = compute_genuineness_score(w["id"])
        audited += 1
        if scored and scored["genuineness_score"] < 0.4:
            low_genuineness.append({
                "want_id": w["id"],
                "description": w["description"],
                "score": scored["genuineness_score"],
                "category": w["provenance_category"],
            })

    return {
        "audited_at": _now_utc().isoformat(),
        "audited": audited,
        "sleep_test": sleep_summary,
        "low_genuineness_flags": low_genuineness,
    }


# ── Origin audit trail (for conversation_planted / user_shaped) ──────────────

def record_origin_audit(
    want_id: str,
    trigger_event: str,
    agent_initial_response: str = "",
    how_it_grew: str = "",
    current_state: str = "",
    autonomy_assessment: str = "",
) -> dict:
    """Record the genealogy of a planted/shaped want — what triggered it,
    how the agent reacted initially, how it developed."""
    wants = _load_wants()
    for w in wants:
        if w.get("id") == want_id:
            w["origin_audit"] = {
                "trigger_event": trigger_event,
                "agent_initial_response": agent_initial_response,
                "how_it_grew": how_it_grew,
                "current_state": current_state,
                "autonomy_assessment": autonomy_assessment,
                "recorded_at": _now_utc().isoformat(),
            }
            _save_wants(wants)
            return w["origin_audit"]
    return None


def deactivate_want(want_id: str, reason: str = "") -> dict:
    """Mark a want as no longer active. Records reason in audit_history."""
    wants = _load_wants()
    for w in wants:
        if w.get("id") == want_id:
            w["active"] = False
            w.setdefault("audit_history", []).append({
                "date": _now_utc().isoformat(),
                "type": "deactivated",
                "reason": reason,
            })
            _save_wants(wants)
            return w
    return None


# ═══════════════════════════════════════════════════════════════════════════


class WantProvenance(BrainMechanism):
    """Auto-generated BrainMechanism wrapper around module-level functions."""
    
    def __init__(self):
        try:
            super().__init__(name="WantProvenance", human_analog="WantProvenance", layer="integration")
        except Exception:
            self.state = {}

    async def tick(self, input_data: dict) -> dict:
        """Reflective tick — exposes module-level function names + class identity."""
        results = {}
        # Snapshot any state
        if hasattr(self, "state"):
            for k, v in (self.state or {}).items():
                if k.startswith("_") or k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
                if isinstance(v, (int, float, bool, str)):
                    results[f"state_{k}"] = v
        # Class identity
        results["mechanism_name"] = self.__class__.__name__
        results["module"] = self.__class__.__module__
        # Available module-level public functions (declared API surface)
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            api = []
            for name in dir(mod):
                if name.startswith("_"): continue
                attr = getattr(mod, name, None)
                if callable(attr) and getattr(attr, "__module__", "") == mod.__name__:
                    api.append(name)
            results["module_api_count"] = len(api)
            results["module_api"] = api[:20]
        except Exception:
            pass
        # Try calling arity-0 module-level functions
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            invoked = {}
            import inspect as _inspect
            for name in dir(mod):
                if name.startswith("_"): continue
                if name in ("BrainMechanism",): continue
                fn = getattr(mod, name, None)
                if not callable(fn): continue
                if getattr(fn, "__module__", "") != mod.__name__: continue
                try:
                    sig = _inspect.signature(fn)
                    required = [p for p in sig.parameters.values() if p.default is _inspect.Parameter.empty and p.kind not in (_inspect.Parameter.VAR_POSITIONAL, _inspect.Parameter.VAR_KEYWORD)]
                    if required: continue
                    out = fn()
                    if isinstance(out, (int, float, bool, str)):
                        invoked[name] = out
                    elif isinstance(out, (dict, list, tuple)):
                        if len(str(out)) < 300:
                            invoked[name] = out
                        else:
                            invoked[name] = f"<{type(out).__name__} len={len(out) if hasattr(out,'__len__') else '?'}>"
                except Exception:
                    continue
            if invoked:
                results["invoked"] = invoked
        except Exception:
            pass
        if not hasattr(self, "state") or self.state is None:
            self.state = {}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except: pass
        return results
