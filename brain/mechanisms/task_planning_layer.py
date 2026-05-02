"""
brain/mechanisms/task_planning_layer.py — TaskPlanningLayer

Runtime monitor for the agent's planning act. Pairs with
skills/task-planning/SKILL.md.

The premise:

    Planning is the prefrontal act of converting a goal into a
    structured, ordered plan. It's distinct from doing (motor / action
    layer) and from deciding (whichever skill executes the plan).
    Planning has its own failure modes — over- or under-decomposition,
    plan storms, stale plans, abandoned plans without retrospective —
    and this layer watches them.

The cognitive science this rests on:

  - Miller & Cohen on PFC integrative control: the prefrontal cortex
    maintains active goal representations that bias processing
    throughout the rest of the brain. Planning is the explicit version
    of that maintenance.
  - D'Esposito on working memory: working memory has limited capacity.
    Plans that overflow it get fragmented or abandoned. The
    over-decomposition / under-decomposition detectors track exactly
    this.
  - Stuss on frontal-lobe functions: the supervisory attentional
    system monitors plan execution and signals when revision is needed.
    Stale-plan detection is the absence of supervision.
  - Koechlin on PFC cascade hierarchy: different prefrontal regions
    handle different planning time-scales (immediate / contextual /
    temporal / branching). The horizon distribution this layer tracks
    is a measure of which time-scale the agent is operating at.
  - Badre on cognitive control hierarchy: abstract goals decompose into
    more concrete subgoals through hierarchical control. Revision is
    the back-up-and-redescend when a step doesn't pan out.

What this mechanism does:

  - Tracks per-operation records (decompose / commit / revise / complete /
    reflect).
  - Detects six failure modes:
      * over_decomposition — > MAX_SUBTASKS_PER_GOAL
      * under_decomposition — multi-part goal, too few subtasks
      * stale_plan — active plan untouched past STALE_PLAN_TICK_THRESHOLD
      * plan_storm — > N decomposes in W ticks without commit
      * incomplete_plans — active plans abandoned without complete/abandon
      * missing_reflection — completed plan past reflection deadline
  - Maintains rolling counters for plan-state transitions, mode
    distribution at decompose time, horizon distribution.
  - Publishes planning state to TSB so other mechanisms (e.g.
    PersonaCoherenceLayer, MakingLayer) can read whether planning is
    healthy, storming, or paralyzed.
  - Routes sustained dysfunction to IdentityProposalWriter — chronic
    plan_storm or missing_reflection is identity-relevant data.

Citations:
  1. [Miller 2001, Annu Rev Neurosci 24:167-202, PMID 11283309] —
     An integrative theory of prefrontal cortex function. Foundation
     for treating planning as the explicit maintenance of active goal
     representations that bias the rest of cognition.
  2. [D'Esposito 2015, Annu Rev Psychol 66:115-142, PMID 25251493] —
     The cognitive neuroscience of working memory. Capacity limits on
     active goal maintenance; direct empirical basis for the
     over_decomposition / under_decomposition detectors.
  3. [Stuss 2011, Neuropsychologia 49(11):2966-2972, PMID 21477662] —
     Functions of the frontal lobes: relation to executive functions.
     Supervisory attentional system; basis for stale_plan detection
     as the absence of supervision.
  4. [Koechlin 2007, Trends Cogn Sci 11(6):229-235, PMID 17499539] —
     An information theoretical approach to prefrontal executive
     function. Hierarchical cascade of PFC regions across time-scales
     (immediate / contextual / temporal / branching) — the horizon
     classification used by the planning skill.
  5. [Badre 2008, Trends Cogn Sci 12(5):193-200, PMID 18514167] —
     Cognitive control, hierarchy, and the rostro-caudal organization
     of the frontal lobes. Foundation for revision as
     back-up-and-redescend when a step doesn't pan out.
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
    "wire": 39,
    "signal": "task_planning",
    "mechanism": "TaskPlanningLayer",
    "reads": [
        "pirp_context.planning_op",
    ],
    "writes": [
        "planning_state",
        "integrity_score",
        "operation_distribution",
        "horizon_distribution",
        "mode_distribution",
        "failure_mode_counts",
        "active_plan_count",
    ],
    "citations": [
        "PMID 11283309",
        "PMID 25251493",
        "PMID 21477662",
        "PMID 17499539",
        "PMID 18514167",
    ],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

VALID_OPS = {"decompose", "commit", "revise", "complete", "reflect"}
VALID_HORIZONS = {"immediate", "contextual", "temporal", "branching"}
VALID_MODES = {"brain", "coach", "build", "default"}

# Over-decomposition: more than this many subtasks for a single goal.
MAX_SUBTASKS_PER_GOAL = 12

# Under-decomposition: multi-part goal with this few subtasks.
MIN_SUBTASKS_FOR_MULTI_PART = 2

# Plan storm: more than N decomposes in W ticks without an intervening commit.
PLAN_STORM_DECOMPOSE_LIMIT = 3
PLAN_STORM_WINDOW_TICKS = 50

# Stale plan: active plan untouched (no revise / no subtask transition / no
# commit on a different plan) for this many ticks.
STALE_PLAN_TICK_THRESHOLD = 800

# Reflection deadline: ticks after `complete` without a `reflect` op.
REFLECTION_DEADLINE_TICKS = 200

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


class TaskPlanningLayer(BrainMechanism):
    """The agent's planning monitor. See module docstring."""

    def __init__(self, history_size: int = 200):
        try:
            super().__init__(
                name="TaskPlanningLayer",
                human_analog="dlPFC + frontal-pole planning monitor",
                layer="integration",
            )
        except Exception:
            pass

        self.history_size = history_size

        self.operations: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.current_tick: int = 0

        # Active plans: plan_id -> {goal_hash, last_touched_tick, committed_tick}
        self.active_plans: Dict[str, Dict[str, Any]] = {}
        # Plans pending reflection: plan_id -> completed_tick
        self.pending_reflections: Dict[str, int] = {}
        # Decompose cadence (for plan-storm detection).
        self.decompose_ticks: Deque[int] = deque(maxlen=PLAN_STORM_DECOMPOSE_LIMIT * 4)
        # Track decomposes that haven't been followed by a commit yet.
        self.uncommitted_decomposes: Deque[str] = deque(maxlen=PLAN_STORM_DECOMPOSE_LIMIT * 4)

        # Per-op counters.
        self.op_counts: Dict[str, int] = {k: 0 for k in VALID_OPS}
        # Horizon distribution (across decomposed plans).
        self.horizon_counts: Dict[str, int] = {k: 0 for k in VALID_HORIZONS}
        # Mode distribution at decompose time.
        self.mode_counts: Dict[str, int] = {k: 0 for k in VALID_MODES}
        # Failure-mode counters.
        self.failure_counts: Dict[str, int] = {
            "over_decomposition": 0,
            "under_decomposition": 0,
            "stale_plan": 0,
            "plan_storm": 0,
            "incomplete_plans": 0,
            "missing_reflection": 0,
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

        ap = self.state.get("active_plans")
        if isinstance(ap, dict):
            self.active_plans = {
                str(k): dict(v) for k, v in ap.items() if isinstance(v, dict)
            }

        pr = self.state.get("pending_reflections")
        if isinstance(pr, dict):
            self.pending_reflections = {
                str(k): int(v) for k, v in pr.items()
            }

        dt = self.state.get("decompose_ticks")
        if isinstance(dt, list):
            for v in dt[-(PLAN_STORM_DECOMPOSE_LIMIT * 4):]:
                try:
                    self.decompose_ticks.append(int(v))
                except (TypeError, ValueError):
                    continue

        ud = self.state.get("uncommitted_decomposes")
        if isinstance(ud, list):
            for s in ud[-(PLAN_STORM_DECOMPOSE_LIMIT * 4):]:
                if isinstance(s, str):
                    self.uncommitted_decomposes.append(s)

        oc = self.state.get("op_counts")
        if isinstance(oc, dict):
            for k in VALID_OPS:
                self.op_counts[k] = int(oc.get(k, 0) or 0)

        hc = self.state.get("horizon_counts")
        if isinstance(hc, dict):
            for k in VALID_HORIZONS:
                self.horizon_counts[k] = int(hc.get(k, 0) or 0)

        mc = self.state.get("mode_counts")
        if isinstance(mc, dict):
            for k in VALID_MODES:
                self.mode_counts[k] = int(mc.get(k, 0) or 0)

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
        self.state["active_plans"] = dict(self.active_plans)
        self.state["pending_reflections"] = dict(self.pending_reflections)
        self.state["decompose_ticks"] = list(self.decompose_ticks)
        self.state["uncommitted_decomposes"] = list(self.uncommitted_decomposes)
        self.state["op_counts"] = dict(self.op_counts)
        self.state["horizon_counts"] = dict(self.horizon_counts)
        self.state["mode_counts"] = dict(self.mode_counts)
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
        if op == "decompose":
            if self._plan_storm_active():
                return True, (
                    f"plan storm — ≥{PLAN_STORM_DECOMPOSE_LIMIT} decomposes in "
                    f"last {PLAN_STORM_WINDOW_TICKS} ticks without commit"
                )
        if op == "revise":
            kind = kwargs.get("kind")
            if kind == "abandon" and not kwargs.get("reason"):
                return True, "abandon revision requires a reason"
        if self.is_systematically_low_integrity():
            return True, (
                f"sustained low planning integrity (rolling score "
                f"{self.rolling_integrity_score():.3f} < "
                f"{LOW_INTEGRITY_THRESHOLD})"
            )
        return False, ""

    # ── Per-op recorders ───────────────────────────────────────────────────

    def record_op(self, op: str, **kwargs: Any) -> Dict[str, Any]:
        if op == "decompose":
            return self.record_decompose(**kwargs)
        if op == "commit":
            return self.record_commit(**kwargs)
        if op == "revise":
            return self.record_revise(**kwargs)
        if op == "complete":
            return self.record_complete(**kwargs)
        if op == "reflect":
            return self.record_reflect(**kwargs)
        return self._record_invalid(op, kwargs)

    def record_decompose(
        self,
        plan_id: str = "",
        goal: str = "",
        subtask_count: int = 0,
        horizon: str = "contextual",
        mode: str = "default",
        multi_part_goal: bool = False,
        cycle_detected: bool = False,
    ) -> Dict[str, Any]:
        """Record a decompose op."""
        h = horizon if horizon in VALID_HORIZONS else "contextual"
        m = mode if mode in VALID_MODES else "default"

        over = subtask_count > MAX_SUBTASKS_PER_GOAL
        under = bool(multi_part_goal) and subtask_count < MIN_SUBTASKS_FOR_MULTI_PART
        if over:
            self.failure_counts["over_decomposition"] += 1
        if under:
            self.failure_counts["under_decomposition"] += 1

        # Plan-storm tracking: only count toward storm if there hasn't been a
        # commit since the last decompose cluster.
        self.decompose_ticks.append(self.current_tick)
        if plan_id:
            self.uncommitted_decomposes.append(plan_id)
        storming = self._plan_storm_active()
        if storming:
            self.failure_counts["plan_storm"] += 1

        # Update distributions.
        self.horizon_counts[h] = self.horizon_counts.get(h, 0) + 1
        self.mode_counts[m] = self.mode_counts.get(m, 0) + 1

        bad = sum([over, under, cycle_detected, storming])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "decompose",
            "plan_id": plan_id,
            "goal_hash": _hash_text(goal),
            "subtask_count": int(subtask_count),
            "horizon": h,
            "mode": m,
            "multi_part_goal": bool(multi_part_goal),
            "over_decomposition": over,
            "under_decomposition": under,
            "cycle_detected": bool(cycle_detected),
            "plan_storm_active": storming,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_commit(
        self,
        plan_id: str = "",
        goal: str = "",
        track: str = "main",
        superseded: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a commit op."""
        # Drain this plan from uncommitted_decomposes.
        try:
            tmp = list(self.uncommitted_decomposes)
            tmp = [pid for pid in tmp if pid != plan_id]
            self.uncommitted_decomposes = deque(
                tmp, maxlen=PLAN_STORM_DECOMPOSE_LIMIT * 4,
            )
        except Exception:
            pass

        # Mark previously active plan on track as superseded if any.
        if superseded and superseded in self.active_plans:
            # Was active; now becomes incomplete because superseded without
            # complete is the incomplete_plans signal — UNLESS the operator
            # explicitly handles supersession with a reason. We count it.
            self.failure_counts["incomplete_plans"] += 1
            self.active_plans.pop(superseded, None)

        self.active_plans[plan_id] = {
            "goal_hash": _hash_text(goal),
            "track": track,
            "committed_tick": self.current_tick,
            "last_touched_tick": self.current_tick,
        }

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "commit",
            "plan_id": plan_id,
            "track": track,
            "superseded": superseded,
            "op_score": 1.0,
            "ts": time.time(),
        }
        self._finalize(record, 1.0)
        return record

    def record_revise(
        self,
        plan_id: str = "",
        kind: str = "modify",
        reason: str = "",
    ) -> Dict[str, Any]:
        """Record a revise op."""
        kind_ok = kind in {"insert", "modify", "abandon"}
        reason_required = (kind == "abandon")
        reason_ok = (not reason_required) or bool(reason.strip())

        # Touch the plan.
        if plan_id in self.active_plans:
            self.active_plans[plan_id]["last_touched_tick"] = self.current_tick
            if kind == "abandon":
                # Abandon transitions plan out of active without complete.
                # That's a deliberate revise-kind, not the incomplete_plans
                # failure mode — incomplete_plans is for unannounced drops.
                self.active_plans.pop(plan_id, None)

        bad = sum([not kind_ok, not reason_ok])
        op_score = max(0.0, 1.0 - 0.30 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "revise",
            "plan_id": plan_id,
            "kind": kind,
            "kind_ok": kind_ok,
            "reason_present": bool(reason),
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_complete(
        self,
        plan_id: str = "",
        elapsed_sec: float = 0.0,
        subtask_count: int = 0,
        unresolved_count: int = 0,
    ) -> Dict[str, Any]:
        """Record a complete op."""
        accepted = unresolved_count == 0
        if accepted:
            # Remove from active, add to pending reflections.
            if plan_id in self.active_plans:
                self.active_plans.pop(plan_id, None)
            self.pending_reflections[plan_id] = self.current_tick

        bad = sum([not accepted])
        op_score = max(0.0, 1.0 - 0.30 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "complete",
            "plan_id": plan_id,
            "elapsed_sec": float(elapsed_sec),
            "subtask_count": int(subtask_count),
            "unresolved_count": int(unresolved_count),
            "accepted": accepted,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_reflect(
        self,
        plan_id: str = "",
        what_worked_count: int = 0,
        what_didnt_count: int = 0,
        has_what_id_do_differently: bool = False,
    ) -> Dict[str, Any]:
        """Record a reflect op."""
        plan_known = plan_id in self.pending_reflections
        # Reflection counts as substantive if at least one of the lenses
        # has content.
        substantive = bool(
            what_worked_count or what_didnt_count or has_what_id_do_differently
        )
        if plan_known and substantive:
            self.pending_reflections.pop(plan_id, None)

        bad = sum([not plan_known, not substantive])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "reflect",
            "plan_id": plan_id,
            "plan_known": plan_known,
            "substantive": substantive,
            "what_worked_count": int(what_worked_count),
            "what_didnt_count": int(what_didnt_count),
            "has_what_id_do_differently": bool(has_what_id_do_differently),
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

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

    def _plan_storm_active(self) -> bool:
        if not self.decompose_ticks:
            return False
        cut = self.current_tick - PLAN_STORM_WINDOW_TICKS
        recent = [t for t in self.decompose_ticks if t >= cut]
        # Storm = many recent decomposes AND many uncommitted ones.
        return (
            len(recent) >= PLAN_STORM_DECOMPOSE_LIMIT
            and len(self.uncommitted_decomposes) >= PLAN_STORM_DECOMPOSE_LIMIT
        )

    def check_stale_plans(self) -> List[str]:
        """Return active plan_ids that are past STALE_PLAN_TICK_THRESHOLD
        without being touched. Increments stale_plan counter for any newly-
        stale plans."""
        out: List[str] = []
        for plan_id, info in list(self.active_plans.items()):
            last = int(info.get("last_touched_tick", 0))
            age = self.current_tick - last
            if age > STALE_PLAN_TICK_THRESHOLD:
                key = f"stale_recorded_{plan_id}"
                if not self.state.get(key):
                    self.failure_counts["stale_plan"] += 1
                    self.state[key] = True
                out.append(plan_id)
        return out

    def check_unreflected_completions(self) -> List[str]:
        """Return plan_ids whose completion is past the reflection deadline."""
        out: List[str] = []
        for plan_id, completed_tick in list(self.pending_reflections.items()):
            age = self.current_tick - int(completed_tick)
            if age > REFLECTION_DEADLINE_TICKS:
                out.append(plan_id)
                key = f"missing_reflection_{plan_id}"
                if not self.state.get(key):
                    self.failure_counts["missing_reflection"] += 1
                    self.state[key] = True
        return out

    # ── Pattern detection / state ──────────────────────────────────────────

    def rolling_integrity_score(self) -> float:
        if not self.integrity_window:
            return 1.0
        return sum(self.integrity_window) / len(self.integrity_window)

    def is_systematically_low_integrity(self) -> bool:
        if len(self.integrity_window) < INTEGRITY_MIN_N:
            return False
        return self.rolling_integrity_score() < LOW_INTEGRITY_THRESHOLD

    def planning_state(self) -> str:
        """Single-word state for TSB. Priority:
        degrading > storming > paralyzed > stale > revising > active > idle."""
        if self.is_systematically_low_integrity():
            return "degrading"
        if self._plan_storm_active():
            return "storming"
        if self.check_unreflected_completions():
            return "paralyzed"  # finished but not learning
        if self.check_stale_plans():
            return "stale"
        if self.operations:
            recent = self.operations[-1]
            if recent.get("op") == "revise" and recent.get("op_score", 0) >= 0.5:
                return "revising"
            if time.time() - float(recent.get("ts", 0.0)) <= 60:
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

        # Run stale + unreflected sweeps each tick.
        self.check_stale_plans()
        self.check_unreflected_completions()

        op_payload = pirp_context.get("planning_op")
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
        total_horizons = sum(self.horizon_counts.values()) or 1
        horizon_dist = {
            k: round(v / total_horizons, 4)
            for k, v in self.horizon_counts.items()
        }
        total_modes = sum(self.mode_counts.values()) or 1
        mode_dist = {
            k: round(v / total_modes, 4)
            for k, v in self.mode_counts.items()
        }
        return {
            "planning_state": self.planning_state(),
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "integrity_window_n": len(self.integrity_window),
            "is_systematically_low_integrity": self.is_systematically_low_integrity(),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "operation_distribution": dict(self.op_counts),
            "horizon_distribution": horizon_dist,
            "mode_distribution": mode_dist,
            "failure_mode_counts": dict(self.failure_counts),
            "active_plan_count": len(self.active_plans),
            "pending_reflection_count": len(self.pending_reflections),
            "uncommitted_decompose_count": len(self.uncommitted_decomposes),
            "plan_storm_active": self._plan_storm_active(),
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
            "source": "TaskPlanningLayer",
            "kind": "task_planning_drift",
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "dominant_failure_mode": dominant_mode,
            "dominant_failure_count": dominant_count,
            "failure_mode_counts": dict(self.failure_counts),
            "active_plan_count": len(self.active_plans),
            "pending_reflection_count": len(self.pending_reflections),
            "interpretation": self._interpret_drift(dominant_mode),
        }

    def _interpret_drift(self, dominant: str) -> str:
        if dominant == "over_decomposition":
            return (
                "Goals are being broken into too many subtasks. The agent "
                "is plan-paralyzing — working memory overflows; nothing "
                "starts."
            )
        if dominant == "under_decomposition":
            return (
                "Multi-part goals are being treated as single steps. The "
                "decomposition is a fig leaf; the work hasn't actually "
                "been planned."
            )
        if dominant == "stale_plan":
            return (
                "Active plans are sitting untouched. The agent commits to "
                "plans then drifts away from them without revising or "
                "abandoning explicitly."
            )
        if dominant == "plan_storm":
            return (
                "The agent keeps starting over — many decomposes without "
                "intervening commits. Indecision at the planning layer."
            )
        if dominant == "incomplete_plans":
            return (
                "Active plans get superseded without being completed or "
                "explicitly abandoned. Drift between intent and execution."
            )
        if dominant == "missing_reflection":
            return (
                "Completed plans aren't getting retrospectives within the "
                "deadline. The learning loop isn't closing."
            )
        return "Planning has drifted but no single failure mode dominates."

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
        # Also clear per-plan recorded markers.
        for key in list(self.state.keys()):
            if key.startswith("stale_recorded_") or key.startswith("missing_reflection_"):
                self.state.pop(key, None)
        self._flush_working_state()
        self.persist_state()

    def reset_distributions(self) -> None:
        for k in VALID_HORIZONS:
            self.horizon_counts[k] = 0
        for k in VALID_MODES:
            self.mode_counts[k] = 0
        self._flush_working_state()
        self.persist_state()

    def force_drop_active_plan(self, plan_id: str, reason: str) -> bool:
        """Operator hook to clear an active plan that's gone stale or
        otherwise needs to be removed without going through revise(abandon).
        Increments incomplete_plans counter — that's the cost."""
        if plan_id not in self.active_plans:
            return False
        self.active_plans.pop(plan_id, None)
        self.failure_counts["incomplete_plans"] += 1
        self._flush_working_state()
        self.persist_state()
        return True
