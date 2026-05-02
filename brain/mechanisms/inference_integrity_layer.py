"""
brain/mechanisms/inference_integrity_layer.py — InferenceIntegrityLayer

The runtime monitor for the agent's act of inference — extracting meaning
from structured data while staying epistemically honest. Pairs with
skills/data-analysis/SKILL.md. Every analysis the agent runs flows through
here so the brain has a single coherent view of what's been claimed, with
what confidence, on what sample size, and how those claims hold up against
later evidence.

The neuroscience analog is the metacognitive system — anterior prefrontal
cortex tracking confidence-vs-accuracy (knowing what you know), dorsolateral
PFC integrating evidence, dorsomedial PFC evaluating whether claimed
conclusions are actually supported. The failure modes here aren't motor
flailing or default-mode mush — they're the well-documented inferential
biases: overconfidence, confirmation, cherry-picking, miscalibration,
treating analysis output as ground truth.

What this mechanism does:

  - Tracks per-analysis records: intent, hypothesis, claim, confidence,
    sample size, dimensions used, alternatives considered, outcome (when
    later evidence arrives).
  - Maintains intent distribution (describe / compare / predict / explain).
  - Detects unhealthy patterns:
      * overconfident: claimed confidence exceeds what sample size supports
      * single_hypothesis_streak: many analyses testing one prior, none
        considering alternatives
      * shrinking_samples: sample size trending downward over recent
        analyses (cherry-picking signal)
      * miscalibrated: claimed confidence consistently higher than actual
        hit rate when outcomes arrive
  - Maintains a rolling calibration window: each (claimed_confidence,
    was_right) pair from `record_outcome()`. Score = how well claimed
    confidence matched reality.
  - Publishes inference state to the TSB so AttentionModifier can bias
    toward "consider alternatives" or "request more data" when patterns
    suggest the agent is reasoning past its evidence.
  - Hands off sustained miscalibration or overconfidence streaks to
    IdentityProposalWriter — claiming more certainty than the agent has is
    identity-relevant data.

Citations:
  1. [Bechara 1997, Science 275(5304):1293-1295, PMID 9036851] — somatic
     marker hypothesis: prefrontal damage impairs the appropriate
     attachment of confidence/uncertainty to decisions. Same circuit
     governs whether a claim's reported confidence honestly tracks the
     evidence supporting it.
  2. [De Martino 2006, Science 313(5787):684-687, PMID 16888142] — Frames,
     biases, and rational decision-making in the human brain. Amygdala-PFC
     interaction during framing effects; documents how confidence becomes
     dissociated from evidence under emotional or framing pressure. The
     overconfidence detection here is the analog of dorsomedial-PFC
     evaluation correcting that drift.
  3. [Fleming 2010, Science 329(5998):1541-1543, PMID 20847276] — Relating
     introspective accuracy to individual differences in brain structure.
     Anterior PFC and metacognitive accuracy (calibration). The
     calibration-tracking loop in this mechanism is the computational
     analog: tracking how often "I'm 80% sure" actually means 80% right.
"""

from brain.base_mechanism import BrainMechanism
import math
import os
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_DB = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")

__wire_meta__ = {
    "wire": 29,
    "signal": "inference_integrity",
    "mechanism": "InferenceIntegrityLayer",
    "reads": [
        "pirp_context.analysis",
        "pirp_context.analysis_outcome",
    ],
    "writes": [
        "inference_state",
        "calibration_score",
        "intent_distribution",
        "overconfidence_flag",
        "single_hypothesis_streak",
    ],
    "citations": ["PMID 9036851", "PMID 16888142", "PMID 20847276"],
}

# ── Tuning constants ──────────────────────────────────────────────────────────

# Per-intent sample-size sensitivity for the confidence-vs-sample heuristic.
# For a given intent, claimed_confidence > base + min(span, n / scale) is
# flagged as overconfident.
INTENT_CONFIDENCE_BUDGET = {
    "describe": (0.6, 0.4, 50.0),   # base, span, scale (lower stakes)
    "compare":  (0.5, 0.4, 75.0),
    "predict":  (0.4, 0.4, 100.0),  # highest stakes — confidence grows slower with n
    "explain":  (0.45, 0.4, 100.0),
}

# Single-hypothesis streak: this many analyses in a row testing the same
# hypothesis = streak detected.
SINGLE_HYPOTHESIS_STREAK_LEN = 5

# Shrinking samples: rolling 5-sample window, sample size trending downward
# enough to flag.
SHRINKING_SAMPLES_WINDOW = 5
SHRINKING_SAMPLES_RATIO = 0.5  # latest 2 mean is ≤ first 3 mean × 0.5 = shrinking

# Calibration: rolling window of (claim_conf, was_right) pairs.
CALIBRATION_WINDOW = 30
# Miscalibration threshold: |mean_claimed_conf - hit_rate| > this = miscalibrated
MISCALIBRATION_DELTA = 0.15
# Need at least this many resolved analyses before claiming miscalibration.
CALIBRATION_MIN_N = 8

# IPW: only re-fire after this many additional issues past threshold.
IPW_REPORT_EVERY = 3

VALID_INTENTS = {"describe", "compare", "predict", "explain"}
HEALTH_CLASSES = ("idle", "inferring", "well_calibrated", "overconfident", "miscalibrated")


def _confidence_budget(intent: str, sample_size: int) -> float:
    """Return the maximum claimed confidence supported by sample_size for
    this intent, per the project's confidence-vs-sample heuristic."""
    base, span, scale = INTENT_CONFIDENCE_BUDGET.get(
        intent, (0.5, 0.4, 100.0)
    )
    n = max(0, int(sample_size or 0))
    return base + min(span, n / scale)


# ── Mechanism ─────────────────────────────────────────────────────────────────

class InferenceIntegrityLayer(BrainMechanism):
    """
    The agent's inference monitor. See module docstring for full description.
    """

    def __init__(self, db_path: Optional[Path] = None, history_size: int = 200):
        try:
            super().__init__(
                name="InferenceIntegrityLayer",
                human_analog="anterior PFC metacognitive calibration / inference integrity",
                layer="integration",
            )
        except Exception:
            pass

        self.db_path = db_path or AGENT_DB
        self.history_size = history_size

        # In-memory working state.
        self.analyses: Deque[Dict[str, Any]] = deque(maxlen=history_size)
        self.intent_state: Dict[str, Dict[str, int]] = {
            k: {"total": 0, "overconfident": 0, "with_alternatives": 0}
            for k in VALID_INTENTS
        }
        # (claimed_confidence, was_right) pairs from record_outcome.
        self.calibration_window: Deque[Tuple[float, bool]] = deque(maxlen=CALIBRATION_WINDOW)
        self.consecutive_overconfident: int = 0
        self.fired_last_tick: bool = False
        self.ipw_report_count: int = 0

        # Restore persisted state.
        self.load_state()
        self._restore_working_state()

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        if not isinstance(self.state, dict):
            return

        saved = self.state.get("analyses")
        if isinstance(saved, list):
            for a in saved[-self.history_size:]:
                if isinstance(a, dict):
                    self.analyses.append(a)

        saved_intents = self.state.get("intent_state")
        if isinstance(saved_intents, dict):
            for k in VALID_INTENTS:
                if isinstance(saved_intents.get(k), dict):
                    self.intent_state[k].update({
                        sk: int(saved_intents[k].get(sk, 0) or 0)
                        for sk in ("total", "overconfident", "with_alternatives")
                    })

        saved_cal = self.state.get("calibration_window")
        if isinstance(saved_cal, list):
            for pair in saved_cal[-CALIBRATION_WINDOW:]:
                if isinstance(pair, (list, tuple)) and len(pair) == 2:
                    self.calibration_window.append(
                        (float(pair[0]), bool(pair[1]))
                    )

        self.consecutive_overconfident = int(
            self.state.get("consecutive_overconfident", 0) or 0
        )
        self.ipw_report_count = int(self.state.get("ipw_report_count", 0) or 0)

    def _flush_working_state(self) -> None:
        self.state["analyses"] = list(self.analyses)
        self.state["intent_state"] = {
            k: dict(self.intent_state[k]) for k in VALID_INTENTS
        }
        self.state["calibration_window"] = [
            [conf, right] for conf, right in self.calibration_window
        ]
        self.state["consecutive_overconfident"] = self.consecutive_overconfident
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_updated"] = time.time()

    # ── Public API: callers use these ──────────────────────────────────────

    def should_block(
        self,
        intent: str,
        sample_size: int = 0,
        claimed_confidence: float = 0.0,
    ) -> Tuple[bool, str]:
        """Decide whether to block an upcoming analysis.

        Blocks when:
          - intent is invalid
          - prediction on n<10 (sample-size floor for predict)
          - claimed_confidence ≥ 0.8 with sample_size < 30 (without override)
          - single-hypothesis streak detected and the new analysis doesn't
            consider alternatives

        The single-hypothesis-streak check requires the caller to pre-declare
        whether it has alternatives via a separate keyword; we don't have it
        here, so streak-based blocking is advisory: should_block returns True
        and the caller can override by adding alternatives.
        """
        if intent not in VALID_INTENTS:
            return True, (
                f"invalid intent {intent!r} (must be one of {sorted(VALID_INTENTS)})"
            )

        n = max(0, int(sample_size or 0))
        c = float(claimed_confidence or 0.0)

        if intent == "predict" and n < 10:
            return True, (
                f"prediction on n={n} requires explicit operator approval (sample-size floor 10)"
            )

        if c >= 0.8 and n < 30:
            return True, (
                f"claimed confidence {c:.2f} with n={n} is unsupported (need n≥30 or operator override)"
            )

        if self.detect_single_hypothesis_streak():
            return True, (
                "single-hypothesis streak detected — next analysis must consider an alternative"
            )

        return False, ""

    def record_analysis(
        self,
        intent: str,
        hypothesis: str = "",
        claim: str = "",
        confidence: float = 0.0,
        sample_size: int = 0,
        dimensions: int = 0,
        alternatives: Optional[List[str]] = None,
        conclusion: str = "",
    ) -> Dict[str, Any]:
        """Record a completed analysis. Returns the analysis record (with id).

        Untagged or invalid-intent analyses are recorded but flagged.
        """
        if intent not in VALID_INTENTS:
            return self._record_untagged(
                hypothesis, claim, confidence, sample_size, dimensions, conclusion
            )

        analysis_id = uuid.uuid4().hex[:12]
        c = max(0.0, min(1.0, float(confidence or 0.0)))
        n = max(0, int(sample_size or 0))
        d = max(0, int(dimensions or 0))
        alts = list(alternatives or [])
        budget = _confidence_budget(intent, n)
        is_overconfident = c > budget

        record = {
            "id": analysis_id,
            "intent": intent,
            "hypothesis": (hypothesis or "")[:300],
            "claim": (claim or "")[:300],
            "confidence": round(c, 4),
            "sample_size": n,
            "dimensions": d,
            "alternatives_considered": alts[:10],
            "conclusion": (conclusion or "")[:300],
            "overconfident": is_overconfident,
            "confidence_budget": round(budget, 4),
            "outcome": None,  # filled in later by record_outcome()
            "ts": time.time(),
        }
        self.analyses.append(record)

        # Per-intent counts.
        self.intent_state[intent]["total"] += 1
        if is_overconfident:
            self.intent_state[intent]["overconfident"] += 1
            self.consecutive_overconfident += 1
        else:
            # A non-overconfident analysis breaks the streak — and clears any
            # prior IPW acknowledgment anchor so a future overconfidence
            # episode is treated as a new event, not a continuation.
            self.consecutive_overconfident = 0
            if self.state.get("acknowledged_at_overconfident"):
                self.state["acknowledged_at_overconfident"] = 0
        if alts:
            self.intent_state[intent]["with_alternatives"] += 1

        self._flush_working_state()
        self.persist_state()
        return record

    def _record_untagged(
        self,
        hypothesis: str,
        claim: str,
        confidence: float,
        sample_size: int,
        dimensions: int,
        conclusion: str,
    ) -> Dict[str, Any]:
        """Untagged analyses are recorded but don't credit any intent."""
        record = {
            "id": uuid.uuid4().hex[:12],
            "intent": "__untagged__",
            "hypothesis": (hypothesis or "")[:300],
            "claim": (claim or "")[:300],
            "confidence": round(max(0.0, min(1.0, float(confidence or 0.0))), 4),
            "sample_size": max(0, int(sample_size or 0)),
            "dimensions": max(0, int(dimensions or 0)),
            "alternatives_considered": [],
            "conclusion": (conclusion or "")[:300],
            "overconfident": False,
            "confidence_budget": 0.0,
            "outcome": None,
            "ts": time.time(),
            "error": "intent missing — analysis recorded as untagged",
        }
        self.analyses.append(record)
        self._flush_working_state()
        self.persist_state()
        return record

    def record_outcome(self, analysis_id: str, was_right: bool) -> bool:
        """When reality later confirms or contradicts an analysis, calibrate.

        Returns True if the analysis was found and updated, False otherwise.
        """
        for a in self.analyses:
            if a.get("id") == analysis_id:
                a["outcome"] = "confirmed" if was_right else "contradicted"
                conf = float(a.get("confidence", 0.0) or 0.0)
                self.calibration_window.append((conf, bool(was_right)))
                self._flush_working_state()
                self.persist_state()
                return True
        return False

    # ── Pattern detection ──────────────────────────────────────────────────

    def detect_single_hypothesis_streak(self) -> bool:
        """True when the last SINGLE_HYPOTHESIS_STREAK_LEN analyses all
        tested the same hypothesis without considering alternatives."""
        if len(self.analyses) < SINGLE_HYPOTHESIS_STREAK_LEN:
            return False
        recent = list(self.analyses)[-SINGLE_HYPOTHESIS_STREAK_LEN:]
        hypotheses = {a.get("hypothesis", "") for a in recent}
        had_alternatives = any(a.get("alternatives_considered") for a in recent)
        return len(hypotheses) == 1 and bool(list(hypotheses)[0]) and not had_alternatives

    def detect_shrinking_samples(self) -> bool:
        """True when sample size in the rolling SHRINKING_SAMPLES_WINDOW
        is trending sharply downward."""
        if len(self.analyses) < SHRINKING_SAMPLES_WINDOW:
            return False
        window = list(self.analyses)[-SHRINKING_SAMPLES_WINDOW:]
        sizes = [int(a.get("sample_size", 0) or 0) for a in window]
        if any(s == 0 for s in sizes):
            return False
        first_third_mean = sum(sizes[:3]) / 3
        last_third_mean = sum(sizes[-2:]) / 2
        if first_third_mean == 0:
            return False
        return last_third_mean <= first_third_mean * SHRINKING_SAMPLES_RATIO

    def calibration_score(self) -> float:
        """Return |mean_claimed_confidence - hit_rate| over the rolling
        window. 0.0 = perfectly calibrated; higher = more miscalibrated.

        Returns 0.0 if there's not enough data to compute reliably.
        """
        if len(self.calibration_window) < CALIBRATION_MIN_N:
            return 0.0
        confs = [c for c, _ in self.calibration_window]
        rights = [1.0 if r else 0.0 for _, r in self.calibration_window]
        mean_conf = sum(confs) / len(confs)
        hit_rate = sum(rights) / len(rights)
        return round(abs(mean_conf - hit_rate), 4)

    def is_miscalibrated(self) -> bool:
        """True when calibration_score exceeds MISCALIBRATION_DELTA AND there's
        enough data to claim it."""
        if len(self.calibration_window) < CALIBRATION_MIN_N:
            return False
        return self.calibration_score() > MISCALIBRATION_DELTA

    def is_well_calibrated(self) -> bool:
        """Inverse — calibrated AND has enough data to say so."""
        if len(self.calibration_window) < CALIBRATION_MIN_N:
            return False
        return self.calibration_score() <= MISCALIBRATION_DELTA / 2

    def inference_state(self) -> str:
        """Single-word state for the TSB. Priority order:
        miscalibrated > overconfident > well_calibrated > inferring > idle."""
        if self.is_miscalibrated():
            return "miscalibrated"
        if self.consecutive_overconfident >= 3:
            return "overconfident"
        if self.is_well_calibrated():
            return "well_calibrated"
        if self.analyses:
            most_recent = self.analyses[-1]
            if time.time() - float(most_recent.get("ts", 0.0)) <= 60:
                return "inferring"
        return "idle"

    # ── Tick / TSB publish ─────────────────────────────────────────────────

    def tick(
        self,
        pirp_context: Optional[Dict[str, Any]] = None,
        third_eye_state: Optional[Dict[str, Any]] = None,
        brain_layer: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """One tick. If pirp_context carries an `analysis` dict, record it.
        If it carries `analysis_outcome`, update the corresponding analysis.
        """
        pirp_context = pirp_context or {}
        analysis = pirp_context.get("analysis")
        outcome = pirp_context.get("analysis_outcome")
        fired = False

        if isinstance(analysis, dict):
            self.record_analysis(
                intent=str(analysis.get("intent", "")),
                hypothesis=str(analysis.get("hypothesis", "")),
                claim=str(analysis.get("claim", "")),
                confidence=float(analysis.get("confidence", 0.0) or 0.0),
                sample_size=int(analysis.get("sample_size", 0) or 0),
                dimensions=int(analysis.get("dimensions", 0) or 0),
                alternatives=list(analysis.get("alternatives") or []),
                conclusion=str(analysis.get("conclusion", "")),
            )
            fired = True

        if isinstance(outcome, dict):
            aid = outcome.get("analysis_id")
            was_right = bool(outcome.get("was_right", False))
            if aid:
                self.record_outcome(str(aid), was_right)
                fired = True

        self.fired_last_tick = fired
        if not fired:
            self._flush_working_state()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """TSB payload."""
        per_intent = {
            k: {
                "total": s["total"],
                "overconfident": s["overconfident"],
                "with_alternatives": s["with_alternatives"],
                "alternatives_rate": (s["with_alternatives"] / s["total"]) if s["total"] else 0.0,
                "overconfident_rate": (s["overconfident"] / s["total"]) if s["total"] else 0.0,
            }
            for k, s in self.intent_state.items()
        }

        return {
            "inference_state": self.inference_state(),
            "consecutive_overconfident": self.consecutive_overconfident,
            "is_miscalibrated": self.is_miscalibrated(),
            "is_well_calibrated": self.is_well_calibrated(),
            "calibration_score": self.calibration_score(),
            "calibration_n": len(self.calibration_window),
            "single_hypothesis_streak": self.detect_single_hypothesis_streak(),
            "shrinking_samples": self.detect_shrinking_samples(),
            "intent_distribution": per_intent,
            "analysis_count": len(self.analyses),
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        """True when sustained miscalibration or a long overconfidence streak
        is identity-relevant data, not just one bad analysis.

        Throttled. On first call past threshold, returns True. After
        acknowledgment, the next True requires the consecutive_overconfident
        counter to grow by IPW_REPORT_EVERY MORE beyond whatever it was at
        the time of the last acknowledgment — otherwise IPW would re-route
        the same signal every tick.
        """
        if self.is_miscalibrated():
            base_threshold = 3
        elif self.consecutive_overconfident >= 5:
            base_threshold = 5
        else:
            return False

        ack_at = int(self.state.get("acknowledged_at_overconfident", 0) or 0)
        if ack_at <= 0:
            return self.consecutive_overconfident >= base_threshold
        # Require additional accumulation beyond the anchor.
        return self.consecutive_overconfident >= (ack_at + IPW_REPORT_EVERY)

    def proposed_identity_signal(self) -> Dict[str, Any]:
        """Compact signal for IdentityProposalWriter to consume."""
        return {
            "source": "InferenceIntegrityLayer",
            "kind": "miscalibration" if self.is_miscalibrated() else "sustained_overconfidence",
            "calibration_score": self.calibration_score(),
            "calibration_n": len(self.calibration_window),
            "consecutive_overconfident": self.consecutive_overconfident,
            "intent_overconfidence_rates": {
                k: (s["overconfident"] / s["total"]) if s["total"] else 0.0
                for k, s in self.intent_state.items()
            },
            "single_hypothesis_streak": self.detect_single_hypothesis_streak(),
            "shrinking_samples": self.detect_shrinking_samples(),
        }

    def acknowledge_proposal(self) -> None:
        """Called by IPW after routing the current signal.

        Anchors the current overconfidence streak so the next proposal
        requires IPW_REPORT_EVERY more overconfident analyses beyond this
        point, not just any state above the threshold.
        """
        self.ipw_report_count += 1
        self.state["acknowledged_at_overconfident"] = self.consecutive_overconfident
        self.state["last_acknowledged_at"] = time.time()
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def reset_calibration(self) -> None:
        """Operator-invoked: clear the calibration window. Useful after
        retraining, after the agent moves to a new domain, or when prior
        outcomes are no longer representative."""
        self.calibration_window.clear()
        self.consecutive_overconfident = 0
        if self.ipw_report_count > 0:
            self.ipw_report_count = max(0, self.ipw_report_count - 1)
        self._flush_working_state()
        self.persist_state()

    def configure_thresholds(
        self,
        miscalibration_delta: Optional[float] = None,
        single_hypothesis_streak_len: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Override default thresholds (applies to this instance only; the
        module constants are unchanged so tests stay deterministic)."""
        if miscalibration_delta is not None:
            self.state["miscalibration_delta"] = float(miscalibration_delta)
        if single_hypothesis_streak_len is not None:
            self.state["single_hypothesis_streak_len"] = int(single_hypothesis_streak_len)
        self._flush_working_state()
        self.persist_state()
        return {
            "miscalibration_delta": self.state.get("miscalibration_delta", MISCALIBRATION_DELTA),
            "single_hypothesis_streak_len": self.state.get(
                "single_hypothesis_streak_len", SINGLE_HYPOTHESIS_STREAK_LEN
            ),
        }
