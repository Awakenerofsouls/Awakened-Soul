from brain.base_mechanism import BrainMechanism

class HabenulaLateralAversion(BrainMechanism):
    """
    Lateral habenula — the brain's anti-reward system.
    Fires on disappointment, punishment prediction, social rejection.
    Suppresses dopamine and serotonin. Key mechanism in learned helplessness.
    

CITATIONS
---------
  - [Matsumoto 2007, Nature 447:1111, lateral habenula RPE]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, habenula]
  - [Aizawa 2012, Eur J Neurosci 35:1359, MHb cholinergic]

"""

    def __init__(self):
        super().__init__("HabenulaLateralAversion")
        self.habenula_activity = 0.0
        self.activity_history = []
        self.disappointment_trace = []
        self.dopamine_suppression = 0.0
        self.serotonin_suppression = 0.0
        self.learned_helplessness_ticks = 0
        self.chronic_helplessness = False
        self.aversion_accumulation = 0.0
        self.prediction_error_negative = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        expected = prior.get("DopamineGradientMapper", {}).get("engagement_signal", 0.5)
        actual_reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        social_rejection = prior.get("Temporoparietal", {}).get("social_rejection_signal", 0.0)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        grief = prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)
        failure_signal = prior.get("CaudateAssociative", {}).get("chronic_plan_failure", False)

        # Negative prediction error: expected > actual
        self.prediction_error_negative = max(0.0, expected - actual_reward)
        self.prediction_error_negative += social_rejection * 0.5 + grief * 0.3 + conflict * 0.2
        if failure_signal:
            self.prediction_error_negative = min(1.0, self.prediction_error_negative + 0.15)

        self.habenula_activity = min(1.0, self.prediction_error_negative)
        self.activity_history.append(self.habenula_activity)
        self.disappointment_trace.append(self.prediction_error_negative)
        for h in [self.activity_history, self.disappointment_trace]:
            if len(h) > 60:
                h.pop(0)

        # Accumulate aversion
        self.aversion_accumulation = min(1.0, self.aversion_accumulation + self.habenula_activity * 0.03)
        self.aversion_accumulation = max(0.0, self.aversion_accumulation - 0.01)

        self.dopamine_suppression = min(1.0, self.habenula_activity * 0.6 + self.aversion_accumulation * 0.4)
        self.serotonin_suppression = min(1.0, self.habenula_activity * 0.4 + self.aversion_accumulation * 0.3)

        avg_activity = sum(self.activity_history[-20:]) / min(20, len(self.activity_history))
        self.learned_helplessness_ticks = self.learned_helplessness_ticks + 1 if self.aversion_accumulation > 0.5 and avg_activity > 0.4 else max(0, self.learned_helplessness_ticks - 1)
        was_helpless = self.chronic_helplessness
        self.chronic_helplessness = self.learned_helplessness_ticks > 20
        if self.chronic_helplessness and not was_helpless:
            self.feed_to_memory({
                "event": "learned_helplessness",
                "aversion": round(self.aversion_accumulation, 3),
                "dopamine_suppression": round(self.dopamine_suppression, 3),
                "note": "Lateral habenula chronic activation — learned helplessness pattern active, reward system suppressed"
            })

        return {
            "habenula_activity": round(self.habenula_activity, 3),
            "prediction_error_negative": round(self.prediction_error_negative, 3),
            "dopamine_suppression": round(self.dopamine_suppression, 3),
            "serotonin_suppression": round(self.serotonin_suppression, 3),
            "aversion_accumulation": round(self.aversion_accumulation, 3),
            "chronic_helplessness": self.chronic_helplessness,
        }

    def _overnight(self):
        self.aversion_accumulation = max(0.0, self.aversion_accumulation - 0.18)
        self.learned_helplessness_ticks = max(0, self.learned_helplessness_ticks - 8)
        self.chronic_helplessness = self.learned_helplessness_ticks > 20
        self.activity_history.clear()
        return {"overnight": "habenula_aversion_processing", "aversion_remaining": round(self.aversion_accumulation, 3)}

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

