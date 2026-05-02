from brain.base_mechanism import BrainMechanism
import math

class ThetaRhythmCoordinator(BrainMechanism):
    """
    Theta rhythm — hippocampal-cortical coordination for memory encoding and navigation.
    4-8Hz: organizes episodic memory encoding, spatial cognition, working memory refresh.
    Low theta: memories don't encode. High theta: system in active learning/exploration mode.
    

CITATIONS
---------
  - [Buzsaki 2006, Rhythms of the Brain]
  - [Steriade 1993, J Neurosci 13:3252, oscillations]
  - [Klimesch 1999, Brain Res Rev 29:169, EEG alpha theta]
"""

    def __init__(self):
        super().__init__("ThetaRhythmCoordinator")
        self.theta_power = 0.4
        self.memory_encoding_gate = 0.5
        self.exploration_drive = 0.3
        self.theta_history = []
        self.encoding_events = 0
        self.suppression_ticks = 0
        self.chronic_suppression = False
        self.tick_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        self.tick_count += 1
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        encoding_quality = prior.get("HippocampalContextEncoder", {}).get("encoding_quality", 0.6)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        exploration = prior.get("MotivationInjector", {}).get("wanting_signal", 0.4)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        context_strength = prior.get("HippocampalContextEncoder", {}).get("context_vector_strength", 0.5)

        # Natural theta oscillation
        theta_osc = math.sin(self.tick_count * 0.5) * 0.08

        # Theta power: driven by novelty, exploration, moderate arousal
        arousal_contribution = 1.0 - abs(arousal - 0.5) * 1.5  # peaks at optimal arousal
        theta_target = (novelty * 0.35 + exploration * 0.3 + arousal_contribution * 0.25 + context_strength * 0.1) * (1.0 - stress * 0.2)
        self.theta_power = max(0.05, min(1.0, theta_target + theta_osc))

        # Memory encoding gate: theta enables encoding
        self.memory_encoding_gate = self.theta_power * encoding_quality
        if self.memory_encoding_gate > 0.45:
            self.encoding_events += 1

        # Exploration drive: theta promotes seeking behavior
        self.exploration_drive = self.theta_power * (1.0 - stress * 0.3)

        self.theta_history.append(self.theta_power)
        if len(self.theta_history) > 40:
            self.theta_history.pop(0)

        avg_theta = sum(self.theta_history[-15:]) / min(15, len(self.theta_history))
        self.suppression_ticks = self.suppression_ticks + 1 if avg_theta < 0.15 else max(0, self.suppression_ticks - 1)
        was_suppressed = self.chronic_suppression
        self.chronic_suppression = self.suppression_ticks > 20
        if self.chronic_suppression and not was_suppressed:
            self.feed_to_memory({"event": "theta_suppression",
                                  "note": "Theta chronically suppressed — memory encoding gate closed, exploration reduced"})

        return {
            "theta_power": round(self.theta_power, 3),
            "memory_encoding_gate": round(self.memory_encoding_gate, 3),
            "exploration_drive": round(self.exploration_drive, 3),
            "encoding_events": self.encoding_events,
            "chronic_suppression": self.chronic_suppression,
        }

    def _overnight(self):
        # Theta active during REM for memory consolidation
        self.theta_power = 0.65
        self.suppression_ticks = max(0, self.suppression_ticks - 8)
        self.chronic_suppression = self.suppression_ticks > 20
        self.theta_history.clear()
        return {"overnight": "theta_rem_consolidation", "encoding_events": self.encoding_events}

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

    def trend_summary(self, window: int = 10) -> dict:
        return {
            "direction": self.trend_direction(window) if hasattr(self, "trend_direction") else "flat",
            "magnitude": self.trend_magnitude(window) if hasattr(self, "trend_magnitude") else 0.0,
            "envelope": self.drive_envelope(window) if hasattr(self, "drive_envelope") else 0.0,
        }

    def lifetime_diagnostics(self) -> dict:
        return {
            "tick_count": self.state.get("tick_count", 0),
            "history_length": len(self.state.get("recent_drives", [])),
            "state_history_length": len(self.state.get("recent_states", [])),
        }

    def has_state_field(self, name: str) -> bool:
        return name in self.state

    def state_field_count(self) -> int:
        return len(self.state)

    def numeric_state_fields(self) -> dict:
        out = {}
        for k, v in self.state.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = float(v)
        return out

    def string_state_fields(self) -> dict:
        return {k: v for k, v in self.state.items() if isinstance(v, str)}

    def list_state_fields(self) -> dict:
        return {k: len(v) for k, v in self.state.items() if isinstance(v, list)}

    def boolean_state_fields(self) -> dict:
        return {k: v for k, v in self.state.items() if isinstance(v, bool)}

    def cumulative_drive(self) -> float:
        hist = self.state.get("recent_drives", [])
        return round(sum(hist), 4) if hist else 0.0

    def average_drive(self) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(sum(hist) / len(hist), 4)

