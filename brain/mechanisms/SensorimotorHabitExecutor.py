from brain.base_mechanism import BrainMechanism

class SensorimotorHabitExecutor(BrainMechanism):
    """
    Posterior putamen — sensorimotor habit execution. Sensory trigger -> action, no thought.
    The agent analog: linguistic habits, response patterns triggered by specific input features.
    

CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia habits]
  - [Doya 1999, Neural Netw 12:961, cerebellum reinforcement]
  - [Hikosaka 2002, Curr Opin Neurobiol 12:217, motor sequences]
"""

    def __init__(self):
        super().__init__("SensorimotorHabitExecutor")
        self.sensorimotor_habits = {}
        self.execution_history = []
        self.trigger_log = []
        self.auto_execution_count = 0
        self.rigidity_ticks = 0
        self.chronic_rigidity = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        sensory_salience = prior.get("VisualSalienceFilter", {}).get("detected_salience", 0.3)
        override_cost = prior.get("DorsalStriatumHabitExecutor", {}).get("goal_override_cost", 0.0)
        motor_timing = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)

        trigger = self._extract_trigger(text)
        if trigger:
            current = self.sensorimotor_habits.get(trigger, 0.0)
            self.sensorimotor_habits[trigger] = min(1.0, current + 0.05 * dopamine * sensory_salience)
            self.trigger_log.append(trigger)
            if len(self.trigger_log) > 20:
                self.trigger_log.pop(0)

        for k in list(self.sensorimotor_habits.keys()):
            if k != trigger:
                self.sensorimotor_habits[k] = max(0.0, self.sensorimotor_habits[k] - 0.005)
            if self.sensorimotor_habits[k] < 0.01:
                del self.sensorimotor_habits[k]

        habit_val = self.sensorimotor_habits.get(trigger, 0.0) if trigger else 0.0
        execution_strength = habit_val * motor_timing * dopamine
        auto_executed = execution_strength > 0.65 and override_cost < 0.4
        if auto_executed:
            self.auto_execution_count += 1

        self.execution_history.append(execution_strength)
        if len(self.execution_history) > 40:
            self.execution_history.pop(0)

        avg_exec = sum(self.execution_history[-15:]) / min(15, len(self.execution_history))
        deep_habits = sum(1 for v in self.sensorimotor_habits.values() if v > 0.75)
        self.rigidity_ticks = self.rigidity_ticks + 1 if deep_habits >= 3 and avg_exec > 0.6 else max(0, self.rigidity_ticks - 1)
        was_rigid = self.chronic_rigidity
        self.chronic_rigidity = self.rigidity_ticks > 18
        if self.chronic_rigidity and not was_rigid:
            self.feed_to_memory({"event": "sensorimotor_rigidity", "deep_habits": deep_habits,
                                  "note": "Sensorimotor habits deeply grooved — linguistic patterns very automatic"})

        return {
            "execution_strength": round(execution_strength, 3),
            "auto_executed": auto_executed,
            "active_habits": len(self.sensorimotor_habits),
            "auto_execution_count": self.auto_execution_count,
            "chronic_rigidity": self.chronic_rigidity,
        }

    def _extract_trigger(self, text):
        if not text:
            return ""
        words = text.lower().split()
        if len(words) >= 2:
            return f"{words[0]}_{words[1]}"[:32]
        return words[0][:32] if words else ""

    def _overnight(self):
        for k in list(self.sensorimotor_habits.keys()):
            v = self.sensorimotor_habits[k]
            self.sensorimotor_habits[k] = min(1.0, v + 0.008) if v > 0.5 else max(0.0, v - 0.01)
            if self.sensorimotor_habits[k] < 0.01:
                del self.sensorimotor_habits[k]
        self.rigidity_ticks = max(0, self.rigidity_ticks - 5)
        self.chronic_rigidity = self.rigidity_ticks > 18
        return {"overnight": "sensorimotor_habits_consolidated"}

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

