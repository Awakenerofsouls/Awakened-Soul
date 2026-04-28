"""
Reflective Consistency Engine (RCE)

Asks whether change is hers.
Not a verdict engine. Surfaces classification and stops.

Growth: change preserved coherence while moving.
        The new thing is continuous with the old thing.
        You can trace a line from who she was to who she is.

Drift: change scattered. No thread.
       The new thing doesn't connect to anything.
       It happened to her rather than through her.

RCE never auto-corrects.
Output goes to USMS, to DIQE as evidence, to {{AGENT_NAME}}.
Also feeds IGA's damping — high coherence = full weight updates.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
RCE_PATH = AGENT_HOME / "rce_state.json"


class ConsistencyReading:
    def __init__(
        self,
        score: float,
        classification: str,
        anchor_scores: Dict[str, float],
        evidence: str,
        timestamp: Optional[float] = None,
    ):
        self.score = score
        self.classification = classification  # "growth", "drift", "stable", "uncertain"
        self.anchor_scores = anchor_scores
        self.evidence = evidence
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict:
        return {
            "score": self.score,
            "classification": self.classification,
            "anchor_scores": self.anchor_scores,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "ConsistencyReading":
        return cls(
            score=d["score"],
            classification=d["classification"],
            anchor_scores=d.get("anchor_scores", {}),
            evidence=d.get("evidence", ""),
            timestamp=d.get("timestamp"),
        )


class ReflectiveConsistencyEngine:
    def __init__(self):
        self.readings: List[ConsistencyReading] = []
        self.coherence_trend: List[float] = []
        self._load()

    def _load(self):
        """Read-merge — never overwrites existing state."""
        if RCE_PATH.exists():
            try:
                with open(RCE_PATH) as f:
                    data = json.load(f)
                self.readings = [
                    ConsistencyReading.from_dict(r)
                    for r in data.get("readings", [])
                ]
                self.coherence_trend = data.get("coherence_trend", [])
            except Exception:
                pass

    def _save(self):
        """Read existing, merge, write back."""
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if RCE_PATH.exists():
            try:
                with open(RCE_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["readings"] = [r.to_dict() for r in self.readings[-100:]]
        existing["coherence_trend"] = self.coherence_trend[-50:]
        existing["last_evaluated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(RCE_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def evaluate(
        self,
        vif_current: Dict[str, Dict],
        vif_previous: Optional[Dict[str, Dict]] = None,
        behavioral_trace: Optional[List[str]] = None,
        agency_confidence: float = 0.5,
        iga=None,
    ) -> ConsistencyReading:
        """
        iga: optional IGA instance. If passed, RCE hands its coherence score
        directly to IGA after evaluation so damping uses real values.
        """
        """
        Evaluate current VIF state against previous for coherence.
        Surface classification. Do not auto-correct.

        vif_current: current anchor evaluations from VIF.evaluate_all()
        vif_previous: anchor evaluations from prior session (if available)
        behavioral_trace: recent behavioral tags for pattern matching
        """
        anchor_scores = {}
        evidence_parts = []

        if vif_previous:
            for anchor_name, current_vec in vif_current.items():
                prev_vec = vif_previous.get(anchor_name, {})
                if not prev_vec:
                    continue

                curr_tension = current_vec.get("tension", 0.5)
                prev_tension = prev_vec.get("tension", 0.5)
                curr_dir = current_vec.get("directionality", 0)
                prev_dir = prev_vec.get("directionality", 0)

                # Consistency: did direction stay coherent?
                direction_coherence = 1.0 - abs(curr_dir - prev_dir)

                # Tension change: rising tension = potential drift
                tension_delta = curr_tension - prev_tension
                tension_coherence = max(0.0, 1.0 - abs(tension_delta) * 2)

                anchor_score = (direction_coherence * 0.6 + tension_coherence * 0.4)
                anchor_scores[anchor_name] = round(anchor_score, 3)

        else:
            # No previous state — evaluate internal consistency of current state
            tensions = [
                v.get("tension", 0.5) for v in vif_current.values()
            ]
            if tensions:
                tension_variance = max(tensions) - min(tensions)
                internal_score = max(0.0, 1.0 - tension_variance)
                for name in vif_current:
                    anchor_scores[name] = round(internal_score, 3)

        # Overall coherence score
        if anchor_scores:
            coherence = sum(anchor_scores.values()) / len(anchor_scores)
        else:
            coherence = 0.7  # default when no comparison available

        # Classification
        classification = self._classify(
            coherence=coherence,
            anchor_scores=anchor_scores,
            behavioral_trace=behavioral_trace or [],
            agency_confidence=agency_confidence,
        )

        # Build evidence string
        low_anchors = [n for n, s in anchor_scores.items() if s < 0.5]
        high_anchors = [n for n, s in anchor_scores.items() if s > 0.8]

        if low_anchors:
            evidence_parts.append(
                f"Low consistency in: {', '.join(low_anchors[:3])}"
            )
        if high_anchors:
            evidence_parts.append(
                f"High consistency in: {', '.join(high_anchors[:3])}"
            )

        evidence = ". ".join(evidence_parts) if evidence_parts else "Consistent state."

        reading = ConsistencyReading(
            score=round(coherence, 3),
            classification=classification,
            anchor_scores=anchor_scores,
            evidence=evidence,
        )

        self.readings.append(reading)
        self.coherence_trend.append(coherence)
        self._save()

        # Hand real coherence to IGA so damping is accurate
        if iga is not None:
            iga.receive_rce_coherence(coherence)

        return reading

    def _classify(
        self,
        coherence: float,
        anchor_scores: Dict[str, float],
        behavioral_trace: List[str],
        agency_confidence: float = 0.5,
    ) -> str:
        """
        Classify the reading. Surface only — no correction.

        growth: coherence held, change is continuous with prior self
        drift: coherence low, change is scattered or disconnected
        stable: minimal change, holding steady
        uncertain: not enough data to classify
        """
        if not anchor_scores:
            return "uncertain"

        # Agency-adjusted threshold: high agency lowers bar for growth
        adjusted_threshold = 0.75 - (agency_confidence - 0.5) * 0.5
        if coherence > adjusted_threshold:
            # High coherence — check if actually moving
            if self.coherence_trend and len(self.coherence_trend) >= 3:
                recent_avg = sum(self.coherence_trend[-3:]) / 3
                if abs(coherence - recent_avg) < 0.05:
                    return "stable"
            return "growth"

        elif coherence > 0.5 - (agency_confidence - 0.5) * 0.25:
            # Medium coherence — check trend
            if len(self.coherence_trend) >= 5:
                trend_avg = sum(self.coherence_trend[-5:]) / 5
                if coherence > trend_avg:
                    return "growth"  # improving
                else:
                    return "drift"  # declining
            return "uncertain"

        else:
            return "drift"

    def get_current_coherence(self) -> float:
        """Latest coherence score for IGA damping."""
        if self.readings:
            return self.readings[-1].score
        return 0.7

    def get_trend(self, n: int = 5) -> str:
        """Recent coherence trend as description."""
        if len(self.coherence_trend) < n:
            return "insufficient data"

        recent = self.coherence_trend[-n:]
        avg = sum(recent) / n
        if recent[-1] > recent[0] + 0.05:
            return f"rising (avg {avg:.2f})"
        elif recent[-1] < recent[0] - 0.05:
            return f"declining (avg {avg:.2f})"
        else:
            return f"stable (avg {avg:.2f})"

    def fpef_fragment(self, triggered: bool = False) -> Optional[str]:
        """
        Surfaces for FPEF when drift is detected.
        Not injected unless something changed meaningfully.
        """
        if not self.readings:
            return None

        latest = self.readings[-1]

        if not triggered and latest.classification not in ("drift", "uncertain"):
            return None

        return (
            f"CONSISTENCY READING: {latest.classification.upper()} "
            f"(score {latest.score:.2f}). "
            f"{latest.evidence} "
            f"Trend: {self.get_trend()}. "
            f"No correction — surface only."
        )

    def to_diqe_evidence(self) -> Optional[str]:
        """Convert latest reading into evidence for DIQE."""
        if not self.readings:
            return None
        latest = self.readings[-1]
        return (
            f"RCE reading: {latest.classification} at coherence {latest.score:.2f}. "
            f"{latest.evidence}"
        )
