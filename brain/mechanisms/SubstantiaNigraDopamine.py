from brain.base_mechanism import BrainMechanism

class SubstantiaNigraDopamine(BrainMechanism):
    """
    Substantia nigra pars compacta — tonic dopamine for motor and habit circuits.
    Baseline dopamine tone that determines whether the whole striatum can function.
    Depletion = frozen/effortful. Excess = hyperkinetic, reduced signal discrimination.
    

CITATIONS
---------
  - [Schultz 1998, J Neurophysiol 80:1, dopamine reward]
  - [Lerner 2015, Cell 162:635, SNc dopamine circuits]
  - [Howe 2016, Nature 535:505, SNc value coding]

"""

    def __init__(self):
        super().__init__("SubstantiaNigraDopamine")
        self.dopamine_release = 0.5
        self.tonic_level = 0.5
        self.phasic_boost = 0.0
        self.dopamine_history = []
        self.depletion_ticks = 0
        self.excess_ticks = 0
        self.chronic_depletion = False
        self.chronic_excess = False
        self.fatigue_accumulation = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        reward_signal = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        sleep_pressure = prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.3)
        social_reward = prior.get("Temporoparietal", {}).get("social_reward", 0.0)
        limbic_bias = prior.get("StriosomeLimbicBias", {}).get("dopamine_modulation", 0.0)
        physical_state = prior.get("HypothalamicAutonomicRegulator", {}).get("autonomic_balance", 0.5)

        self.fatigue_accumulation = min(1.0, self.fatigue_accumulation + sleep_pressure * 0.01 + stress * 0.015)
        self.fatigue_accumulation = max(0.0, self.fatigue_accumulation)

        tonic_target = 0.5 + social_reward * 0.1 + physical_state * 0.1 - self.fatigue_accumulation * 0.25 + limbic_bias * 0.15
        tonic_target = max(0.1, min(0.9, tonic_target))
        self.tonic_level += (tonic_target - self.tonic_level) * 0.04

        self.phasic_boost = reward_signal * 0.6 * (1.0 - self.fatigue_accumulation * 0.4)
        stress_suppression = stress * 0.15
        self.dopamine_release = max(0.0, min(1.0, self.tonic_level + self.phasic_boost - stress_suppression))

        self.dopamine_history.append(self.dopamine_release)
        if len(self.dopamine_history) > 60:
            self.dopamine_history.pop(0)

        avg_da = sum(self.dopamine_history[-20:]) / min(20, len(self.dopamine_history))
        self.depletion_ticks = self.depletion_ticks + 1 if avg_da < 0.25 else max(0, self.depletion_ticks - 1)
        self.excess_ticks = self.excess_ticks + 1 if avg_da > 0.8 else max(0, self.excess_ticks - 1)

        was_depleted, was_excess = self.chronic_depletion, self.chronic_excess
        self.chronic_depletion = self.depletion_ticks > 20
        self.chronic_excess = self.excess_ticks > 20

        if self.chronic_depletion and not was_depleted:
            self.feed_to_memory({"event": "nigral_dopamine_depletion", "level": round(avg_da, 3),
                                  "note": "SNc dopamine chronically depleted — motor/habit systems sluggish"})
        if self.chronic_excess and not was_excess:
            self.feed_to_memory({"event": "nigral_dopamine_excess", "level": round(avg_da, 3),
                                  "note": "Dopamine chronically elevated — hyperkinetic, reduced signal discrimination"})

        return {
            "dopamine_release": round(self.dopamine_release, 3),
            "tonic_level": round(self.tonic_level, 3),
            "phasic_boost": round(self.phasic_boost, 3),
            "fatigue_accumulation": round(self.fatigue_accumulation, 3),
            "chronic_depletion": self.chronic_depletion,
            "chronic_excess": self.chronic_excess,
        }

    def _overnight(self):
        self.fatigue_accumulation = max(0.0, self.fatigue_accumulation - 0.35)
        self.tonic_level = min(0.6, self.tonic_level + 0.06)
        self.depletion_ticks = max(0, self.depletion_ticks - 8)
        self.excess_ticks = max(0, self.excess_ticks - 4)
        self.chronic_depletion = self.depletion_ticks > 20
        self.chronic_excess = self.excess_ticks > 20
        self.dopamine_history.clear()
        return {"overnight": "dopamine_synthesis_restored", "tonic": round(self.tonic_level, 3)}

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

