from brain.base_mechanism import BrainMechanism

class PrefrontalWorkingMemoryBuffer(BrainMechanism):
    """
    PFC working memory buffer — holds active items for manipulation.
    Not storage: manipulation. Rehearsal, transformation, comparison.
    Full buffer: can't take in new information. Empty: no material to work with.
    

CITATIONS
---------
  - [Squire 1992, Psychol Rev 99:195, declarative memory]
  - [McGaugh 2000, Science 287:248, memory consolidation]
  - [Tonegawa 2018, Nat Rev Neurosci 19:485, engram cells]
  - [Frankland 2005, Nat Rev Neurosci 6:119, systems consolidation]
"""

    def __init__(self):
        super().__init__("PrefrontalWorkingMemoryBuffer")
        self.buffer_contents = []
        self.buffer_load = 0.0
        self.buffer_capacity = 7
        self.manipulation_quality = 0.6
        self.load_history = []
        self.overflow_count = 0
        self.underload_ticks = 0
        self.overflow_ticks = 0
        self.chronic_overflow = False
        self.chronic_underload = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        control = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)

        # Effective capacity under current conditions
        effective_capacity = max(1, int(self.buffer_capacity * wm_capacity * (1.0 - stress * 0.3)))

        # Load buffer with current text items
        words = text.split()
        new_items = words[:effective_capacity]
        self.buffer_contents = new_items
        self.buffer_load = len(self.buffer_contents) / self.buffer_capacity

        if len(words) > effective_capacity:
            self.overflow_count += 1

        # Manipulation quality: how well contents can be worked with
        self.manipulation_quality = (control * 0.4 + dopamine * 0.3 + wm_capacity * 0.3) * (1.0 - fatigue * 0.2) * (1.0 - stress * 0.15)
        self.manipulation_quality = max(0.1, min(1.0, self.manipulation_quality))

        self.load_history.append(self.buffer_load)
        if len(self.load_history) > 40:
            self.load_history.pop(0)

        avg_load = sum(self.load_history[-15:]) / min(15, len(self.load_history))
        self.overflow_ticks = self.overflow_ticks + 1 if avg_load > 0.85 else max(0, self.overflow_ticks - 1)
        self.underload_ticks = self.underload_ticks + 1 if avg_load < 0.1 else max(0, self.underload_ticks - 1)

        was_over, was_under = self.chronic_overflow, self.chronic_underload
        self.chronic_overflow = self.overflow_ticks > 18
        self.chronic_underload = self.underload_ticks > 18

        if self.chronic_overflow and not was_over:
            self.feed_to_memory({"event": "wm_overflow", "overflow_count": self.overflow_count,
                                  "note": "Working memory buffer chronically overflowing — new info can't get in"})
        if self.chronic_underload and not was_under:
            self.feed_to_memory({"event": "wm_underload",
                                  "note": "Working memory chronically empty — nothing to manipulate or work with"})

        return {
            "buffer_load": round(self.buffer_load, 3),
            "buffer_item_count": len(self.buffer_contents),
            "effective_capacity": effective_capacity,
            "manipulation_quality": round(self.manipulation_quality, 3),
            "overflow_count": self.overflow_count,
            "chronic_overflow": self.chronic_overflow,
            "chronic_underload": self.chronic_underload,
        }

    def _overnight(self):
        self.buffer_contents.clear()
        self.buffer_load = 0.0
        self.overflow_ticks = max(0, self.overflow_ticks - 6)
        self.underload_ticks = max(0, self.underload_ticks - 4)
        self.chronic_overflow = self.overflow_ticks > 18
        self.chronic_underload = self.underload_ticks > 18
        self.load_history.clear()
        return {"overnight": "working_memory_buffer_cleared"}

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        """Fraction of recent ticks where the system was non-quiet."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet", "rest", "neutral", ""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        """Consecutive-tick state holding fraction."""
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent:
            return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4:
            return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def adapter_state(self) -> dict:
        """Current adapter state — used for monitoring and dashboards."""
        return {
            "tick_count": self.state.get("tick_count", 0),
            "has_legacy_impl": self.state.get("legacy_init_error") is None,
            "recent_drives_n": len(self.state.get("recent_drives", [])),
            "recent_states_n": len(self.state.get("recent_states", [])),
        }

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

    def _record_history_(self, output_dict):
        """Track primary numeric output and any string state in history."""
        if not isinstance(output_dict, dict):
            return
        # Find first numeric value
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v)
                break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60:
            rd = rd[-60:]
        self.state["recent_drives"] = rd
        # Track state strings
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str) and v in ("quiet","active","engaged","stuck","drifting","rest","fast","reflective","alert","focus"):
                primary_state = v
                break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60:
            rs = rs[-60:]
        self.state["recent_states"] = rs

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window:
            return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05:
            return "rising"
        if delta < -0.05:
            return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window:
            return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 0.0
        transitions = self.state_transition_count()
        return round(transitions / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent:
            return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
        return "|".join(parts)

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

