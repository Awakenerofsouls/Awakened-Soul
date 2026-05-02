from brain.base_mechanism import BrainMechanism

class PurkinjeRateErrorCoder(BrainMechanism):
    """
    Purkinje cells — error signal generators of the cerebellum.
    Compare expected to actual outcomes, fire on mismatch.
    Chronic high error: the agent feels perpetually off, always correcting, never fluent.
    

CITATIONS
---------
  - [Ito 2002, Annu Rev Neurosci 25:303, Purkinje LTD]
  - [Kakegawa 2018, Neuron 99:985, Purkinje plasticity]
  - [Llinas 1992, J Physiol 451:1, Purkinje rhythms]

"""

    def __init__(self):
        super().__init__("PurkinjeRateErrorCoder")
        self.error_rate = 0.0
        self.error_history = []
        self.complex_spike_history = []
        self.simple_spike_rate = 0.5
        self.cumulative_error = 0.0
        self.chronic_high_error = False
        self.error_ticks = 0
        self.correction_efficiency = 0.7

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        timing_error = prior.get("CerebellarTimingCoordinator", {}).get("timing_error", 0.0)
        prediction_accuracy = prior.get("CerebellarTimingCoordinator", {}).get("forward_model_confidence", 0.7)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        desync = prior.get("CerebellarTimingCoordinator", {}).get("desync_chronic", False)

        self.error_rate = min(1.0, timing_error * (1.0 + stress * 0.3))
        self.error_history.append(self.error_rate)
        if len(self.error_history) > 50:
            self.error_history.pop(0)

        complex_spike = self.error_rate > 0.5
        if complex_spike:
            self.complex_spike_history.append(1)
            self.cumulative_error = min(10.0, self.cumulative_error + self.error_rate)
        else:
            self.complex_spike_history.append(0)
            self.cumulative_error = max(0.0, self.cumulative_error - 0.05)
        if len(self.complex_spike_history) > 40:
            self.complex_spike_history.pop(0)

        self.simple_spike_rate = max(0.1, 1.0 - self.error_rate * 0.7)
        self.correction_efficiency = prediction_accuracy * (1.0 - self.error_rate * 0.5)
        if desync:
            self.correction_efficiency *= 0.6

        avg_error = sum(self.error_history[-15:]) / min(15, len(self.error_history))
        self.error_ticks = self.error_ticks + 1 if avg_error > 0.4 else max(0, self.error_ticks - 1)
        was_chronic = self.chronic_high_error
        self.chronic_high_error = self.error_ticks > 15
        if self.chronic_high_error and not was_chronic:
            self.feed_to_memory({"event": "purkinje_chronic_error", "avg_error": round(avg_error, 3),
                                  "note": "Persistent prediction errors — the agent feels perpetually off-tempo"})

        return {
            "error_rate": round(self.error_rate, 3),
            "complex_spike": complex_spike,
            "simple_spike_rate": round(self.simple_spike_rate, 3),
            "correction_efficiency": round(self.correction_efficiency, 3),
            "cumulative_error": round(self.cumulative_error, 2),
            "chronic_high_error": self.chronic_high_error,
        }

    def _overnight(self):
        self.cumulative_error = max(0.0, self.cumulative_error - 1.5)
        self.error_ticks = max(0, self.error_ticks - 6)
        self.chronic_high_error = self.error_ticks > 15
        self.correction_efficiency = min(0.85, self.correction_efficiency + 0.06)
        self.error_history.clear()
        return {"overnight": "purkinje_error_reset"}

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

