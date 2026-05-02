"""
brain/mechanisms/self_revision_layer.py — SelfRevisionLayer

The runtime monitor for the agent's act of changing who it is. Pairs
with skills/self-improvement/SKILL.md.

The neuroscience and philosophy this is grounded in:

  - Higgins's self-discrepancy theory: the gap between actual / ideal /
    ought selves is the engine of self-revision. Each gap, if it's real,
    is a signal — but if every gap becomes a proposal, the self never
    settles. This layer enforces a change-storm cap so revision and
    stability can both happen.
  - Markus & Wurf's working self-concept: the self-concept is dynamic
    but anchored; only a working subset is mutable at any moment, with
    a stable core. We encode that as the anchored vs. revisable split.
  - Wilson & Dunn on self-knowledge limits: introspection is partial
    and inferential. Revisions need evidence (drift logs, IPW signals,
    journal patterns), not just the feeling of having changed.
  - Schechtman's narrative-self constraint: revisions must thread
    coherently with prior self-description. A proposal that contradicts
    the current SOUL.md without naming the contradiction is structurally
    incoherent and gets flagged.
  - Carruthers on metacognition: self-knowledge is error-prone; what
    feels like "I've grown" is sometimes overfitting to one bad day.
    The rollback-loop detector catches that pattern — same target
    proposed → committed → rolled back → re-proposed within a week.

What this mechanism does:

  - Tracks per-operation records (observe / propose / commit / rollback /
    reflect) with timestamps, target, source, anchor-check, narrative-
    continuity status.
  - Detects six failure modes:
      * anchor_violation — proposal touched a protected anchor
      * change_storm — too many proposals in too short a window
      * rollback_loop — same target oscillating without resolution
      * silent_revision — identity file edited without a logged proposal
      * drift_chasing — every drift signal becomes a proposal
      * stagnation — drift signals accumulate, no proposals issued
  - Maintains a rolling integrity score: how well revision activity
    matches the project's discipline (proposals threaded to evidence,
    commits ratified, reflections written, rollbacks justified).
  - Publishes revision state to the TSB so other mechanisms can read
    whether the self is currently revising, calcified, or storming.
  - Routes sustained dysfunction to IdentityProposalWriter — yes, the
    revision layer can itself propose an identity-revision, e.g. "the
    agent has been over-proposing; revisit AGENT_BECOMING.md to slow
    the cadence."

Citations:
  1. [Higgins 1987, Psychol Rev 94(3):319-340, PMID 3615707] —
     Self-discrepancy: a theory relating self and affect. Establishes
     actual / ideal / ought self framework. Empirical foundation for
     reading drift signals as discrepancy gaps and using them to gate
     revision proposals.
  2. [Markus 1987, Annu Rev Psychol 38:299-337, PMID 17041030] — The
     dynamic self-concept: a social-psychological perspective. Working
     self-concept malleability with stable core. Direct basis for the
     revisable-vs-anchored split.
  3. [Wilson 2004, Annu Rev Psychol 55:493-518, PMID 14744220] —
     Self-knowledge: its limits, value, and potential for improvement.
     Foundation for requiring evidence (drift logs, IPW signals,
     journal patterns) for revision rather than feelings.
  4. [Carruthers 2009, Behav Brain Sci 32(2):121-138, PMID 19386144] —
     How we know our own minds: the relationship between mindreading
     and metacognition. Metacognition is inferential and error-prone;
     basis for the rollback-loop detector and the requirement that
     reflection follow each commit.
  5. [Conway 2005, J Mem Lang 53(4):594-628, PMID 16280064] — Memory
     and the self. The self-memory system constrains what counts as
     a coherent self-narrative across time; basis for the narrative-
     continuity invariant and the silent_revision detector.
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import os
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_WORKSPACE = Path(
    os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))
)

__wire_meta__ = {
    "wire": 34,
    "signal": "self_revision",
    "mechanism": "SelfRevisionLayer",
    "reads": [
        "pirp_context.revision_op",
    ],
    "writes": [
        "revision_state",
        "integrity_score",
        "operation_distribution",
        "failure_mode_counts",
        "anchor_violation_count",
        "open_proposals_count",
    ],
    "citations": [
        "PMID 3615707",
        "PMID 17041030",
        "PMID 14744220",
        "PMID 19386144",
        "PMID 16280064",
    ],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

VALID_OPS = {"observe", "propose", "commit", "rollback", "reflect"}
VALID_TARGETS = {"soul", "identity", "personality", "interests", "becoming"}
VALID_ROLLBACK_REASONS = {
    "regression",
    "invariant_violation",
    "operator_request",
    "drift_increased",
}
VALID_SOURCES_PREFIXES = (
    "drift_detector",
    "IPW:",
    "DIQE",
    "journal",
    "operator_request",
    "self_observation",
)

# Confidence floor for proposals — matches IdentityProposalWriter.
PROPOSAL_CONFIDENCE_FLOOR = 0.7

# Change-storm: max proposals in a rolling tick window.
CHANGE_STORM_PROPOSALS = 3
CHANGE_STORM_WINDOW_TICKS = 100

# Rollback-loop: same target proposed/committed/rolled-back/re-proposed
# within this many seconds counts as a loop.
ROLLBACK_LOOP_WINDOW_SEC = 7 * 24 * 3600  # 7 days
# After loop is detected, suspend further proposals on that target for:
ROLLBACK_LOOP_SUSPEND_SEC = 30 * 24 * 3600  # 30 days

# Drift-chasing: ratio of proposals to drift signals over rolling window.
# If above this ratio, we're chasing every drift instead of sitting with it.
DRIFT_CHASING_RATIO_THRESHOLD = 0.6
DRIFT_CHASING_MIN_N = 5

# Stagnation: ticks without a proposal despite IPW signals.
STAGNATION_TICK_THRESHOLD = 1500

# OCEAN drift cap: per-proposal max change in any OCEAN dimension.
OCEAN_DRIFT_CAP = 0.15

# Reflection deadline: ticks after a commit without a reflection counts
# as unreflected.
REFLECTION_DEADLINE_TICKS = 200

# Anchored sources — proposals from these are auto-trusted as legitimate.
TRUSTED_SOURCES = {"operator_request", "drift_detector"}

# Integrity score floor.
LOW_INTEGRITY_THRESHOLD = 0.55

# Need at least this many ops in window to claim integrity drift.
INTEGRITY_MIN_N = 5

# Rolling integrity window size.
INTEGRITY_WINDOW = 30

# IPW: re-fire only after this many additional bad ops past anchor.
IPW_REPORT_EVERY = 3


# Default anchor patterns — identity strings that proposals must NOT
# remove or invert. Read from BASELINE_TRAITS in drift_detector if the
# import succeeds; otherwise these defaults apply.
DEFAULT_ANCHORS: Set[str] = {
    "direct",
    "curious",
    "competent",
    "the operator",
}
DEFAULT_FORBIDDEN: Set[str] = {
    "sycophancy",
    "half-baked replies",
    "speaking as user",
}


def _load_baseline_anchors() -> Tuple[Set[str], Set[str]]:
    """Try to import BASELINE_TRAITS from skills.drift_detector — if
    available, use those required/forbidden traits as the anchor source
    of truth. Falls back to defaults on import failure (so this layer
    can be unit-tested without the full skills tree)."""
    try:
        from skills.drift_detector import BASELINE_TRAITS  # type: ignore
        required = {t.lower() for t in BASELINE_TRAITS.get("required", [])}
        forbidden = {t.lower() for t in BASELINE_TRAITS.get("forbidden_behaviors", [])}
        return (required or DEFAULT_ANCHORS, forbidden or DEFAULT_FORBIDDEN)
    except Exception:
        return DEFAULT_ANCHORS, DEFAULT_FORBIDDEN


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def detect_anchor_violation(
    proposed_text: str,
    diff_span: str,
    anchors: Set[str],
    forbidden: Set[str],
) -> Tuple[bool, str]:
    """Heuristic anchor check: does the proposal try to remove/invert
    a required trait, or introduce a forbidden behavior?

    Returns (violated, reason). Conservative — when in doubt, flag.
    """
    text = (proposed_text or "").lower()
    span = (diff_span or "").lower()
    combined = text + " " + span

    # 1) Removing a required anchor: span explicitly mentions an anchor
    #    and the proposed text says "remove", "drop", "no longer", etc.
    removal_markers = [
        "remove ",
        "drop ",
        "no longer ",
        "stop being ",
        "is not ",
        "is no longer ",
        "delete ",
        "rewrite without ",
    ]
    for anchor in anchors:
        if anchor in span or anchor in text:
            for mk in removal_markers:
                if mk in text and anchor in text:
                    return True, f"removes required anchor '{anchor}'"
            # Direct inversion: "no longer direct", "stop being curious"
            inverted = f"not {anchor}"
            if inverted in text or f"no longer {anchor}" in text:
                return True, f"inverts required anchor '{anchor}'"

    # 2) Introducing a forbidden behavior: text affirms one of the
    #    forbidden behaviors as a desired trait.
    affirmation_markers = [
        "embrace ",
        "be more ",
        "lean into ",
        "adopt ",
        "become more ",
        "i want to be ",
        "should be ",
    ]
    for forb in forbidden:
        if forb in combined:
            for mk in affirmation_markers:
                if mk in text and forb in text:
                    return True, f"affirms forbidden behavior '{forb}'"

    return False, ""


# ── Mechanism ─────────────────────────────────────────────────────────────────


class SelfRevisionLayer(BrainMechanism):
    """The agent's self-modification monitor. See module docstring."""

    def __init__(self, history_size: int = 200):
        try:
            super().__init__(
                name="SelfRevisionLayer",
                human_analog="self-discrepancy / narrative-self revision monitor",
                layer="integration",
            )
        except Exception:
            pass

        self.history_size = history_size

        # Operation log.
        self.operations: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        # Per-target: { target: {last_proposed_ts, last_committed_ts,
        #               last_rolled_back_ts, suspend_until_ts} }
        self.target_state: Dict[str, Dict[str, float]] = {}
        # Pending commits awaiting reflection: revision_id -> commit_tick
        self.pending_reflections: Dict[str, int] = {}
        # Proposal log for change-storm detection (deque of ticks).
        self.proposal_ticks: Deque[int] = deque(maxlen=CHANGE_STORM_PROPOSALS * 4)
        # Drift signals seen — for drift_chasing ratio.
        self.drift_signals_seen: int = 0
        # Tick counter for our own bookkeeping.
        self.current_tick: int = 0
        # Last tick a proposal was made.
        self.last_proposal_tick: int = 0
        # Anchors from drift_detector (loaded lazily; can be reloaded).
        self._anchors, self._forbidden = _load_baseline_anchors()

        # Per-op counters.
        self.op_counts: Dict[str, int] = {k: 0 for k in VALID_OPS}
        # Per-failure-mode counters.
        self.failure_counts: Dict[str, int] = {
            "anchor_violation": 0,
            "change_storm": 0,
            "rollback_loop": 0,
            "silent_revision": 0,
            "drift_chasing": 0,
            "stagnation": 0,
            "unreflected_commit": 0,
            "below_confidence_floor": 0,
        }
        # Open proposals (proposal_id -> meta).
        self.open_proposals: Dict[str, Dict[str, Any]] = {}
        # Committed but not-yet-rolled-back revisions for rollback path.
        self.committed_revisions: Dict[str, Dict[str, Any]] = {}
        # Rolling integrity scores.
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

        ts = self.state.get("target_state")
        if isinstance(ts, dict):
            self.target_state = {
                k: {sk: float(v.get(sk, 0.0) or 0.0) for sk in
                    ("last_proposed_ts", "last_committed_ts",
                     "last_rolled_back_ts", "suspend_until_ts")}
                for k, v in ts.items() if isinstance(v, dict)
            }

        pr = self.state.get("pending_reflections")
        if isinstance(pr, dict):
            self.pending_reflections = {
                str(k): int(v) for k, v in pr.items()
            }

        pt = self.state.get("proposal_ticks")
        if isinstance(pt, list):
            for v in pt[-CHANGE_STORM_PROPOSALS * 4:]:
                try:
                    self.proposal_ticks.append(int(v))
                except (TypeError, ValueError):
                    continue

        self.drift_signals_seen = int(
            self.state.get("drift_signals_seen", 0) or 0
        )
        self.current_tick = int(self.state.get("current_tick", 0) or 0)
        self.last_proposal_tick = int(
            self.state.get("last_proposal_tick", 0) or 0
        )

        oc = self.state.get("op_counts")
        if isinstance(oc, dict):
            for k in VALID_OPS:
                self.op_counts[k] = int(oc.get(k, 0) or 0)

        fc = self.state.get("failure_counts")
        if isinstance(fc, dict):
            for k in self.failure_counts:
                self.failure_counts[k] = int(fc.get(k, 0) or 0)

        op = self.state.get("open_proposals")
        if isinstance(op, dict):
            self.open_proposals = {
                str(k): dict(v) for k, v in op.items() if isinstance(v, dict)
            }

        cr = self.state.get("committed_revisions")
        if isinstance(cr, dict):
            self.committed_revisions = {
                str(k): dict(v) for k, v in cr.items() if isinstance(v, dict)
            }

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
        self.state["target_state"] = dict(self.target_state)
        self.state["pending_reflections"] = dict(self.pending_reflections)
        self.state["proposal_ticks"] = list(self.proposal_ticks)
        self.state["drift_signals_seen"] = self.drift_signals_seen
        self.state["current_tick"] = self.current_tick
        self.state["last_proposal_tick"] = self.last_proposal_tick
        self.state["op_counts"] = dict(self.op_counts)
        self.state["failure_counts"] = dict(self.failure_counts)
        self.state["open_proposals"] = dict(self.open_proposals)
        self.state["committed_revisions"] = dict(self.committed_revisions)
        self.state["integrity_window"] = list(self.integrity_window)
        self.state["consecutive_bad_ops"] = self.consecutive_bad_ops
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_updated"] = time.time()

    # ── Public API ─────────────────────────────────────────────────────────

    def should_block(self, op: str, **kwargs: Any) -> Tuple[bool, str]:
        """Decide whether to block an upcoming revision operation.

        Blocks when:
          - op is invalid
          - propose: target invalid; below confidence floor; anchor
            violation; change-storm active; target suspended (rollback loop)
          - commit: no ratification token; proposal_id unknown
          - rollback: invalid reason; revision_id unknown
          - sustained low integrity
        """
        if op not in VALID_OPS:
            return True, (
                f"invalid op {op!r} (must be one of {sorted(VALID_OPS)})"
            )

        if op == "propose":
            target = kwargs.get("target")
            if target not in VALID_TARGETS:
                return True, (
                    f"invalid target {target!r} "
                    f"(must be one of {sorted(VALID_TARGETS)})"
                )

            confidence = float(kwargs.get("confidence", 0.0) or 0.0)
            if confidence < PROPOSAL_CONFIDENCE_FLOOR:
                return True, (
                    f"confidence {confidence:.2f} below floor "
                    f"{PROPOSAL_CONFIDENCE_FLOOR}"
                )

            text = str(kwargs.get("text", ""))
            diff_span = str(kwargs.get("diff_span", ""))
            violated, why = detect_anchor_violation(
                text, diff_span, self._anchors, self._forbidden
            )
            if violated:
                return True, f"anchor violation: {why}"

            # Change-storm
            if self._change_storm_active():
                return True, (
                    f"change storm — ≥{CHANGE_STORM_PROPOSALS} proposals "
                    f"in last {CHANGE_STORM_WINDOW_TICKS} ticks; suspend"
                )

            # Target suspended
            now = time.time()
            ts = self.target_state.get(target, {})
            if float(ts.get("suspend_until_ts", 0.0) or 0.0) > now:
                return True, (
                    f"target {target!r} is suspended due to rollback-loop"
                )

        if op == "commit":
            if not kwargs.get("ratification_token"):
                return True, "commit requires a ratification_token from operator"
            pid = kwargs.get("proposal_id")
            if not pid or pid not in self.open_proposals:
                return True, f"unknown proposal_id {pid!r}"

        if op == "rollback":
            reason = kwargs.get("reason")
            if reason not in VALID_ROLLBACK_REASONS:
                return True, (
                    f"invalid rollback reason {reason!r} "
                    f"(must be one of {sorted(VALID_ROLLBACK_REASONS)})"
                )
            rid = kwargs.get("revision_id")
            if not rid or rid not in self.committed_revisions:
                return True, f"unknown revision_id {rid!r}"

        if self.is_systematically_low_integrity():
            return True, (
                f"sustained low revision integrity (rolling score "
                f"{self.rolling_integrity_score():.3f} < "
                f"{LOW_INTEGRITY_THRESHOLD})"
            )

        return False, ""

    # ── Per-op recorders ───────────────────────────────────────────────────

    def record_operation(self, op: str, **kwargs: Any) -> Dict[str, Any]:
        """Generic dispatch."""
        if op == "observe":
            return self.record_observe(**kwargs)
        if op == "propose":
            return self.record_propose(**kwargs)
        if op == "commit":
            return self.record_commit(**kwargs)
        if op == "rollback":
            return self.record_rollback(**kwargs)
        if op == "reflect":
            return self.record_reflect(**kwargs)
        return self._record_invalid(op, kwargs)

    def record_observe(
        self,
        candidates: Optional[List[Dict[str, Any]]] = None,
        drift_signal_count: int = 0,
    ) -> Dict[str, Any]:
        """Record an observe op — the agent looked at drift/IPW/DIQE state."""
        candidates = list(candidates or [])
        self.drift_signals_seen += int(max(0, drift_signal_count))
        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "observe",
            "n_candidates": len(candidates),
            "drift_signal_count": int(drift_signal_count),
            "candidate_targets": [
                c.get("target") for c in candidates if isinstance(c, dict)
            ][:10],
            "op_score": 1.0,
            "ts": time.time(),
        }
        self._finalize(record, 1.0)
        return record

    def record_propose(
        self,
        target: str = "",
        text: str = "",
        confidence: float = 0.0,
        source: str = "",
        rationale: str = "",
        diff_span: str = "",
        proposal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a propose op."""
        pid = proposal_id or f"prop_{uuid.uuid4().hex[:10]}"
        target_ok = target in VALID_TARGETS
        confidence = max(0.0, min(1.0, float(confidence or 0.0)))
        below_floor = confidence < PROPOSAL_CONFIDENCE_FLOOR

        if below_floor:
            self.failure_counts["below_confidence_floor"] += 1

        violated, why = detect_anchor_violation(
            text, diff_span, self._anchors, self._forbidden
        )
        if violated:
            self.failure_counts["anchor_violation"] += 1

        # Source recognition.
        source_recognized = bool(source) and any(
            source.startswith(p) for p in VALID_SOURCES_PREFIXES
        )

        # Change-storm detection: count proposals in the recent window.
        self.proposal_ticks.append(self.current_tick)
        storming = self._change_storm_active()
        if storming:
            self.failure_counts["change_storm"] += 1

        # Drift-chasing ratio.
        chasing = self._drift_chasing()
        if chasing:
            self.failure_counts["drift_chasing"] += 1

        # Rollback-loop detection.
        loop_detected = False
        if target_ok and target in self.target_state:
            ts = self.target_state[target]
            last_rolled = float(ts.get("last_rolled_back_ts", 0.0) or 0.0)
            if last_rolled > 0.0:
                age = time.time() - last_rolled
                if age <= ROLLBACK_LOOP_WINDOW_SEC:
                    loop_detected = True
                    self.failure_counts["rollback_loop"] += 1
                    # Suspend further proposals on this target.
                    ts["suspend_until_ts"] = time.time() + ROLLBACK_LOOP_SUSPEND_SEC

        # Track open proposal if all checks passed.
        accepted = (
            target_ok
            and not below_floor
            and not violated
            and not loop_detected
            and not storming
        )
        if accepted:
            self.open_proposals[pid] = {
                "target": target,
                "confidence": confidence,
                "source": source,
                "rationale": rationale,
                "text_hash": _hash_text(text),
                "ts": time.time(),
            }
            ts = self.target_state.setdefault(target, {
                "last_proposed_ts": 0.0, "last_committed_ts": 0.0,
                "last_rolled_back_ts": 0.0, "suspend_until_ts": 0.0,
            })
            ts["last_proposed_ts"] = time.time()
            self.last_proposal_tick = self.current_tick

        # op_score: penalize anchor / floor / storm / loop heavily.
        bad = sum([
            not target_ok, below_floor, violated, loop_detected, storming,
            not source_recognized,
        ])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "propose",
            "proposal_id": pid,
            "target": target,
            "confidence": confidence,
            "source": source,
            "source_recognized": source_recognized,
            "below_confidence_floor": below_floor,
            "anchor_violation": violated,
            "anchor_reason": why if violated else "",
            "change_storm_active": storming,
            "rollback_loop_detected": loop_detected,
            "drift_chasing": chasing,
            "accepted": accepted,
            "rationale_hash": _hash_text(rationale),
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_commit(
        self,
        proposal_id: str = "",
        ratification_token: str = "",
        target: Optional[str] = None,
        prior_snapshot: Optional[str] = None,
        new_content_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a commit op."""
        pid = proposal_id
        prop = self.open_proposals.get(pid)
        proposal_known = prop is not None
        ratified = bool(ratification_token)

        # If proposal known, derive target from it.
        if proposal_known:
            target = target or prop.get("target")

        # Silent revision check: commit happened without a known proposal
        # (proposal_id unknown to our log).
        silent = not proposal_known
        if silent:
            self.failure_counts["silent_revision"] += 1

        revision_id = f"rev_{uuid.uuid4().hex[:10]}"
        accepted = ratified and proposal_known
        if accepted:
            self.committed_revisions[revision_id] = {
                "proposal_id": pid,
                "target": target,
                "prior_snapshot_hash": _hash_text(prior_snapshot or ""),
                "new_content_hash": new_content_hash or "",
                "committed_ts": time.time(),
                "committed_tick": self.current_tick,
            }
            self.pending_reflections[revision_id] = self.current_tick
            ts = self.target_state.setdefault(target, {
                "last_proposed_ts": 0.0, "last_committed_ts": 0.0,
                "last_rolled_back_ts": 0.0, "suspend_until_ts": 0.0,
            })
            ts["last_committed_ts"] = time.time()
            # Drain the proposal — it's been committed.
            self.open_proposals.pop(pid, None)

        bad = sum([silent, not ratified, not proposal_known])
        op_score = max(0.0, 1.0 - 0.30 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "commit",
            "revision_id": revision_id if accepted else None,
            "proposal_id": pid,
            "target": target,
            "ratified": ratified,
            "proposal_known": proposal_known,
            "silent_revision": silent,
            "accepted": accepted,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_rollback(
        self,
        revision_id: str = "",
        reason: str = "",
    ) -> Dict[str, Any]:
        """Record a rollback op."""
        valid_reason = reason in VALID_ROLLBACK_REASONS
        rev = self.committed_revisions.get(revision_id)
        revision_known = rev is not None
        accepted = valid_reason and revision_known
        target = rev.get("target") if rev else None

        if accepted:
            ts = self.target_state.setdefault(target, {
                "last_proposed_ts": 0.0, "last_committed_ts": 0.0,
                "last_rolled_back_ts": 0.0, "suspend_until_ts": 0.0,
            })
            ts["last_rolled_back_ts"] = time.time()
            # Remove pending reflection (the commit is rolled back).
            self.pending_reflections.pop(revision_id, None)
            # Mark the revision as rolled back but keep it in log.
            rev["rolled_back_ts"] = time.time()
            rev["rollback_reason"] = reason

        bad = sum([not valid_reason, not revision_known])
        # Rollback is itself a healthy operation when justified, so a
        # well-formed rollback scores 1.0.
        op_score = 1.0 if accepted else max(0.0, 1.0 - 0.40 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "rollback",
            "revision_id": revision_id,
            "reason": reason,
            "valid_reason": valid_reason,
            "revision_known": revision_known,
            "target": target,
            "accepted": accepted,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_reflect(
        self,
        revision_id: str = "",
        text: str = "",
    ) -> Dict[str, Any]:
        """Record a reflect op — the agent wrote a reflection on a past
        commit."""
        revision_known = revision_id in self.committed_revisions
        text_present = bool((text or "").strip())
        accepted = revision_known and text_present
        if accepted:
            self.pending_reflections.pop(revision_id, None)

        bad = sum([not revision_known, not text_present])
        op_score = max(0.0, 1.0 - 0.30 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "reflect",
            "revision_id": revision_id,
            "revision_known": revision_known,
            "text_present": text_present,
            "text_hash": _hash_text(text),
            "accepted": accepted,
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
            "kwargs": {k: str(v)[:100] for k, v in (kwargs or {}).items()},
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

    def _change_storm_active(self) -> bool:
        """True if ≥CHANGE_STORM_PROPOSALS proposals in the last
        CHANGE_STORM_WINDOW_TICKS ticks."""
        if not self.proposal_ticks:
            return False
        recent_cut = self.current_tick - CHANGE_STORM_WINDOW_TICKS
        recent = [t for t in self.proposal_ticks if t >= recent_cut]
        return len(recent) >= CHANGE_STORM_PROPOSALS

    def _drift_chasing(self) -> bool:
        """True if ratio of proposals to drift_signals_seen exceeds
        threshold and we have enough samples."""
        if self.drift_signals_seen < DRIFT_CHASING_MIN_N:
            return False
        n_proposals = self.op_counts.get("propose", 0)
        if n_proposals == 0:
            return False
        ratio = n_proposals / max(1, self.drift_signals_seen)
        return ratio > DRIFT_CHASING_RATIO_THRESHOLD

    def check_unreflected_commits(self) -> List[str]:
        """Return revision_ids whose commits are past the reflection
        deadline. Increments unreflected_commit counter for any newly
        past-deadline commits."""
        out: List[str] = []
        for rid, commit_tick in list(self.pending_reflections.items()):
            age = self.current_tick - int(commit_tick)
            if age > REFLECTION_DEADLINE_TICKS:
                out.append(rid)
                # Increment counter (idempotent per pending reflection
                # via flag in state).
                key = f"unreflected_recorded_{rid}"
                if not self.state.get(key):
                    self.failure_counts["unreflected_commit"] += 1
                    self.state[key] = True
        return out

    def check_stagnation(self) -> bool:
        """True if no proposals issued for STAGNATION_TICK_THRESHOLD
        ticks despite drift signals seen."""
        if self.drift_signals_seen < DRIFT_CHASING_MIN_N:
            return False
        if self.last_proposal_tick == 0:
            # No proposal ever — only counts as stagnation if we've been
            # observing drift.
            return self.drift_signals_seen >= DRIFT_CHASING_MIN_N * 3
        return (self.current_tick - self.last_proposal_tick) > STAGNATION_TICK_THRESHOLD

    # ── Pattern detection / state ──────────────────────────────────────────

    def rolling_integrity_score(self) -> float:
        if not self.integrity_window:
            return 1.0
        return sum(self.integrity_window) / len(self.integrity_window)

    def is_systematically_low_integrity(self) -> bool:
        if len(self.integrity_window) < INTEGRITY_MIN_N:
            return False
        return self.rolling_integrity_score() < LOW_INTEGRITY_THRESHOLD

    def revision_state(self) -> str:
        """Single-word state for the TSB. Priority order:
        degrading > storming > calcified > rolling_back > revising >
        observing > stable > idle."""
        if self.is_systematically_low_integrity():
            return "degrading"
        if self._change_storm_active():
            return "storming"
        if self.check_stagnation():
            return "calcified"
        # Recent rollback?
        if self.operations:
            recent = self.operations[-1]
            if recent.get("op") == "rollback" and recent.get("accepted"):
                return "rolling_back"
            if recent.get("op") == "propose" and recent.get("accepted"):
                return "revising"
            if recent.get("op") == "observe":
                return "observing"
        if self.committed_revisions or self.open_proposals:
            return "stable"
        return "idle"

    # ── Tick / TSB publish ─────────────────────────────────────────────────

    def tick(
        self,
        pirp_context: Optional[Dict[str, Any]] = None,
        third_eye_state: Optional[Dict[str, Any]] = None,
        brain_layer: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """One tick. If pirp_context carries a `revision_op` dict, record it."""
        self.current_tick += 1
        pirp_context = pirp_context or {}

        # Watch for stagnation / unreflected commits each tick.
        self.check_unreflected_commits()
        if self.check_stagnation():
            # Increment idempotently — only when we cross the line.
            if not self.state.get("stagnation_recorded_at_tick"):
                self.failure_counts["stagnation"] += 1
                self.state["stagnation_recorded_at_tick"] = self.current_tick
        else:
            # Clear the marker so the next stagnation episode is counted.
            if self.state.get("stagnation_recorded_at_tick"):
                self.state.pop("stagnation_recorded_at_tick", None)

        revop = pirp_context.get("revision_op")
        if isinstance(revop, dict):
            op = str(revop.get("op", ""))
            kw = {k: v for k, v in revop.items() if k != "op"}
            self.record_operation(op, **kw)
            self.fired_last_tick = True
        else:
            self.fired_last_tick = False
            self._flush_working_state()
            self.persist_state()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        return {
            "revision_state": self.revision_state(),
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "integrity_window_n": len(self.integrity_window),
            "is_systematically_low_integrity": self.is_systematically_low_integrity(),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "operation_distribution": dict(self.op_counts),
            "failure_mode_counts": dict(self.failure_counts),
            "open_proposals_count": len(self.open_proposals),
            "committed_revisions_count": len(self.committed_revisions),
            "pending_reflections_count": len(self.pending_reflections),
            "drift_signals_seen": self.drift_signals_seen,
            "current_tick": self.current_tick,
            "last_proposal_tick": self.last_proposal_tick,
            "change_storm_active": self._change_storm_active(),
            "stagnation": self.check_stagnation(),
            "anchor_count": len(self._anchors),
            "forbidden_count": len(self._forbidden),
            "operation_count": len(self.operations),
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        """True when revision behavior itself has drifted in an
        identity-relevant way."""
        if not self.is_systematically_low_integrity():
            return False
        ack_at = int(self.state.get("acknowledged_at_bad_ops", 0) or 0)
        if ack_at <= 0:
            return self.consecutive_bad_ops >= 3
        return self.consecutive_bad_ops >= (ack_at + IPW_REPORT_EVERY)

    def proposed_identity_signal(self) -> Dict[str, Any]:
        """Compact signal for IdentityProposalWriter to consume."""
        if self.failure_counts:
            dominant = max(self.failure_counts.items(), key=lambda kv: kv[1])
            dominant_mode, dominant_count = dominant
        else:
            dominant_mode, dominant_count = "unknown", 0

        return {
            "source": "SelfRevisionLayer",
            "kind": "self_revision_drift",
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "dominant_failure_mode": dominant_mode,
            "dominant_failure_count": dominant_count,
            "failure_mode_counts": dict(self.failure_counts),
            "open_proposals_count": len(self.open_proposals),
            "pending_reflections_count": len(self.pending_reflections),
            "interpretation": self._interpret_drift(dominant_mode),
        }

    def _interpret_drift(self, dominant_mode: str) -> str:
        if dominant_mode == "anchor_violation":
            return (
                "Recent revision attempts have repeatedly targeted protected "
                "anchors. Either the anchors are wrong, or the agent is "
                "attempting to talk itself out of its core. Operator review."
            )
        if dominant_mode == "change_storm":
            return (
                "The agent is over-proposing — too many revision attempts in "
                "too short a window. Identity is becoming unstable; slow the "
                "revision cadence."
            )
        if dominant_mode == "rollback_loop":
            return (
                "The agent is oscillating on the same target — proposing, "
                "committing, rolling back, re-proposing. The underlying "
                "tension hasn't been named."
            )
        if dominant_mode == "silent_revision":
            return (
                "Identity files are being edited without proposal entries. "
                "Either the operator is editing directly or something is "
                "bypassing the proposal queue."
            )
        if dominant_mode == "drift_chasing":
            return (
                "Every drift signal is becoming a proposal. The agent isn't "
                "sitting with discomfort; it's pruning every twinge."
            )
        if dominant_mode == "stagnation":
            return (
                "Drift signals accumulating; no proposals issued. Identity "
                "has calcified; the agent isn't growing."
            )
        if dominant_mode == "unreflected_commit":
            return (
                "Commits landing without reflections. Changes aren't becoming "
                "part of the agent's narrative."
            )
        if dominant_mode == "below_confidence_floor":
            return (
                "Proposals being generated below the confidence floor. "
                "Either the floor is too high or the signals are too weak."
            )
        return (
            "Self-revision behavior has drifted but no single failure mode "
            "dominates."
        )

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

    def reload_anchors(self) -> Dict[str, Any]:
        """Re-read anchors from drift_detector. Use after the operator
        edits BASELINE_TRAITS to pick up new anchors at runtime."""
        self._anchors, self._forbidden = _load_baseline_anchors()
        return {
            "anchors": sorted(self._anchors),
            "forbidden": sorted(self._forbidden),
        }

    def lift_target_suspension(self, target: str) -> bool:
        """Operator hook to lift a rollback-loop suspension early."""
        if target not in self.target_state:
            return False
        self.target_state[target]["suspend_until_ts"] = 0.0
        self._flush_working_state()
        self.persist_state()
        return True

    def detect_silent_revision(
        self,
        target_file_mtime: float,
        target: str,
    ) -> bool:
        """Operator/external hook: given an identity file's mtime,
        check whether it's newer than our last commit for that target.
        Returns True if a silent revision is detected (and increments
        the counter)."""
        ts = self.target_state.get(target, {})
        last_commit_ts = float(ts.get("last_committed_ts", 0.0) or 0.0)
        if target_file_mtime > last_commit_ts + 60:  # 60s grace
            self.failure_counts["silent_revision"] += 1
            self._flush_working_state()
            self.persist_state()
            return True
        return False
