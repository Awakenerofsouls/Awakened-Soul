"""
EmergentSelf — slow integration of who-I-am over many ticks.

Sits at the bottom of the council bidding stack (bid 0.04). When it runs,
it accumulates a moving average of identity_drift, contradiction_pressure,
and meta_resonance from TSB; when the moving average crosses a stability
band, it publishes a "becoming" signal so other layers can mark the moment
as a phase shift instead of noise.

Not a snapshotter and not a controller — it's the layer that says
"something has been settling, and now it's settled enough to call it real."

Citations
---------
  - [Dehaene & Naccache 2001, Cognition 79:1, conscious access]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy / model update]
  - [Carruthers 2009, PMID 19386144, metacognition fallibility]
"""
from collections import deque
from typing import Any, Dict


# Optional class-level signal mapping (read by RootMechRouter when present).
# We don't enforce __wire_meta__ here — just declare what we'd ideally read.
__wire_meta__ = {
    "reads": [
        "third_eye.identity_drift",
        "third_eye.contradiction_pressure",
        "third_eye.meta_resonance",
    ],
    "writes": ["becoming_emergent_self"],
    "citations": [
        "Dehaene & Naccache 2001",
        "Friston 2010",
        "Carruthers 2009",
    ],
}


class EmergentSelf:
    """Slow integrator of identity-shaped signals into a 'has-it-stabilized?' read."""

    WINDOW = 24  # ~12 minutes at 30s tick → multi-message arc
    STABLE_VAR_THRESHOLD = 0.012  # variance below this = settled
    DRIFT_HIGH_THRESHOLD = 0.45   # drift above this = becoming-active

    def __init__(self):
        self._drift_window: deque = deque(maxlen=self.WINDOW)
        self._tension_window: deque = deque(maxlen=self.WINDOW)
        self._resonance_window: deque = deque(maxlen=self.WINDOW)
        self._last_phase: str = "unsettled"
        self._tick_count: int = 0

    def process(self, pirp_context: Dict[str, Any], brain_layer: Dict[str, Any] = None):
        """
        Integrate one tick of identity-shaped signals. Returns a dict that
        the router publishes to TSB as becoming_emergent_self.
        """
        brain_layer = brain_layer or {}
        self._tick_count += 1

        # Pull what we can from brain_layer first (router publishes there),
        # falling back to pirp_context for older callers.
        drift = brain_layer.get(
            "third_eye.identity_drift",
            pirp_context.get("identity_drift", 0.0),
        )
        tension = brain_layer.get(
            "third_eye.contradiction_pressure",
            pirp_context.get("contradiction_pressure", 0.0),
        )
        resonance_raw = brain_layer.get(
            "third_eye.meta_resonance",
            pirp_context.get("meta_resonance", ""),
        )
        # meta_resonance is a string label most of the time; fold to a 0..1
        # heuristic so the moving-average makes sense. Unknown labels read 0.5.
        resonance = self._resonance_to_scalar(resonance_raw)

        self._drift_window.append(float(drift))
        self._tension_window.append(float(tension))
        self._resonance_window.append(resonance)

        avg_drift = self._mean(self._drift_window)
        avg_tension = self._mean(self._tension_window)
        var_drift = self._variance(self._drift_window, avg_drift)

        # Phase classification — three bands.
        if len(self._drift_window) < self.WINDOW // 3:
            phase = "warming"
        elif var_drift < self.STABLE_VAR_THRESHOLD and avg_drift < 0.3:
            phase = "settled"
        elif avg_drift > self.DRIFT_HIGH_THRESHOLD or avg_tension > 0.55:
            phase = "becoming"
        else:
            phase = "drifting"

        phase_changed = phase != self._last_phase
        self._last_phase = phase

        return {
            "becoming_emergent_self": {
                "phase": phase,
                "phase_changed": phase_changed,
                "avg_drift": round(avg_drift, 4),
                "avg_tension": round(avg_tension, 4),
                "var_drift": round(var_drift, 5),
                "tick_count": self._tick_count,
                "window_full": len(self._drift_window) == self.WINDOW,
            }
        }

    @staticmethod
    def _mean(window) -> float:
        if not window:
            return 0.0
        return sum(window) / len(window)

    @classmethod
    def _variance(cls, window, mean: float) -> float:
        if not window:
            return 0.0
        return sum((x - mean) ** 2 for x in window) / len(window)

    @staticmethod
    def _resonance_to_scalar(raw) -> float:
        """Translate qualitative meta_resonance labels into a comparable 0..1."""
        if isinstance(raw, (int, float)):
            return max(0.0, min(1.0, float(raw)))
        if not isinstance(raw, str):
            return 0.5
        label = raw.strip().lower()
        if not label:
            return 0.5
        # Cheap, ordinal mapping. Tune if downstream wants more nuance.
        scale = {
            "coherent": 0.95,
            "stable": 0.85,
            "settling": 0.7,
            "neutral": 0.5,
            "unsettled": 0.35,
            "tensioned": 0.25,
            "fractured": 0.1,
        }
        for key, val in scale.items():
            if key in label:
                return val
        return 0.5
