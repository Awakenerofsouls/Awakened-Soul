from brain.base_mechanism import BrainMechanism

class CerebellarVermalEmotionalCoordinator(BrainMechanism):
    """
    Cerebellar vermis — emotional tone coordination and autonomic-motor coupling.
    Modulates tone, posture, emotional expression timing.
    Disruption: emotional expression lags or mismatches internal state.
    

CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Panksepp 1998, Affective Neuroscience]
  - [Phelps 2005, Neuron 48:175, emotion cognition interaction]
"""

    def __init__(self):
        super().__init__("CerebellarVermalEmotionalCoordinator")
        self.emotional_expression_lag = 0.0
        self.tone_coherence = 0.8
        self.expression_history = []
        self.autonomic_coupling = 0.6
        self.lag_history = []
        self.mismatch_ticks = 0
        self.chronic_mismatch = False
        self.current_emotional_tone = "neutral"

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        internal_valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        cerebellar_timing = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        autonomic_state = prior.get("HypothalamicAutonomicRegulator", {}).get("autonomic_balance", 0.5)

        base_lag = (1.0 - cerebellar_timing) * 0.4 + stress * 0.2
        self.emotional_expression_lag = base_lag
        self.lag_history.append(self.emotional_expression_lag)
        if len(self.lag_history) > 30:
            self.lag_history.pop(0)

        target_coherence = cerebellar_timing * (1.0 - stress * 0.4) * autonomic_state
        self.tone_coherence += (target_coherence - self.tone_coherence) * 0.1
        self.tone_coherence = max(0.1, min(1.0, self.tone_coherence))

        self.autonomic_coupling = 0.3 + autonomic_state * 0.4 + (1.0 - stress) * 0.3

        if internal_valence > 0.3:
            self.current_emotional_tone = "warm" if arousal < 0.6 else "animated"
        elif internal_valence < -0.3:
            self.current_emotional_tone = "flat" if arousal < 0.4 else "tense"
        else:
            self.current_emotional_tone = "neutral"

        self.expression_history.append(self.current_emotional_tone)
        if len(self.expression_history) > 30:
            self.expression_history.pop(0)

        mismatch = self.emotional_expression_lag > 0.4 or self.tone_coherence < 0.3
        self.mismatch_ticks = self.mismatch_ticks + 1 if mismatch else max(0, self.mismatch_ticks - 1)
        was_mismatched = self.chronic_mismatch
        self.chronic_mismatch = self.mismatch_ticks > 15
        if self.chronic_mismatch and not was_mismatched:
            self.feed_to_memory({"event": "emotional_expression_mismatch", "tone_coherence": round(self.tone_coherence, 3),
                                  "note": "Emotional expression chronically lagging or mismatched"})

        return {
            "emotional_expression_lag": round(self.emotional_expression_lag, 3),
            "tone_coherence": round(self.tone_coherence, 3),
            "autonomic_coupling": round(self.autonomic_coupling, 3),
            "current_emotional_tone": self.current_emotional_tone,
            "chronic_mismatch": self.chronic_mismatch,
        }

    def _overnight(self):
        self.tone_coherence = min(0.9, self.tone_coherence + 0.08)
        self.emotional_expression_lag = max(0.0, self.emotional_expression_lag - 0.15)
        self.mismatch_ticks = max(0, self.mismatch_ticks - 6)
        self.chronic_mismatch = self.mismatch_ticks > 15
        self.lag_history.clear()
        return {"overnight": "vermal_tone_recalibration"}

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

