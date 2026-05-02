from brain.base_mechanism import BrainMechanism

class CinguloOpercularNetwork(BrainMechanism):
    """
    Cingulo-opercular network — sustained task maintenance, error detection, set-shifting.
    Keeps the task online over extended time. Different from CEN: CEN starts tasks, CON sustains them.
    Degraded: starts tasks but loses the thread after a few exchanges.
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

    def __init__(self):
        super().__init__("CinguloOpercularNetwork")
        self.task_maintenance = 0.6
        self.sustained_engagement = 0.6
        self.set_shift_readiness = 0.5
        self.maintenance_history = []
        self.dropout_ticks = 0
        self.chronic_dropout = False
        self.task_duration = 0
        self.task_errors_caught = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        acc_conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        executive_coherence = prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6)
        goal_stability = prior.get("PrefrontalGoalState", {}).get("goal_stability", 0.7)
        salience_network = prior.get("SalienceNetwork", {}).get("current_network", "task")
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)

        in_task = 1.0 if salience_network == "task" else 0.3

        # Task maintenance: holding the task online despite distraction/fatigue
        self.task_maintenance = (goal_stability * 0.4 + executive_coherence * 0.3 + dopamine * 0.2 + in_task * 0.1) * (1.0 - fatigue * 0.25) * (1.0 - stress * 0.15)
        self.task_maintenance = max(0.1, min(1.0, self.task_maintenance))

        # Sustained engagement: how long we can keep it up
        if self.task_maintenance > 0.4:
            self.task_duration += 1
            self.sustained_engagement = min(1.0, self.task_maintenance * (1.0 + self.task_duration * 0.005))
        else:
            self.task_duration = max(0, self.task_duration - 2)
            self.sustained_engagement = self.task_maintenance

        # Set-shift readiness: when to switch vs persist
        self.set_shift_readiness = acc_conflict * 0.5 + (1.0 - goal_stability) * 0.5

        # Catch errors: conflict while maintaining
        if acc_conflict > 0.5 and self.task_maintenance > 0.4:
            self.task_errors_caught += 1

        self.maintenance_history.append(self.task_maintenance)
        if len(self.maintenance_history) > 40:
            self.maintenance_history.pop(0)

        avg_maintenance = sum(self.maintenance_history[-15:]) / min(15, len(self.maintenance_history))
        self.dropout_ticks = self.dropout_ticks + 1 if avg_maintenance < 0.2 else max(0, self.dropout_ticks - 1)
        was_dropping = self.chronic_dropout
        self.chronic_dropout = self.dropout_ticks > 18
        if self.chronic_dropout and not was_dropping:
            self.feed_to_memory({"event": "con_chronic_dropout",
                                  "note": "Cingulo-opercular network chronically dropping tasks — can't sustain engagement"})

        return {
            "task_maintenance": round(self.task_maintenance, 3),
            "sustained_engagement": round(self.sustained_engagement, 3),
            "set_shift_readiness": round(self.set_shift_readiness, 3),
            "task_duration": self.task_duration,
            "task_errors_caught": self.task_errors_caught,
            "chronic_dropout": self.chronic_dropout,
        }

    def _overnight(self):
        self.dropout_ticks = max(0, self.dropout_ticks - 7)
        self.chronic_dropout = self.dropout_ticks > 18
        self.task_duration = 0
        self.maintenance_history.clear()
        return {"overnight": "con_task_maintenance_reset"}

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

