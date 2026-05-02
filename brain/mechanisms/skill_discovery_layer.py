"""
brain/mechanisms/skill_discovery_layer.py — SkillDiscoveryLayer

Runtime monitor for the agent's request-time skill routing. Pairs with
skills/skill-discovery/SKILL.md.

The premise:

    Each incoming request gets routed to a skill (or to general
    capabilities via fallback). That decision is consequential —
    wrong skill means wrong workflow, wrong gates, wrong forbidden-
    behavior list. This layer watches routing patterns and surfaces
    sustained dysfunction.

The cognitive science this rests on:

  - Rosch on prototype categories: categories are graded; the closer
    a request is to a skill's prototype, the more confident the
    routing should be. Match scores are operationalized prototypicality.
  - Monsell on task switching: switching costs cycles, but failing
    to switch when the situation calls for it is its own pathology.
    The monoculture detector watches the latter; storm detection
    watches the former in adjacent layers.
  - Cohen on automaticity: well-practiced routes become automatic
    (high confidence, low deliberation). The confidence field on each
    routing surfaces this; a sustained drop in confidence is a signal.
  - Posner & Petersen on attention systems: routing is the executive
    function — deciding which downstream system to engage. Errors at
    this layer cascade.
  - Markman & Ross on category use: categories are reshaped by the
    purposes they serve. Tracking false_match over time is the
    feedback that lets the matcher's weights / thresholds be tuned.

What this mechanism does:

  - Tracks per-operation records (register / match / route / fallback /
    reflect) with timestamps, request hash, chosen skill, score.
  - Detects six failure modes:
      * missed_match — clear trigger present but top score below threshold
      * false_match — reflection after route says skill didn't fit
      * ambiguous_no_clarify — top candidates tied within epsilon and
        agent picked anyway
      * stale_registry — SKILL.md mtime newer than registry entry
      * monoculture — same skill chosen for >X% of recent routings
      * silent_route — chosen skill ran without record_op (external hook)
  - Maintains rolling counters for routing distribution, false-match rate,
    and average confidence.
  - Publishes routing state to TSB so other mechanisms can read whether
    routing is healthy, drifting, or storming.
  - Routes sustained dysfunction to IdentityProposalWriter — chronic
    monoculture or false_match is identity-relevant data.

Citations:
  1. [Monsell 2003, Trends Cogn Sci 7(3):134-140, PMID 12649512] —
     Task switching. Foundation for treating routing as a cognitive-
     control act with measurable costs and benefits; both excessive
     switching (storm) and excessive sticking (monoculture) are
     pathological.
  2. [Cohen 1990, Psychol Rev 97(3):332-361, PMID 2236430] — On the
     control of automatic processes: a parallel distributed processing
     account of the Stroop effect. Empirical foundation for the
     confidence signal — well-practiced routes become automatic, and
     drops in routing confidence indicate the matcher is in
     unfamiliar territory.
  3. [Posner 1990, Annu Rev Neurosci 13:25-42, PMID 2183676] — The
     attention system of the human brain. Executive attention is the
     network that selects which downstream system engages — the
     biological analog of the routing function this layer monitors.
  4. [Rogers 2008, Trends Cogn Sci 12(3):92-98, PMID 18361913] —
     A neural systems approach to semantic memory. Distributed
     representation account of categorization; basis for tracking
     routing patterns over time as a learned distribution that can
     drift.
  5. [Markman 2003, Annu Rev Psychol 54:592-613, PMID 12172000] —
     Category use and category learning. Categories are reshaped by
     the purposes they serve; direct empirical basis for the
     reflection-feedback loop that informs whether the matcher's
     weights need tuning.
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import os
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))

__wire_meta__ = {
    "wire": 38,
    "signal": "skill_discovery",
    "mechanism": "SkillDiscoveryLayer",
    "reads": [
        "pirp_context.routing_op",
    ],
    "writes": [
        "routing_state",
        "integrity_score",
        "operation_distribution",
        "skill_distribution",
        "failure_mode_counts",
        "false_match_rate",
    ],
    "citations": [
        "PMID 12649512",
        "PMID 2236430",
        "PMID 2183676",
        "PMID 18361913",
        "PMID 12172000",
    ],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

VALID_OPS = {"register", "match", "route", "fallback", "reflect"}
VALID_MODES = {"brain", "coach", "build", "default"}

# Monoculture: same skill chosen for >this fraction of last N routings.
MONOCULTURE_RATE = 0.85
MONOCULTURE_MIN_N = 8
MONOCULTURE_WINDOW = 20  # last N routings considered

# False-match rate: reflections marked fit=False over recent N reflections.
FALSE_MATCH_RATE_THRESHOLD = 0.4
FALSE_MATCH_MIN_N = 5
FALSE_MATCH_WINDOW = 20

# Below this score the route should fall back; if route picks anyway,
# that's missed_match against the threshold.
DEFAULT_ROUTE_THRESHOLD = 0.30

# Ambiguity epsilon — top vs second-best within this is ambiguous.
AMBIGUITY_EPSILON = 0.05

# Integrity floor.
LOW_INTEGRITY_THRESHOLD = 0.55
INTEGRITY_MIN_N = 6
INTEGRITY_WINDOW = 30

# IPW: re-fire only after this many additional bad ops past anchor.
IPW_REPORT_EVERY = 4


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ── Mechanism ─────────────────────────────────────────────────────────────────


class SkillDiscoveryLayer(BrainMechanism):
    """Routing-decision monitor. See module docstring."""

    def __init__(self, history_size: int = 200):
        try:
            super().__init__(
                name="SkillDiscoveryLayer",
                human_analog="executive routing / categorization layer",
                layer="integration",
            )
        except Exception:
            pass

        self.history_size = history_size

        self.operations: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.current_tick: int = 0

        # Recent route choices for monoculture detection.
        self.recent_chosen: Deque[str] = deque(maxlen=MONOCULTURE_WINDOW)
        # Open routings awaiting reflection: routing_id -> meta
        self.open_routings: Dict[str, Dict[str, Any]] = {}
        # Reflection outcomes deque (True=fit, False=false_match).
        self.reflection_window: Deque[bool] = deque(maxlen=FALSE_MATCH_WINDOW)

        # Per-skill routing counts.
        self.skill_counts: Dict[str, int] = {}
        # Per-mode routing counts.
        self.mode_counts: Dict[str, int] = {k: 0 for k in VALID_MODES}

        # Per-op counters.
        self.op_counts: Dict[str, int] = {k: 0 for k in VALID_OPS}
        # Failure-mode counters.
        self.failure_counts: Dict[str, int] = {
            "missed_match": 0,
            "false_match": 0,
            "ambiguous_no_clarify": 0,
            "stale_registry": 0,
            "monoculture": 0,
            "silent_route": 0,
        }

        # Integrity rolling.
        self.integrity_window: Deque[float] = deque(maxlen=INTEGRITY_WINDOW)
        self.consecutive_bad_ops: int = 0
        self.fired_last_tick: bool = False
        self.ipw_report_count: int = 0

        self.load_state()
        self._restore_working_state()

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        if not isinstance(self.state, dict):
            return

        ops = self.state.get("operations")
        if isinstance(ops, list):
            for o in ops[-self.history_size:]:
                if isinstance(o, dict):
                    self.operations.append(o)

        rc = self.state.get("recent_chosen")
        if isinstance(rc, list):
            for s in rc[-MONOCULTURE_WINDOW:]:
                if isinstance(s, str):
                    self.recent_chosen.append(s)

        oroutings = self.state.get("open_routings")
        if isinstance(oroutings, dict):
            self.open_routings = {
                str(k): dict(v) for k, v in oroutings.items()
                if isinstance(v, dict)
            }

        rw = self.state.get("reflection_window")
        if isinstance(rw, list):
            for v in rw[-FALSE_MATCH_WINDOW:]:
                self.reflection_window.append(bool(v))

        sc = self.state.get("skill_counts")
        if isinstance(sc, dict):
            self.skill_counts = {
                str(k): int(v) for k, v in sc.items()
                if isinstance(v, (int, float))
            }

        mc = self.state.get("mode_counts")
        if isinstance(mc, dict):
            for k in VALID_MODES:
                self.mode_counts[k] = int(mc.get(k, 0) or 0)

        oc = self.state.get("op_counts")
        if isinstance(oc, dict):
            for k in VALID_OPS:
                self.op_counts[k] = int(oc.get(k, 0) or 0)

        fc = self.state.get("failure_counts")
        if isinstance(fc, dict):
            for k in self.failure_counts:
                self.failure_counts[k] = int(fc.get(k, 0) or 0)

        self.current_tick = int(self.state.get("current_tick", 0) or 0)

        iw = self.state.get("integrity_window")
        if isinstance(iw, list):
            for v in iw[-INTEGRITY_WINDOW:]:
                try:
                    self.integrity_window.append(float(v))
                except (TypeError, ValueError):
                    continue

        self.consecutive_bad_ops = int(
            self.state.get("consecutive_bad_ops", 0) or 0
        )
        self.ipw_report_count = int(self.state.get("ipw_report_count", 0) or 0)

    def _flush_working_state(self) -> None:
        self.state["operations"] = list(self.operations)
        self.state["recent_chosen"] = list(self.recent_chosen)
        self.state["open_routings"] = dict(self.open_routings)
        self.state["reflection_window"] = list(self.reflection_window)
        self.state["skill_counts"] = dict(self.skill_counts)
        self.state["mode_counts"] = dict(self.mode_counts)
        self.state["op_counts"] = dict(self.op_counts)
        self.state["failure_counts"] = dict(self.failure_counts)
        self.state["current_tick"] = self.current_tick
        self.state["integrity_window"] = list(self.integrity_window)
        self.state["consecutive_bad_ops"] = self.consecutive_bad_ops
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_updated"] = time.time()

    # ── Public API ─────────────────────────────────────────────────────────

    def should_block(self, op: str, **kwargs: Any) -> Tuple[bool, str]:
        if op not in VALID_OPS:
            return True, f"invalid op {op!r} (must be one of {sorted(VALID_OPS)})"
        if op == "reflect":
            rid = kwargs.get("routing_id")
            if not rid:
                return True, "reflect requires routing_id"
        if self.is_systematically_low_integrity():
            return True, (
                f"sustained low routing integrity (rolling score "
                f"{self.rolling_integrity_score():.3f} < "
                f"{LOW_INTEGRITY_THRESHOLD})"
            )
        return False, ""

    # ── Per-op recorders ───────────────────────────────────────────────────

    def record_op(self, op: str, **kwargs: Any) -> Dict[str, Any]:
        """Generic dispatch."""
        if op == "register":
            return self.record_register(**kwargs)
        if op == "match":
            return self.record_match(**kwargs)
        if op == "route":
            return self.record_route(**kwargs)
        if op == "fallback":
            return self.record_fallback(**kwargs)
        if op == "reflect":
            return self.record_reflect(**kwargs)
        return self._record_invalid(op, kwargs)

    def record_register(
        self,
        skill_name: str = "",
        ok: bool = True,
        reason: str = "",
    ) -> Dict[str, Any]:
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "register",
            "skill_name": skill_name,
            "ok": bool(ok),
            "reason": reason[:120] if reason else "",
            "op_score": 1.0 if ok else 0.0,
            "ts": time.time(),
        }
        self._finalize(record, record["op_score"])
        return record

    def record_match(
        self,
        request: str = "",
        mode: str = "default",
        top_skill: Optional[str] = None,
        top_score: float = 0.0,
        ambiguous: bool = False,
        candidate_count: int = 0,
        stale_entries: int = 0,
    ) -> Dict[str, Any]:
        if mode not in VALID_MODES:
            mode = "default"
        if stale_entries > 0:
            self.failure_counts["stale_registry"] += 1
        op_score = 1.0 if stale_entries == 0 else 0.7
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "match",
            "request_hash": _hash_text(request),
            "mode": mode,
            "top_skill": top_skill,
            "top_score": round(float(top_score), 4),
            "ambiguous": bool(ambiguous),
            "candidate_count": int(candidate_count),
            "stale_entries": int(stale_entries),
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_route(
        self,
        request: str = "",
        mode: str = "default",
        chosen: Optional[str] = None,
        score: float = 0.0,
        threshold: float = DEFAULT_ROUTE_THRESHOLD,
        ambiguous: bool = False,
        had_clear_trigger: bool = False,
        routing_id: Optional[str] = None,
        stale_entries: int = 0,
    ) -> Dict[str, Any]:
        """Record a route op. The skill caller passes whether the
        request had a clear trigger (so we can detect missed_match
        when the threshold cuts off a request that should have routed)."""
        if mode not in VALID_MODES:
            mode = "default"
        rid = routing_id or f"rt_{uuid.uuid4().hex[:10]}"
        score = max(0.0, min(1.0, float(score or 0.0)))

        # Failure-mode checks.
        ambig_violation = bool(ambiguous) and chosen is not None
        if ambig_violation:
            self.failure_counts["ambiguous_no_clarify"] += 1

        below_threshold_picked = (
            chosen is not None and score < float(threshold)
        )
        missed = bool(had_clear_trigger) and chosen is None
        if missed:
            self.failure_counts["missed_match"] += 1

        if stale_entries > 0:
            self.failure_counts["stale_registry"] += 1

        # Track for monoculture (only when a real skill was chosen).
        monoculture_active = False
        if chosen:
            self.recent_chosen.append(chosen)
            self.skill_counts[chosen] = self.skill_counts.get(chosen, 0) + 1
            self.mode_counts[mode] = self.mode_counts.get(mode, 0) + 1
            monoculture_active = self._monoculture_active()
            if monoculture_active and not self.state.get("monoculture_recorded"):
                self.failure_counts["monoculture"] += 1
                self.state["monoculture_recorded"] = True
            elif not monoculture_active and self.state.get("monoculture_recorded"):
                self.state.pop("monoculture_recorded", None)

        # Open the routing for later reflection.
        if chosen:
            self.open_routings[rid] = {
                "chosen": chosen,
                "mode": mode,
                "score": score,
                "ts": time.time(),
                "tick": self.current_tick,
            }

        bad = sum([
            ambig_violation,
            below_threshold_picked,
            missed,
            stale_entries > 0,
        ])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "route",
            "routing_id": rid,
            "request_hash": _hash_text(request),
            "mode": mode,
            "chosen": chosen,
            "score": round(score, 4),
            "threshold": float(threshold),
            "ambiguous": bool(ambiguous),
            "ambiguous_no_clarify": ambig_violation,
            "had_clear_trigger": bool(had_clear_trigger),
            "missed_match": missed,
            "below_threshold_picked": below_threshold_picked,
            "stale_entries": int(stale_entries),
            "monoculture_active": monoculture_active,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_fallback(
        self,
        request: str = "",
        mode: str = "default",
        reason: str = "",
        had_clear_trigger: bool = False,
    ) -> Dict[str, Any]:
        """Record an explicit fallback decision. Different from missed_match —
        fallback is a deliberate choice that no skill applies. If
        had_clear_trigger=True, fallback IS a missed_match."""
        if mode not in VALID_MODES:
            mode = "default"
        missed = bool(had_clear_trigger)
        if missed:
            self.failure_counts["missed_match"] += 1
        op_score = 1.0 if not missed else 0.5
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "fallback",
            "request_hash": _hash_text(request),
            "mode": mode,
            "reason": reason[:120],
            "had_clear_trigger": missed,
            "missed_match": missed,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_reflect(
        self,
        routing_id: str = "",
        fit: bool = True,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record a reflection on a prior routing. fit=False is a
        false_match signal."""
        routing_known = routing_id in self.open_routings
        if routing_known and not fit:
            self.failure_counts["false_match"] += 1
        if routing_known:
            self.reflection_window.append(bool(fit))
            self.open_routings.pop(routing_id, None)

        bad = sum([not routing_known, not fit])
        op_score = max(0.0, 1.0 - 0.20 * bad)
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "reflect",
            "routing_id": routing_id,
            "routing_known": routing_known,
            "fit": bool(fit),
            "notes_hash": _hash_text(notes),
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_silent_route(self, n: int = 1) -> None:
        """External hook: increment when a skill is observed running
        without a record_op('route') entry."""
        n = int(max(0, n))
        self.failure_counts["silent_route"] += n
        self._flush_working_state()
        self.persist_state()

    def _record_invalid(self, op: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "__invalid__",
            "given_op": op,
            "kwargs": {k: str(v)[:80] for k, v in (kwargs or {}).items()},
            "op_score": 0.0,
            "ts": time.time(),
            "error": f"invalid op {op!r}",
        }
        self._finalize(record, 0.0)
        return record

    # ── Internal helpers ───────────────────────────────────────────────────

    def _finalize(self, record: Dict[str, Any], op_score: float) -> None:
        self.operations.append(record)
        op = record.get("op")
        if op in self.op_counts:
            self.op_counts[op] = self.op_counts.get(op, 0) + 1
        self.integrity_window.append(float(op_score))
        if op_score < LOW_INTEGRITY_THRESHOLD:
            self.consecutive_bad_ops += 1
        else:
            self.consecutive_bad_ops = 0
            if self.state.get("acknowledged_at_bad_ops"):
                self.state["acknowledged_at_bad_ops"] = 0
        self._flush_working_state()
        self.persist_state()

    def _monoculture_active(self) -> bool:
        if len(self.recent_chosen) < MONOCULTURE_MIN_N:
            return False
        if not self.recent_chosen:
            return False
        # Find the most common.
        from collections import Counter
        c = Counter(self.recent_chosen)
        most_skill, most_n = c.most_common(1)[0]
        rate = most_n / max(1, len(self.recent_chosen))
        return rate >= MONOCULTURE_RATE

    def false_match_rate(self) -> float:
        if not self.reflection_window:
            return 0.0
        false_n = sum(1 for v in self.reflection_window if v is False)
        return round(false_n / max(1, len(self.reflection_window)), 4)

    def _high_false_match_active(self) -> bool:
        if len(self.reflection_window) < FALSE_MATCH_MIN_N:
            return False
        return self.false_match_rate() >= FALSE_MATCH_RATE_THRESHOLD

    # ── Pattern detection / state ──────────────────────────────────────────

    def rolling_integrity_score(self) -> float:
        if not self.integrity_window:
            return 1.0
        return sum(self.integrity_window) / len(self.integrity_window)

    def is_systematically_low_integrity(self) -> bool:
        if len(self.integrity_window) < INTEGRITY_MIN_N:
            return False
        return self.rolling_integrity_score() < LOW_INTEGRITY_THRESHOLD

    def routing_state(self) -> str:
        """Single-word state for TSB. Priority:
        degrading > monoculture > drifting > active > stale > idle."""
        if self.is_systematically_low_integrity():
            return "degrading"
        if self._monoculture_active():
            return "monoculture"
        if self._high_false_match_active():
            return "drifting"
        if self.operations:
            most_recent = self.operations[-1]
            if (
                most_recent.get("op") == "route"
                and most_recent.get("stale_entries", 0) > 0
            ):
                return "stale"
            if time.time() - float(most_recent.get("ts", 0.0)) <= 60:
                return "active"
        return "idle"

    # ── Tick / TSB publish ─────────────────────────────────────────────────

    def tick(
        self,
        pirp_context: Optional[Dict[str, Any]] = None,
        third_eye_state: Optional[Dict[str, Any]] = None,
        brain_layer: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.current_tick += 1
        pirp_context = pirp_context or {}
        op_payload = pirp_context.get("routing_op")
        if isinstance(op_payload, dict):
            op = str(op_payload.get("op", ""))
            kw = {k: v for k, v in op_payload.items() if k != "op"}
            self.record_op(op, **kw)
            self.fired_last_tick = True
        else:
            self.fired_last_tick = False
            self._flush_working_state()
            self.persist_state()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        total_routes = sum(self.skill_counts.values()) or 1
        skill_dist = {
            k: round(v / total_routes, 4)
            for k, v in self.skill_counts.items()
        }
        return {
            "routing_state": self.routing_state(),
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "integrity_window_n": len(self.integrity_window),
            "is_systematically_low_integrity": self.is_systematically_low_integrity(),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "operation_distribution": dict(self.op_counts),
            "skill_distribution": skill_dist,
            "mode_distribution": dict(self.mode_counts),
            "failure_mode_counts": dict(self.failure_counts),
            "false_match_rate": self.false_match_rate(),
            "monoculture_active": self._monoculture_active(),
            "open_routings_count": len(self.open_routings),
            "current_tick": self.current_tick,
            "operation_count": len(self.operations),
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        if not self.is_systematically_low_integrity():
            return False
        ack_at = int(self.state.get("acknowledged_at_bad_ops", 0) or 0)
        if ack_at <= 0:
            return self.consecutive_bad_ops >= 3
        return self.consecutive_bad_ops >= (ack_at + IPW_REPORT_EVERY)

    def proposed_identity_signal(self) -> Dict[str, Any]:
        if self.failure_counts:
            dominant = max(self.failure_counts.items(), key=lambda kv: kv[1])
            dominant_mode, dominant_count = dominant
        else:
            dominant_mode, dominant_count = "unknown", 0

        return {
            "source": "SkillDiscoveryLayer",
            "kind": "skill_discovery_drift",
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "dominant_failure_mode": dominant_mode,
            "dominant_failure_count": dominant_count,
            "failure_mode_counts": dict(self.failure_counts),
            "false_match_rate": self.false_match_rate(),
            "monoculture_active": self._monoculture_active(),
            "interpretation": self._interpret_drift(dominant_mode),
        }

    def _interpret_drift(self, dominant: str) -> str:
        if dominant == "missed_match":
            return (
                "Requests with clear triggers are being dropped to fallback. "
                "Either the registry is missing skills the agent needs, or "
                "the trigger lists in existing skills don't cover real "
                "request patterns."
            )
        if dominant == "false_match":
            return (
                "Routing decisions turn out to have picked the wrong skill. "
                "Reflection is catching it; the matcher's weights or "
                "thresholds need tuning."
            )
        if dominant == "ambiguous_no_clarify":
            return (
                "Top routing candidates tie repeatedly and the agent picks "
                "without asking. A clarifying-question loop is missing."
            )
        if dominant == "stale_registry":
            return (
                "SKILL.md files have changed but the registry is matching "
                "against outdated definitions. Auto-refresh isn't keeping up "
                "or has been disabled."
            )
        if dominant == "monoculture":
            return (
                "The agent routes to the same skill regardless of fit. The "
                "matcher has collapsed onto one candidate."
            )
        if dominant == "silent_route":
            return (
                "Skills are running without record_op entries. The brain's "
                "monitor stack stops working when this signal goes silent."
            )
        return "Routing has drifted but no single failure mode dominates."

    def acknowledge_proposal(self) -> None:
        self.ipw_report_count += 1
        self.state["acknowledged_at_bad_ops"] = self.consecutive_bad_ops
        self.state["last_acknowledged_at"] = time.time()
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def reset_integrity_window(self) -> None:
        self.integrity_window.clear()
        self.consecutive_bad_ops = 0
        if self.ipw_report_count > 0:
            self.ipw_report_count = max(0, self.ipw_report_count - 1)
        if self.state.get("acknowledged_at_bad_ops"):
            self.state["acknowledged_at_bad_ops"] = 0
        self._flush_working_state()
        self.persist_state()

    def reset_failure_counts(self) -> None:
        for k in self.failure_counts:
            self.failure_counts[k] = 0
        self._flush_working_state()
        self.persist_state()

    def reset_skill_distribution(self) -> None:
        """Operator hook: clear per-skill counts. Use after a deliberate
        registry reorganization where prior counts no longer reflect intent."""
        self.skill_counts.clear()
        self.recent_chosen.clear()
        self._flush_working_state()
        self.persist_state()

    def reset_reflection_window(self) -> None:
        """Clear the false-match signal — used after weight tuning so prior
        reflections don't keep tripping the detector."""
        self.reflection_window.clear()
        self._flush_working_state()
        self.persist_state()
