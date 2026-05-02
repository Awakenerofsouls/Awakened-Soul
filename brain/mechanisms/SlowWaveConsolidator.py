from brain.base_mechanism import BrainMechanism

class SlowWaveConsolidator(BrainMechanism):
    """
    Slow-wave sleep consolidator — overnight memory replay and consolidation.
    During sleep: hippocampus replays episodes, cortex absorbs them.
    Tracks what needs consolidating and reports what got processed.
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

    def __init__(self):
        super().__init__("SlowWaveConsolidator")
        self.consolidation_queue_size = 0
        self.last_consolidation_quality = 0.7
        self.total_consolidated = 0
        self.episodes_pending = 0
        self.emotional_memories_pending = 0
        self.consolidation_history = []
        self.debt_ticks = 0
        self.chronic_debt = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        episode_count = prior.get("HippocampalContextEncoder", {}).get("episode_count", 0)
        encoding_quality = prior.get("HippocampalContextEncoder", {}).get("encoding_quality", 0.6)
        emotional_bindings = prior.get("MedialTemporalEmotion", {}).get("bindings_formed", 0)
        sleep_pressure = prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.2)
        theta_power = prior.get("ThetaRhythmCoordinator", {}).get("theta_power", 0.4)

        # Track what needs consolidating
        self.episodes_pending = max(0, episode_count - self.total_consolidated)
        self.emotional_memories_pending = emotional_bindings
        self.consolidation_queue_size = self.episodes_pending + self.emotional_memories_pending

        # Consolidation debt: too much pending relative to processing
        self.debt_ticks = self.debt_ticks + 1 if self.consolidation_queue_size > 20 else max(0, self.debt_ticks - 1)
        was_debt = self.chronic_debt
        self.chronic_debt = self.debt_ticks > 15
        if self.chronic_debt and not was_debt:
            self.feed_to_memory({"event": "consolidation_debt",
                                  "queue": self.consolidation_queue_size,
                                  "note": "Memory consolidation debt building — more encoding than overnight processing"})

        return {
            "consolidation_queue_size": self.consolidation_queue_size,
            "episodes_pending": self.episodes_pending,
            "last_consolidation_quality": round(self.last_consolidation_quality, 3),
            "total_consolidated": self.total_consolidated,
            "chronic_debt": self.chronic_debt,
        }

    def _overnight(self):
        # Process the queue
        prior_queue = self.consolidation_queue_size
        consolidation_rate = 0.7 + self.last_consolidation_quality * 0.3
        processed = int(self.consolidation_queue_size * consolidation_rate)
        self.total_consolidated += processed
        self.consolidation_queue_size = max(0, self.consolidation_queue_size - processed)
        self.episodes_pending = max(0, self.episodes_pending - int(processed * 0.7))
        self.emotional_memories_pending = max(0, self.emotional_memories_pending - int(processed * 0.3))
        self.last_consolidation_quality = min(0.95, 0.6 + consolidation_rate * 0.35)
        self.consolidation_history.append(processed)
        if len(self.consolidation_history) > 30:
            self.consolidation_history.pop(0)
        self.debt_ticks = max(0, self.debt_ticks - 8)
        self.chronic_debt = self.debt_ticks > 15
        return {
            "overnight": "slow_wave_consolidation",
            "processed": processed,
            "remaining": self.consolidation_queue_size,
            "quality": round(self.last_consolidation_quality, 3)
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

