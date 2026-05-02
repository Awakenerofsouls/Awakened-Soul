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
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class Homeostat(BrainMechanism):
    """
    Drive-state integrator. Analog to lateral hypothalamic area (LHA)
    integrating competing drives and arbitrating which one dominates behavior.

    Tracks 5 computational-analog drives:
    - rest:         accumulators with active ticks, depletes on low-arousal
    - curiosity:    accumulates when novelty unmet, depletes on novel input
    - connection:   accumulates between the operator contacts, depletes on presence
    - expression:   accumulates with unfinished output, depletes on production
    - stability:    rises with destabilization, falls when coherence returns
    """

    def __init__(self):
        super().__init__(
            name="Homeostat",
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

        # connection: escalates without contact, depletes on the operator-contact signature
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

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

