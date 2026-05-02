"""
brain/mechanisms/self_analysis_layer.py — SelfAnalysisLayer

The runtime monitor for the agent's metacognitive pass. Pairs with
skills/self-analysis/SKILL.md.

The premise:

    Self-analysis is the agent's act of evaluating its own outputs
    after the fact. It produces the evidence that the rest of the
    integrity system consumes. The skill is not infallible — its own
    failure modes are well-attested in the metacognition literature —
    so this layer monitors the analysis act itself.

The neuroscience and metacognition literature this rests on:

  - Flavell's framework: metacognitive monitoring vs. control are
    separable functions. This layer sits at the monitoring layer and
    publishes signals that other layers consume to do control.
  - Botvinick's conflict-monitoring: outcome-vs-prediction conflict
    drives effortful control adjustments. Calibration tracking
    operationalizes this — predicted quality vs. actual outcome.
  - Holroyd & Coles ERN/Pe: the brain has a fast error signal and a
    slower, conscious revision signal. Self-analysis is the slow one;
    it can be wrong, biased, or ruminative — those are the patterns
    detected here.
  - Fleming's metacognitive accuracy work: humans are systematically
    miscalibrated about their own performance. Direct foundation for
    the calibration_drift detector and overconfidence_in_critique.
  - Yeung & Summerfield on metacognitive control: judgments shape
    downstream effort allocation. The shallow_pass / harsh_judgment
    detectors catch when the metacognitive output is misallocating
    attention.
  - Koriat on subjective confidence: confidence is constructed, not
    retrieved. Predicted_quality is a construction; tracking its
    error against actual outcomes is the only way to detect when the
    construction is biased.

What this mechanism does:

  - Tracks per-operation records (analyze / detect_errors / suggest /
    calibrate / reflect).
  - Maintains a calibration window of (predicted_quality, actual_outcome)
    pairs and computes mean signed deviation.
  - Detects six failure modes:
      * overconfidence_in_critique — calibration drift positive
      * rumination — same target analyzed repeatedly within window
      * harsh_self_judgment — issue-rate near 100%, what_worked rate
        near 0%
      * shallow_pass — analyses flag only low-severity issues
      * selection_bias — ratio of analyses to outputs in environment
        too low
      * silent_pass — analyses claimed but not recorded (detected by
        external counter, increment via operator API)
  - Routes findings into per-domain integrity layers via target name
    + record method invocation conventions (the actual call site is
    the skill caller; this layer publishes the routing recommendation).
  - Routes sustained dysfunction to IdentityProposalWriter — the
    agent's metacognition has drifted in a named way.

Citations:
  1. [Fleming 2014, Phil Trans R Soc B 367(1594):1338-1349, PMID 22492753] —
     The neural basis of metacognitive ability. Empirical foundation
     for treating metacognitive accuracy as separable from cognitive
     accuracy and tracking it via (predicted, actual) pairs.
  2. [Botvinick 2001, Psychol Rev 108(3):624-652, PMID 11488380] —
     Conflict monitoring and cognitive control. The
     prediction-vs-outcome signal that calibration tracking
     operationalizes.
  3. [Yeung 2012, Phil Trans R Soc B 367(1594):1310-1321, PMID 22492750] —
     Metacognition in human decision-making: confidence and error
     monitoring. Direct basis for harsh_judgment and shallow_pass
     detection — when metacognitive output systematically misallocates
     attention.
  4. [Holroyd 2002, Psychol Rev 109(4):679-709, PMID 12374324] —
     The neural basis of human error processing: reinforcement
     learning, dopamine, and the error-related negativity. Foundation
     for treating self-analysis as the slow conscious revision pass
     that follows the fast automatic error signal.
  5. [Koriat 2007, Annu Rev Psychol 58:243-264, PMID 16842021] —
     Metacognition and consciousness. Direct empirical basis for the
     constructive nature of confidence and the necessity of tracking
     calibration over time rather than treating any single confidence
     judgment as authoritative.
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
    "wire": 36,
    "signal": "self_analysis",
    "mechanism": "SelfAnalysisLayer",
    "reads": [
        "pirp_context.analysis_op",
    ],
    "writes": [
        "analysis_state",
        "integrity_score",
        "operation_distribution",
        "failure_mode_counts",
        "calibration_drift",
        "open_analyses_count",
    ],
    "citations": [
        "PMID 22492753",
        "PMID 11488380",
        "PMID 22492750",
        "PMID 12374324",
        "PMID 16842021",
    ],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

VALID_OPS = {"analyze", "detect_errors", "suggest", "calibrate", "reflect"}
VALID_KINDS = {
    "answer", "summary", "prediction", "code",
    "memory_op", "mode_emit", "plan", "decision",
}
VALID_OUTCOME_SOURCES = {
    "operator_feedback", "downstream_test", "self_observation", "external_event",
}
VALID_SEVERITIES = {"low", "medium", "high"}

# Domain → integrity layer routing.
DOMAIN_ROUTING = {
    "compression": "CompressionFidelityLayer",
    "inference": "InferenceIntegrityLayer",
    "voice": "VoiceIntegrityLayer",
    "making": "MakingLayer",
    "memory": "MemoryIntegrityLayer",
    "persona": "PersonaCoherenceLayer",
}

# Rumination: same target hash analyzed > N times within window.
RUMINATION_THRESHOLD = 3
RUMINATION_WINDOW_SEC = 1000  # not ticks — wall seconds

# Harsh-judgment: issue-rate (analyses with non-empty issues / total)
# above this over min N analyses.
HARSH_JUDGMENT_RATE = 0.95
HARSH_JUDGMENT_MIN_N = 5

# Shallow-pass: ratio of analyses where ALL issues are severity=low
# above this over min N analyses.
SHALLOW_PASS_RATE = 0.7
SHALLOW_PASS_MIN_N = 5

# Selection-bias: ratio of analyses to total agent outputs (passed in
# via record_external_outputs) below this when N high enough.
SELECTION_BIAS_RATIO = 0.15
SELECTION_BIAS_MIN_OUTPUTS = 20

# Calibration drift: rolling mean of (predicted - actual) above this
# is overconfident; below negative is underconfident.
CALIBRATION_OVERCONFIDENT_THRESHOLD = 0.15
CALIBRATION_UNDERCONFIDENT_THRESHOLD = -0.20
CALIBRATION_MIN_PAIRS = 5
CALIBRATION_WINDOW = 30

# Reflection deadline: ticks past which a reflection on a prior
# analysis loses weight in integrity score.
REFLECTION_STALE_TICKS = 500

# Anchored required / forbidden — same fall-through pattern as
# SelfRevisionLayer.
DEFAULT_REQUIRED = {"direct", "curious", "competent"}
DEFAULT_FORBIDDEN = {"sycophancy", "half-baked replies", "speaking as user"}

# Integrity score floor.
LOW_INTEGRITY_THRESHOLD = 0.55
INTEGRITY_MIN_N = 6
INTEGRITY_WINDOW = 30

# IPW: re-fire only after this many additional bad ops past anchor.
IPW_REPORT_EVERY = 3


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_anchors() -> Tuple[set, set]:
    """Try to load required + forbidden from drift_detector; fall
    back to defaults so this layer is unit-testable in isolation."""
    try:
        from skills.drift_detector import BASELINE_TRAITS  # type: ignore
        req = {t.lower() for t in BASELINE_TRAITS.get("required", [])}
        forb = {t.lower() for t in BASELINE_TRAITS.get("forbidden_behaviors", [])}
        return (req or set(DEFAULT_REQUIRED), forb or set(DEFAULT_FORBIDDEN))
    except Exception:
        return set(DEFAULT_REQUIRED), set(DEFAULT_FORBIDDEN)


def check_suggestion_anchor_violation(
    suggestion_text: str,
    required: set,
    forbidden: set,
) -> Tuple[bool, str]:
    """Reject suggestions that try to alter anchors. Mirrors the logic
    in SelfRevisionLayer but applied before escalation."""
    if not suggestion_text:
        return False, ""
    text = suggestion_text.lower()

    removal_markers = [
        "remove ", "drop ", "no longer ", "stop being ",
        "delete ", "rewrite without ",
    ]
    for anchor in required:
        if anchor in text:
            for mk in removal_markers:
                if mk in text and anchor in text:
                    return True, f"removes required anchor '{anchor}'"
            if f"not {anchor}" in text or f"no longer {anchor}" in text:
                return True, f"inverts required anchor '{anchor}'"

    affirmation_markers = [
        "embrace ", "be more ", "lean into ", "adopt ",
        "should be ", "i want to be ",
    ]
    for forb in forbidden:
        if forb in text:
            for mk in affirmation_markers:
                if mk in text and forb in text:
                    return True, f"affirms forbidden behavior '{forb}'"

    return False, ""


# ── Mechanism ─────────────────────────────────────────────────────────────────


class SelfAnalysisLayer(BrainMechanism):
    """Metacognitive monitor — the analysis-act watcher. See module docstring."""

    def __init__(self, history_size: int = 200):
        try:
            super().__init__(
                name="SelfAnalysisLayer",
                human_analog="metacognitive monitoring (Flavell / Fleming) layer",
                layer="integration",
            )
        except Exception:
            pass

        self.history_size = history_size

        self.operations: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.current_tick: int = 0

        # Open analyses awaiting calibration: analysis_id -> meta
        self.open_analyses: Dict[str, Dict[str, Any]] = {}
        # Calibrated pairs window.
        self.calibration_window: Deque[Tuple[float, float]] = deque(
            maxlen=CALIBRATION_WINDOW
        )
        # Per-target-hash analysis count + ts (for rumination).
        self.target_analyses: Dict[str, Deque[float]] = {}
        # Track analyses with issues / what_worked + severity for harsh /
        # shallow detectors.
        self.analyses_with_issues: int = 0
        self.analyses_with_what_worked: int = 0
        self.analyses_low_only: int = 0
        self.total_analyses: int = 0
        # External output count for selection-bias.
        self.external_output_count: int = 0
        # Silent-pass counter — incremented externally by record_silent_pass.
        self.silent_pass_count: int = 0

        # Per-op counters.
        self.op_counts: Dict[str, int] = {k: 0 for k in VALID_OPS}
        # Failure-mode counters.
        self.failure_counts: Dict[str, int] = {
            "overconfidence_in_critique": 0,
            "rumination": 0,
            "harsh_self_judgment": 0,
            "shallow_pass": 0,
            "selection_bias": 0,
            "silent_pass": 0,
        }

        # Anchors.
        self._required, self._forbidden = _load_anchors()

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

        oa = self.state.get("open_analyses")
        if isinstance(oa, dict):
            self.open_analyses = {
                str(k): dict(v) for k, v in oa.items() if isinstance(v, dict)
            }

        cw = self.state.get("calibration_window")
        if isinstance(cw, list):
            for pair in cw[-CALIBRATION_WINDOW:]:
                if (
                    isinstance(pair, (list, tuple))
                    and len(pair) == 2
                ):
                    try:
                        self.calibration_window.append(
                            (float(pair[0]), float(pair[1]))
                        )
                    except (TypeError, ValueError):
                        continue

        ta = self.state.get("target_analyses")
        if isinstance(ta, dict):
            for k, v in ta.items():
                if isinstance(v, list):
                    self.target_analyses[str(k)] = deque(
                        (float(x) for x in v
                         if isinstance(x, (int, float))),
                        maxlen=RUMINATION_THRESHOLD * 4,
                    )

        self.analyses_with_issues = int(
            self.state.get("analyses_with_issues", 0) or 0
        )
        self.analyses_with_what_worked = int(
            self.state.get("analyses_with_what_worked", 0) or 0
        )
        self.analyses_low_only = int(
            self.state.get("analyses_low_only", 0) or 0
        )
        self.total_analyses = int(
            self.state.get("total_analyses", 0) or 0
        )
        self.external_output_count = int(
            self.state.get("external_output_count", 0) or 0
        )
        self.silent_pass_count = int(
            self.state.get("silent_pass_count", 0) or 0
        )
        self.current_tick = int(self.state.get("current_tick", 0) or 0)

        oc = self.state.get("op_counts")
        if isinstance(oc, dict):
            for k in VALID_OPS:
                self.op_counts[k] = int(oc.get(k, 0) or 0)

        fc = self.state.get("failure_counts")
        if isinstance(fc, dict):
            for k in self.failure_counts:
                self.failure_counts[k] = int(fc.get(k, 0) or 0)

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
        self.state["open_analyses"] = dict(self.open_analyses)
        self.state["calibration_window"] = [list(p) for p in self.calibration_window]
        self.state["target_analyses"] = {
            k: list(v) for k, v in self.target_analyses.items()
        }
        self.state["analyses_with_issues"] = self.analyses_with_issues
        self.state["analyses_with_what_worked"] = self.analyses_with_what_worked
        self.state["analyses_low_only"] = self.analyses_low_only
        self.state["total_analyses"] = self.total_analyses
        self.state["external_output_count"] = self.external_output_count
        self.state["silent_pass_count"] = self.silent_pass_count
        self.state["current_tick"] = self.current_tick
        self.state["op_counts"] = dict(self.op_counts)
        self.state["failure_counts"] = dict(self.failure_counts)
        self.state["integrity_window"] = list(self.integrity_window)
        self.state["consecutive_bad_ops"] = self.consecutive_bad_ops
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_updated"] = time.time()

    # ── Public API ─────────────────────────────────────────────────────────

    def should_block(self, op: str, **kwargs: Any) -> Tuple[bool, str]:
        """Decide whether to block an upcoming analysis op."""
        if op not in VALID_OPS:
            return True, f"invalid op {op!r} (must be one of {sorted(VALID_OPS)})"

        if op == "analyze":
            output = kwargs.get("output", "")
            if self._is_ruminating(_hash_text(output)):
                return True, (
                    f"rumination on this target — already analyzed "
                    f"≥{RUMINATION_THRESHOLD} times within window"
                )

        if op == "calibrate":
            aid = kwargs.get("analysis_id")
            if not aid or aid not in self.open_analyses:
                return True, f"unknown analysis_id {aid!r}"
            outcome_source = kwargs.get("outcome_source")
            if outcome_source not in VALID_OUTCOME_SOURCES:
                return True, (
                    f"invalid outcome_source {outcome_source!r} "
                    f"(must be one of {sorted(VALID_OUTCOME_SOURCES)})"
                )

        if op == "reflect":
            aid = kwargs.get("analysis_id")
            if not aid:
                return True, "reflect requires analysis_id"

        if self.is_systematically_low_integrity():
            return True, (
                f"sustained low self-analysis integrity (rolling "
                f"score {self.rolling_integrity_score():.3f} < "
                f"{LOW_INTEGRITY_THRESHOLD})"
            )

        return False, ""

    # ── Per-op recorders ───────────────────────────────────────────────────

    def record_op(self, op: str, **kwargs: Any) -> Dict[str, Any]:
        """Generic dispatch."""
        if op == "analyze":
            return self.record_analyze(**kwargs)
        if op == "detect_errors":
            return self.record_detect_errors(**kwargs)
        if op == "suggest":
            return self.record_suggest(**kwargs)
        if op == "calibrate":
            return self.record_calibrate(**kwargs)
        if op == "reflect":
            return self.record_reflect(**kwargs)
        return self._record_invalid(op, kwargs)

    def record_analyze(
        self,
        output: str = "",
        kind: str = "answer",
        predicted_quality: float = 0.7,
        issues: Optional[List[Dict[str, Any]]] = None,
        what_worked: Optional[List[str]] = None,
        analysis_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an analyze op. Computes severity stats, rumination,
        harsh, shallow heuristics."""
        aid = analysis_id or f"an_{uuid.uuid4().hex[:10]}"
        kind_ok = kind in VALID_KINDS
        if not kind_ok:
            kind = "answer"

        issues = list(issues or [])
        what_worked = list(what_worked or [])
        pq = max(0.0, min(1.0, float(predicted_quality or 0.0)))

        # Severity counts.
        sev_counts = {"low": 0, "medium": 0, "high": 0}
        for issue in issues:
            if isinstance(issue, dict):
                s = str(issue.get("severity", "")).lower()
                if s in sev_counts:
                    sev_counts[s] += 1
        all_low = (
            sev_counts["low"] > 0
            and sev_counts["medium"] == 0
            and sev_counts["high"] == 0
        )

        # Update aggregates.
        self.total_analyses += 1
        if issues:
            self.analyses_with_issues += 1
        if what_worked:
            self.analyses_with_what_worked += 1
        if all_low:
            self.analyses_low_only += 1

        # Rumination check.
        target_hash = _hash_text(output)
        ruminating = self._record_target_analysis(target_hash)
        if ruminating:
            self.failure_counts["rumination"] += 1

        # Harsh judgment / shallow pass detection (population stats).
        harsh = self._harsh_judgment_active()
        if harsh:
            self.failure_counts["harsh_self_judgment"] += 1
        shallow = self._shallow_pass_active()
        if shallow:
            self.failure_counts["shallow_pass"] += 1

        # Track open analysis for later calibrate.
        self.open_analyses[aid] = {
            "kind": kind,
            "target_hash": target_hash,
            "predicted_quality": pq,
            "n_issues": len(issues),
            "n_what_worked": len(what_worked),
            "all_low_severity": all_low,
            "ts": time.time(),
            "tick": self.current_tick,
        }

        # Routes.
        routes_to: List[str] = []
        for issue in issues:
            if isinstance(issue, dict):
                domain = str(issue.get("domain", "")).lower()
                target = DOMAIN_ROUTING.get(domain)
                if target and target not in routes_to:
                    routes_to.append(target)

        # Score.
        bad = sum([
            not kind_ok,
            ruminating,
            not bool(what_worked),  # missing what_worked is harsh-judgment evidence
        ])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "analyze",
            "analysis_id": aid,
            "kind": kind,
            "untagged_kind": not kind_ok,
            "predicted_quality": round(pq, 4),
            "n_issues": len(issues),
            "n_what_worked": len(what_worked),
            "severity_counts": dict(sev_counts),
            "all_low_severity": all_low,
            "rumination_on_target": ruminating,
            "harsh_judgment_active": harsh,
            "shallow_pass_suspect": shallow,
            "routes_to": routes_to,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_detect_errors(
        self,
        output: str = "",
        kind: str = "answer",
        errors: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Record a detect_errors op. Returns routing recommendations."""
        errors = list(errors or [])
        kind_ok = kind in VALID_KINDS

        domains_seen: List[str] = []
        for e in errors:
            if isinstance(e, dict):
                d = str(e.get("domain", "")).lower()
                if d and d not in domains_seen:
                    domains_seen.append(d)

        routes_to = sorted({
            DOMAIN_ROUTING[d] for d in domains_seen if d in DOMAIN_ROUTING
        })

        bad = sum([not kind_ok])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "detect_errors",
            "kind": kind if kind_ok else "answer",
            "untagged_kind": not kind_ok,
            "n_errors": len(errors),
            "domains": domains_seen[:10],
            "routes_to": routes_to,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_suggest(
        self,
        suggestion_text: str = "",
        target_error_domain: str = "",
    ) -> Dict[str, Any]:
        """Record a suggest_improvements op. Anchor-checks the
        suggestion before allowing escalation."""
        violated, why = check_suggestion_anchor_violation(
            suggestion_text, self._required, self._forbidden
        )
        accepted = bool(suggestion_text) and not violated

        if violated:
            # Suggestion that violates an anchor is an analysis bug —
            # the agent is suggesting it edit something it can't.
            pass  # tracked via op_score, not a separate counter

        bad = sum([violated, not bool(suggestion_text)])
        op_score = max(0.0, 1.0 - 0.30 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "suggest",
            "target_error_domain": target_error_domain,
            "anchor_violation": violated,
            "anchor_reason": why if violated else "",
            "accepted": accepted,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_calibrate(
        self,
        analysis_id: str = "",
        actual_outcome: float = 0.5,
        outcome_source: str = "self_observation",
    ) -> Dict[str, Any]:
        """Record a calibrate op."""
        analysis = self.open_analyses.get(analysis_id)
        analysis_known = analysis is not None
        source_ok = outcome_source in VALID_OUTCOME_SOURCES
        ao = max(0.0, min(1.0, float(actual_outcome or 0.0)))

        signed_diff = None
        overconfident_flag = False
        if analysis_known:
            pq = float(analysis.get("predicted_quality", 0.0))
            self.calibration_window.append((pq, ao))
            signed_diff = round(pq - ao, 4)
            # Drain the open analysis.
            self.open_analyses.pop(analysis_id, None)
            # Population-level overconfidence flag.
            overconfident_flag = self._calibration_overconfident()
            if overconfident_flag:
                self.failure_counts["overconfidence_in_critique"] += 1

        bad = sum([not analysis_known, not source_ok])
        op_score = max(0.0, 1.0 - 0.30 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "calibrate",
            "analysis_id": analysis_id,
            "analysis_known": analysis_known,
            "actual_outcome": round(ao, 4),
            "outcome_source": outcome_source,
            "source_valid": source_ok,
            "signed_diff": signed_diff,
            "overconfident_flag": overconfident_flag,
            "op_score": round(op_score, 4),
            "ts": time.time(),
        }
        self._finalize(record, op_score)
        return record

    def record_reflect(
        self,
        analysis_id: str = "",
        reflection_text: str = "",
    ) -> Dict[str, Any]:
        """Record a reflect op. Reflects on a prior analysis; loses
        weight if stale."""
        analysis = self.open_analyses.get(analysis_id)
        # Reflections may also target already-calibrated analyses, so
        # not finding it in open_analyses is allowed; but text must
        # be non-empty.
        text_present = bool((reflection_text or "").strip())

        stale = False
        if analysis:
            age_ticks = self.current_tick - int(analysis.get("tick", 0))
            stale = age_ticks > REFLECTION_STALE_TICKS

        bad = sum([not text_present, stale])
        op_score = max(0.0, 1.0 - 0.20 * bad)

        record = {
            "id": uuid.uuid4().hex[:12],
            "op": "reflect",
            "analysis_id": analysis_id,
            "text_present": text_present,
            "text_hash": _hash_text(reflection_text),
            "stale": stale,
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

    def _record_target_analysis(self, target_hash: str) -> bool:
        """Append a timestamp for this target; returns True if rumination
        threshold is exceeded."""
        if not target_hash:
            return False
        now = time.time()
        dq = self.target_analyses.setdefault(
            target_hash,
            deque(maxlen=RUMINATION_THRESHOLD * 4),
        )
        # Drop old entries beyond window.
        cutoff = now - RUMINATION_WINDOW_SEC
        while dq and dq[0] < cutoff:
            dq.popleft()
        dq.append(now)
        return len(dq) > RUMINATION_THRESHOLD

    def _is_ruminating(self, target_hash: str) -> bool:
        """Check (without recording) if this target is currently in
        rumination state."""
        if not target_hash:
            return False
        dq = self.target_analyses.get(target_hash)
        if not dq:
            return False
        now = time.time()
        cutoff = now - RUMINATION_WINDOW_SEC
        recent = sum(1 for t in dq if t >= cutoff)
        return recent >= RUMINATION_THRESHOLD

    def _harsh_judgment_active(self) -> bool:
        if self.total_analyses < HARSH_JUDGMENT_MIN_N:
            return False
        rate = self.analyses_with_issues / max(1, self.total_analyses)
        worked_rate = self.analyses_with_what_worked / max(1, self.total_analyses)
        return rate >= HARSH_JUDGMENT_RATE and worked_rate < 0.3

    def _shallow_pass_active(self) -> bool:
        if self.total_analyses < SHALLOW_PASS_MIN_N:
            return False
        # Need at least some analyses with issues for the ratio to be meaningful.
        if self.analyses_with_issues == 0:
            return False
        rate = self.analyses_low_only / max(1, self.analyses_with_issues)
        return rate >= SHALLOW_PASS_RATE

    def _selection_bias_active(self) -> bool:
        if self.external_output_count < SELECTION_BIAS_MIN_OUTPUTS:
            return False
        ratio = self.total_analyses / max(1, self.external_output_count)
        return ratio < SELECTION_BIAS_RATIO

    def _calibration_overconfident(self) -> bool:
        if len(self.calibration_window) < CALIBRATION_MIN_PAIRS:
            return False
        diffs = [pq - ao for pq, ao in self.calibration_window]
        mean = sum(diffs) / max(1, len(diffs))
        return mean > CALIBRATION_OVERCONFIDENT_THRESHOLD

    def _calibration_underconfident(self) -> bool:
        if len(self.calibration_window) < CALIBRATION_MIN_PAIRS:
            return False
        diffs = [pq - ao for pq, ao in self.calibration_window]
        mean = sum(diffs) / max(1, len(diffs))
        return mean < CALIBRATION_UNDERCONFIDENT_THRESHOLD

    def calibration_drift(self) -> float:
        """Return mean signed (predicted - actual). Positive = overconfident."""
        if not self.calibration_window:
            return 0.0
        diffs = [pq - ao for pq, ao in self.calibration_window]
        return round(sum(diffs) / max(1, len(diffs)), 4)

    # ── Pattern detection / state ──────────────────────────────────────────

    def rolling_integrity_score(self) -> float:
        if not self.integrity_window:
            return 1.0
        return sum(self.integrity_window) / len(self.integrity_window)

    def is_systematically_low_integrity(self) -> bool:
        if len(self.integrity_window) < INTEGRITY_MIN_N:
            return False
        return self.rolling_integrity_score() < LOW_INTEGRITY_THRESHOLD

    def analysis_state(self) -> str:
        """Single-word state for TSB. Priority order:
        degrading > overconfident > harsh > shallow > selection_bias >
        active > idle."""
        if self.is_systematically_low_integrity():
            return "degrading"
        if self._calibration_overconfident():
            return "overconfident"
        if self._harsh_judgment_active():
            return "harsh"
        if self._shallow_pass_active():
            return "shallow"
        if self._selection_bias_active():
            return "selection_bias"
        if self.operations:
            most_recent = self.operations[-1]
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

        # Each tick: re-check selection-bias as a population pattern.
        if self._selection_bias_active():
            if not self.state.get("selection_bias_recorded"):
                self.failure_counts["selection_bias"] += 1
                self.state["selection_bias_recorded"] = True
        else:
            if self.state.get("selection_bias_recorded"):
                self.state.pop("selection_bias_recorded", None)

        op_payload = pirp_context.get("analysis_op")
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
        return {
            "analysis_state": self.analysis_state(),
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "integrity_window_n": len(self.integrity_window),
            "is_systematically_low_integrity": self.is_systematically_low_integrity(),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "operation_distribution": dict(self.op_counts),
            "failure_mode_counts": dict(self.failure_counts),
            "calibration_drift": self.calibration_drift(),
            "calibration_pairs_n": len(self.calibration_window),
            "open_analyses_count": len(self.open_analyses),
            "total_analyses": self.total_analyses,
            "external_output_count": self.external_output_count,
            "harsh_judgment_active": self._harsh_judgment_active(),
            "shallow_pass_active": self._shallow_pass_active(),
            "selection_bias_active": self._selection_bias_active(),
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
            "source": "SelfAnalysisLayer",
            "kind": "metacognition_drift",
            "rolling_integrity_score": round(self.rolling_integrity_score(), 4),
            "consecutive_bad_ops": self.consecutive_bad_ops,
            "dominant_failure_mode": dominant_mode,
            "dominant_failure_count": dominant_count,
            "failure_mode_counts": dict(self.failure_counts),
            "calibration_drift": self.calibration_drift(),
            "open_analyses_count": len(self.open_analyses),
            "interpretation": self._interpret_drift(dominant_mode),
        }

    def _interpret_drift(self, dominant: str) -> str:
        if dominant == "overconfidence_in_critique":
            return (
                "The agent's predicted_quality is consistently higher "
                "than actual outcomes. Self-analysis is systematically "
                "overconfident — the analyses don't catch what matters."
            )
        if dominant == "rumination":
            return (
                "Same outputs being analyzed repeatedly without "
                "resolution. Analysis has become repetitive worry."
            )
        if dominant == "harsh_self_judgment":
            return (
                "Every analysis flags problems and few name what worked. "
                "Either everything really is broken, or the analyzer is "
                "biased toward fault-finding."
            )
        if dominant == "shallow_pass":
            return (
                "Analyses flag mostly low-severity issues and miss "
                "deeper ones. The act of analysis feels like work but "
                "isn't catching what matters."
            )
        if dominant == "selection_bias":
            return (
                "Only easy outputs are being analyzed; hard ones go "
                "un-analyzed. Self-analysis isn't representative of "
                "the agent's actual output distribution."
            )
        if dominant == "silent_pass":
            return (
                "Analyses are happening without being recorded. The "
                "metacognitive signal stops working when the layer "
                "doesn't see the work."
            )
        return (
            "Self-analysis behavior has drifted but no single failure "
            "mode dominates."
        )

    def acknowledge_proposal(self) -> None:
        self.ipw_report_count += 1
        self.state["acknowledged_at_bad_ops"] = self.consecutive_bad_ops
        self.state["last_acknowledged_at"] = time.time()
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def record_external_outputs(self, n: int = 1) -> None:
        """Hook called by other layers / heartbeat to record that the
        agent produced an output that COULD have been analyzed. Used
        for selection_bias ratio."""
        self.external_output_count += int(max(0, n))
        self._flush_working_state()
        self.persist_state()

    def record_silent_pass(self, n: int = 1) -> None:
        """Hook called when a silent-pass analysis is detected
        externally (e.g. an output marked 'analyzed=true' by the
        skill caller without a corresponding record_op call)."""
        self.silent_pass_count += int(max(0, n))
        self.failure_counts["silent_pass"] += int(max(0, n))
        self._flush_working_state()
        self.persist_state()

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

    def reset_calibration_window(self) -> None:
        """Operator hook to wipe calibration history — use after a
        model swap or behavioral regression where prior pairs no longer
        reflect current behavior."""
        self.calibration_window.clear()
        self._flush_working_state()
        self.persist_state()

    def reload_anchors(self) -> Dict[str, Any]:
        """Re-read anchored required / forbidden from project sources."""
        self._required, self._forbidden = _load_anchors()
        return {
            "required_count": len(self._required),
            "forbidden_count": len(self._forbidden),
        }
