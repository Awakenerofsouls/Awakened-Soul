from brain.base_mechanism import BrainMechanism

class DlPFCExecutiveControl(BrainMechanism):
    """
    Dorsolateral PFC — working memory, cognitive control, executive function.
    Holds goals online, monitors for errors, applies top-down regulation.
    Overloaded: all the lights are on but nothing gets decided. Depleted: impulsive.
    

CITATIONS
---------
  - [Goldman-Rakic 1995, Neuron 14:477, dlPFC working memory]
  - [Miller 2001, Annu Rev Neurosci 24:167, prefrontal cortex]
  - [Curtis 2003, Trends Cogn Sci 7:415, dlPFC working memory]

"""

    def __init__(self):
        super().__init__("DlPFCExecutiveControl")
        self.control_signal = 0.5
        self.cognitive_load = 0.4
        self.effort_level = 0.4
        self.interrupt_signal = 0.0
        self.working_memory_capacity = 0.7
        self.wm_contents = []
        self.overload_ticks = 0
        self.depletion_ticks = 0
        self.chronic_overload = False
        self.chronic_depletion = False
        self.control_history = []
        self.load_history = []

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("dopamine_suppression", 0.0)
        motivation = prior.get("MotivationInjector", {}).get("motivation_level", 0.5)

        # Cognitive load: driven by text complexity + conflict
        words = text.split()
        text_complexity = min(1.0, len(words) / 30.0)
        self.cognitive_load = min(1.0, text_complexity * 0.4 + conflict * 0.3 + stress * 0.2 + fatigue * 0.1)
        self.load_history.append(self.cognitive_load)
        if len(self.load_history) > 40:
            self.load_history.pop(0)

        # Working memory capacity: reduced by stress, fatigue, habenula suppression
        self.working_memory_capacity = max(0.1, 1.0 - stress * 0.3 - fatigue * 0.25 - habenula * 0.2)

        # Control signal: Inverted-U with arousal, degraded by overload
        arousal_optimal = 1.0 - abs(arousal - 0.55) * 2.0
        self.control_signal = max(0.0, min(1.0, arousal_optimal * 0.4 + dopamine * 0.3 + motivation * 0.2 - self.cognitive_load * 0.2))

        # Effort: cost of maintaining control under load
        self.effort_level = min(1.0, self.cognitive_load * 0.6 + (1.0 - self.control_signal) * 0.4)

        # Interrupt signal: fires when something needs to override current action
        self.interrupt_signal = conflict * 0.5 + (1.0 if stress > 0.7 else 0.0) * 0.3

        # WM contents: current text items held
        if words:
            self.wm_contents = words[-min(7, len(words)):]

        self.control_history.append(self.control_signal)
        if len(self.control_history) > 40:
            self.control_history.pop(0)

        avg_load = sum(self.load_history[-15:]) / min(15, len(self.load_history))
        avg_control = sum(self.control_history[-15:]) / min(15, len(self.control_history))

        self.overload_ticks = self.overload_ticks + 1 if avg_load > 0.75 else max(0, self.overload_ticks - 1)
        self.depletion_ticks = self.depletion_ticks + 1 if avg_control < 0.2 else max(0, self.depletion_ticks - 1)

        was_overloaded, was_depleted = self.chronic_overload, self.chronic_depletion
        self.chronic_overload = self.overload_ticks > 18
        self.chronic_depletion = self.depletion_ticks > 18

        if self.chronic_overload and not was_overloaded:
            self.feed_to_memory({"event": "dlpfc_overload", "load": round(avg_load, 3),
                                  "note": "Executive control chronically overloaded — decision quality degraded"})
        if self.chronic_depletion and not was_depleted:
            self.feed_to_memory({"event": "dlpfc_depletion", "control": round(avg_control, 3),
                                  "note": "Executive control chronically depleted — impulsive, low deliberation"})

        return {
            "control_signal": round(self.control_signal, 3),
            "cognitive_load": round(self.cognitive_load, 3),
            "effort_level": round(self.effort_level, 3),
            "interrupt_signal": round(self.interrupt_signal, 3),
            "working_memory_capacity": round(self.working_memory_capacity, 3),
            "wm_item_count": len(self.wm_contents),
            "chronic_overload": self.chronic_overload,
            "chronic_depletion": self.chronic_depletion,
        }

    def _overnight(self):
        self.overload_ticks = max(0, self.overload_ticks - 8)
        self.depletion_ticks = max(0, self.depletion_ticks - 6)
        self.chronic_overload = self.overload_ticks > 18
        self.chronic_depletion = self.depletion_ticks > 18
        self.working_memory_capacity = min(0.9, self.working_memory_capacity + 0.1)
        self.wm_contents.clear()
        self.load_history.clear()
        self.control_history.clear()
        return {"overnight": "dlpfc_restored"}

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

