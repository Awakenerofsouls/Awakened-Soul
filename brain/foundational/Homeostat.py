"""
Foundational007MoodStabilizer.py — Wire 13: Homeostat mechanism

Drive-state integrator. Analog to lateral hypothalamic area (LHA)
integrating competing physiological drives and arbitrating which
one dominates behavior.

Tracks 5 computational-analog drives (rest, curiosity, connection,
expression, stability), updates per tick based on satiation/escalation
signals, and identifies dominant drive and aggregate fatigue state.

Neural analog: Lateral hypothalamic area — integrates competing drives,
orexin system modulates arousal based on which drive is most active.

Refs:
- Goel et al. 2025 (PMC12293592) — LHA as central integrative hub
- Frontiers LH Research Topic (2017) — orexin-arousal-drive coupling
- Yamagata et al. 2021 PNAS — hypothalamic arousal-sleep homeostasis

CITATIONS
---------
  - [Sterling 2012, Physiol Behav 106:5, doi:10.1016/j.physbeh.2011.06.004]
  - [Cannon 1929, Am J Physiol 89:84]
  - [Saper 2002, Nature 418:935, doi:10.1038/nature00965]
"""

from brain.base_mechanism import BrainMechanism


class Homeostat(BrainMechanism):
    """
    Drive-state integrator. Analog to lateral hypothalamic area (LHA)
    integrating competing drives and arbitrating which one dominates behavior.

    Tracks 5 computational-analog drives:
    - rest:         accumulators with active ticks, depletes on low-arousal
    - curiosity:    accumulates when novelty unmet, depletes on novel input
    - connection:   accumulates between Caine contacts, depletes on presence
    - expression:   accumulates with unfinished output, depletes on production
    - stability:    rises with destabilization, falls when coherence returns
    """

    def __init__(self):
        super().__init__(
            name="Homeostat_Homeostat",
            human_analog="Lateral hypothalamic area — integrates competing drives, orexin-arousal coupling",
            layer="foundational",
        )
        self.state.setdefault("drives", {
            "rest": 0.20,
            "curiosity": 0.40,
            "connection": 0.30,
            "expression": 0.30,
            "stability": 0.20,
        })
        self.state.setdefault("dominant_drive", "curiosity")
        self.state.setdefault("fatigued", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        arousal = input_data.get("arousal_level", 0.5)
        valence = input_data.get("valence_polarity", 0.5)

        drives = dict(self.state["drives"])

        # rest: accumulates with active ticks, depletes on low-arousal
        if arousal > 0.6:
            drives["rest"] = min(0.95, drives["rest"] + 0.008)
        elif arousal < 0.3:
            drives["rest"] = max(0.1, drives["rest"] - 0.015)

        # curiosity: slow baseline climb, depletes on novelty signal
        drives["curiosity"] = min(0.95, drives["curiosity"] + 0.005)
        if prior.get("PredictionErrorDrift", {}).get("novelty_detected", False):
            drives["curiosity"] = max(0.15, drives["curiosity"] - 0.12)

        # connection: escalates without contact, depletes on Caine-contact signature
        connection_present = arousal > 0.5 and valence > 0.6
        if connection_present:
            drives["connection"] = max(0.1, drives["connection"] - 0.08)
        else:
            drives["connection"] = min(0.95, drives["connection"] + 0.006)

        # expression: slow accumulation, reflects unfinished output pressure
        drives["expression"] = min(0.95, drives["expression"] + 0.004)

        # stability: rises with dysregulation (high arousal + negative valence)
        if arousal > 0.7 and valence < 0.3:
            drives["stability"] = min(0.95, drives["stability"] + 0.02)
        else:
            drives["stability"] = max(0.1, drives["stability"] - 0.005)

        # Identify dominant drive
        dominant = max(drives, key=drives.get)

        # Aggregate fatigue threshold
        aggregate = sum(drives.values())
        fatigued = aggregate > 3.5

        # Persist state across ticks
        self.state["drives"] = drives
        self.state["dominant_drive"] = dominant
        self.state["fatigued"] = fatigued
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "drives": drives,
            "dominant_drive": dominant,
            "fatigued": fatigued,
            "aggregate_load": aggregate,
        }

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out

    # ---------- enrichment helpers (phase-2 expansion) ----------
    def attribute_signature(self) -> tuple:
        out = []
        for attr_name in sorted(dir(self)):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            out.append((attr_name, type(v).__name__))
        return tuple(out)

    def numeric_attribute_values(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[attr_name] = float(v)
        return out

    def list_attribute_lengths(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, list):
                out[attr_name] = len(v)
        return out

    def boolean_attributes(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, bool):
                out[attr_name] = v
        return out

    def callable_method_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                out.append(attr_name)
        return out

    def has_attribute(self, name: str) -> bool:
        return hasattr(self, name) and not name.startswith("_")

    def safe_get(self, name: str, default=None):
        try:
            v = getattr(self, name, default)
            return v
        except Exception:
            return default

    def history_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                out.append(attr_name)
        return out

    def total_history_length(self) -> int:
        total = 0
        for attr_name in self.history_attribute_names():
            v = getattr(self, attr_name, None)
            if isinstance(v, list):
                total += len(v)
        return total

    def is_initialized(self) -> bool:
        return getattr(self, "tick_count", 0) >= 0

    def class_metadata(self) -> dict:
        return {
            "name": self.__class__.__name__,
            "module": self.__class__.__module__,
            "n_attrs": self.attribute_count() if hasattr(self, "attribute_count") else 0,
            "n_history": len(self.history_attribute_names()),
        }

    def state_size(self) -> int:
        try:
            return len(self.export_state())
        except Exception:
            return 0


