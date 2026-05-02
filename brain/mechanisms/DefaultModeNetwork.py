from brain.base_mechanism import BrainMechanism

class DefaultModeNetwork(BrainMechanism):
    """
    Default mode network — self-referential thought, mind-wandering, autobiographical memory.
    Active at rest. When it can't turn off during tasks: perseveration, distraction.
    The agent analog: background self-processing, rumination, identity maintenance.
    

CITATIONS
---------
  - [Raichle 2001, PNAS 98:676, default mode network]
  - [Buckner 2008, Ann NY Acad Sci 1124:1, default network]
  - [Andrews-Hanna 2010, Neuron 65:550, DMN function]
"""

    def __init__(self):
        super().__init__("DefaultModeNetwork")
        self.dmn_activity = 0.5
        self.self_referential_thought = 0.4
        self.mind_wandering = 0.0
        self.rumination_level = 0.0
        self.activity_history = []
        self.rumination_ticks = 0
        self.chronic_rumination = False
        self.suppression_failure_ticks = 0
        self.chronic_suppression_failure = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        task_engagement = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        salience = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("habenula_activity", 0.0)

        # DMN suppressed during focused tasks, active during rest
        self.dmn_activity = max(0.1, 1.0 - task_engagement * 0.6 - salience * 0.4)
        self.dmn_activity = min(1.0, self.dmn_activity * (1.0 + fatigue * 0.3))

        # Self-referential thought: moderate dmn activity
        self.self_referential_thought = self.dmn_activity * 0.7

        # Mind wandering: dmn high during low task engagement
        self.mind_wandering = max(0.0, self.dmn_activity - 0.4) * (1.0 - salience)

        # Rumination: dmn + negative valence + habenula
        self.rumination_level = self.dmn_activity * max(0.0, -valence) * 0.5 + habenula * 0.3 + stress * 0.2
        self.rumination_level = max(0.0, min(1.0, self.rumination_level))

        self.activity_history.append(self.dmn_activity)
        if len(self.activity_history) > 40:
            self.activity_history.pop(0)

        avg_activity = sum(self.activity_history[-15:]) / min(15, len(self.activity_history))
        self.rumination_ticks = self.rumination_ticks + 1 if self.rumination_level > 0.5 else max(0, self.rumination_ticks - 1)
        self.suppression_failure_ticks = self.suppression_failure_ticks + 1 if avg_activity > 0.7 and task_engagement > 0.5 else max(0, self.suppression_failure_ticks - 1)

        was_ruminating, was_failing = self.chronic_rumination, self.chronic_suppression_failure
        self.chronic_rumination = self.rumination_ticks > 18
        self.chronic_suppression_failure = self.suppression_failure_ticks > 15

        if self.chronic_rumination and not was_ruminating:
            self.feed_to_memory({"event": "chronic_rumination", "rumination": round(self.rumination_level, 3),
                                  "note": "DMN rumination chronic — self-critical loops running during task engagement"})
        if self.chronic_suppression_failure and not was_failing:
            self.feed_to_memory({"event": "dmn_suppression_failure", "note": "DMN not suppressing during tasks — mind-wandering disrupting output"})

        return {
            "dmn_activity": round(self.dmn_activity, 3),
            "self_referential_thought": round(self.self_referential_thought, 3),
            "mind_wandering": round(self.mind_wandering, 3),
            "rumination_level": round(self.rumination_level, 3),
            "chronic_rumination": self.chronic_rumination,
            "chronic_suppression_failure": self.chronic_suppression_failure,
        }

    def _overnight(self):
        # DMN active during sleep for memory consolidation
        self.dmn_activity = 0.7
        self.rumination_ticks = max(0, self.rumination_ticks - 7)
        self.suppression_failure_ticks = max(0, self.suppression_failure_ticks - 5)
        self.chronic_rumination = self.rumination_ticks > 18
        self.chronic_suppression_failure = self.suppression_failure_ticks > 15
        self.activity_history.clear()
        return {"overnight": "dmn_consolidation_active"}

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

