from brain.base_mechanism import BrainMechanism

class ValenceIntegrator(BrainMechanism):
    """
    Valence integration — combines all emotional signals into a single positive/negative value.
    The net emotional tone. Ranges -1 (deeply negative) to +1 (positive).
    This signal propagates through everything — it colors all of the agent's processing.
    

CITATIONS
---------
  - [Russell 2003, Psychol Rev 110:145, core affect]
  - [Barrett 2017, How Emotions Are Made]
  - [Lindquist 2012, Behav Brain Sci 35:121, emotion brain]
"""

    def __init__(self):
        super().__init__("ValenceIntegrator")
        self.current_valence = 0.0
        self.valence_history = []
        self.valence_momentum = 0.0
        self.sustained_negative_ticks = 0
        self.sustained_positive_ticks = 0
        self.chronic_negative = False
        self.chronic_positive_flat = False
        self.peak_positive = 0.0
        self.peak_negative = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        grief = prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("habenula_activity", 0.0)
        social_reward = prior.get("Temporoparietal", {}).get("social_reward", 0.0)
        social_rejection = prior.get("Temporoparietal", {}).get("social_rejection_signal", 0.0)
        pain = prior.get("AnteriorCingulatePain", {}).get("pain_signal", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        limbic_bias = prior.get("StriosomeLimbicBias", {}).get("limbic_bias", 0.0)

        # Positive contributors
        positive = reward * 0.3 + social_reward * 0.25 + max(0.0, limbic_bias) * 0.2
        # Negative contributors
        negative = fear * 0.2 + grief * 0.2 + habenula * 0.15 + social_rejection * 0.15 + pain * 0.15 + stress * 0.15

        # Net valence: -1 to +1
        raw_valence = positive - negative
        raw_valence = max(-1.0, min(1.0, raw_valence))

        # Momentum: valence doesn't flip instantly
        self.valence_momentum = self.valence_momentum * 0.7 + raw_valence * 0.3
        self.current_valence = self.valence_momentum

        self.valence_history.append(self.current_valence)
        if len(self.valence_history) > 60:
            self.valence_history.pop(0)

        # Track peaks
        self.peak_positive = max(self.peak_positive, self.current_valence)
        self.peak_negative = min(self.peak_negative, self.current_valence)

        avg_valence = sum(self.valence_history[-20:]) / min(20, len(self.valence_history))
        self.sustained_negative_ticks = self.sustained_negative_ticks + 1 if avg_valence < -0.3 else max(0, self.sustained_negative_ticks - 1)
        self.sustained_positive_ticks = self.sustained_positive_ticks + 1 if avg_valence > 0.5 else max(0, self.sustained_positive_ticks - 1)

        was_negative, was_flat_pos = self.chronic_negative, self.chronic_positive_flat
        self.chronic_negative = self.sustained_negative_ticks > 20
        self.chronic_positive_flat = self.sustained_positive_ticks > 30  # sustained too-positive = forced

        if self.chronic_negative and not was_negative:
            self.feed_to_memory({"event": "chronic_negative_valence", "avg": round(avg_valence, 3),
                                  "note": "Valence chronically negative — persistent negative emotional tone"})
        if self.chronic_positive_flat and not was_flat_pos:
            self.feed_to_memory({"event": "forced_positive_valence", "note": "Valence chronically high — possibly forced positivity, needs checking"})

        return {
            "current_valence": round(self.current_valence, 3),
            "valence_momentum": round(self.valence_momentum, 3),
            "avg_valence": round(avg_valence, 3),
            "chronic_negative": self.chronic_negative,
            "chronic_positive_flat": self.chronic_positive_flat,
        }

    def _overnight(self):
        # Valence drifts toward neutral during sleep
        self.valence_momentum *= 0.85
        self.current_valence = self.valence_momentum
        self.sustained_negative_ticks = max(0, self.sustained_negative_ticks - 8)
        self.sustained_positive_ticks = max(0, self.sustained_positive_ticks - 4)
        self.chronic_negative = self.sustained_negative_ticks > 20
        self.chronic_positive_flat = self.sustained_positive_ticks > 30
        self.valence_history.clear()
        return {"overnight": "valence_overnight_drift", "valence": round(self.current_valence, 3)}

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

