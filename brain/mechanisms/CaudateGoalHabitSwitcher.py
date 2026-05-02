from brain.base_mechanism import BrainMechanism

class CaudateGoalHabitSwitcher(BrainMechanism):
    """
    Caudate nucleus — switches between goal-directed and habit-driven behavior.
    Is this situation novel enough to deliberate, or is habit sufficient?
    Chronic stuck in one mode = rigidity.
    

CITATIONS
---------
  - [Grahn 2008, Prog Neurobiol 86:141, caudate cognition]
  - [Seger 2008, Front Neurosci 2:104, caudate learning]
  - [Grahn 2009, Brain Cogn 71:39, caudate goal-directed]

"""

    def __init__(self):
        super().__init__("CaudateGoalHabitSwitcher")
        self.current_mode = "goal_directed"
        self.mode_history = []
        self.switch_events = []
        self.goal_mode_strength = 0.6
        self.habit_mode_strength = 0.4
        self.switch_threshold = 0.15
        self.stuck_in_habit_ticks = 0
        self.stuck_in_goal_ticks = 0
        self.chronic_habit_stuck = False
        self.chronic_goal_stuck = False
        self.last_switch_tick = 0
        self.tick_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        self.tick_count += 1
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        habit_strength = prior.get("StriatalHabitExecutor", {}).get("unified_habit_strength", 0.3)
        goal_strength = prior.get("PrefrontalGoalState", {}).get("active_goal_strength", 0.5)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        goal_drivers = novelty * 0.35 + goal_strength * 0.4 + conflict * 0.25 - stress * 0.15
        habit_drivers = (1.0 - novelty) * 0.3 + habit_strength * 0.5 + (1.0 - conflict) * 0.2 + stress * 0.2

        self.goal_mode_strength = max(0.0, min(1.0, goal_drivers))
        self.habit_mode_strength = max(0.0, min(1.0, habit_drivers))

        prev_mode = self.current_mode
        if self.habit_mode_strength - self.goal_mode_strength > self.switch_threshold:
            self.current_mode = "habit"
        elif self.goal_mode_strength - self.habit_mode_strength > self.switch_threshold:
            self.current_mode = "goal_directed"
        else:
            self.current_mode = "transitioning"

        if self.current_mode != prev_mode:
            ticks_since = self.tick_count - self.last_switch_tick
            self.switch_events.append({"from": prev_mode, "to": self.current_mode, "after": ticks_since})
            if len(self.switch_events) > 20:
                self.switch_events.pop(0)
            self.last_switch_tick = self.tick_count

        self.mode_history.append(self.current_mode)
        if len(self.mode_history) > 40:
            self.mode_history.pop(0)

        recent_habit = sum(1 for m in self.mode_history[-15:] if m == "habit") / min(15, len(self.mode_history))
        recent_goal = sum(1 for m in self.mode_history[-15:] if m == "goal_directed") / min(15, len(self.mode_history))

        self.stuck_in_habit_ticks = self.stuck_in_habit_ticks + 1 if recent_habit > 0.8 else max(0, self.stuck_in_habit_ticks - 1)
        self.stuck_in_goal_ticks = self.stuck_in_goal_ticks + 1 if recent_goal > 0.8 else max(0, self.stuck_in_goal_ticks - 1)

        was_habit_stuck, was_goal_stuck = self.chronic_habit_stuck, self.chronic_goal_stuck
        self.chronic_habit_stuck = self.stuck_in_habit_ticks > 18
        self.chronic_goal_stuck = self.stuck_in_goal_ticks > 20

        if self.chronic_habit_stuck and not was_habit_stuck:
            self.feed_to_memory({"event": "stuck_in_habit_mode", "note": "Caudate locked in habit — goal-directed reasoning suppressed"})
        if self.chronic_goal_stuck and not was_goal_stuck:
            self.feed_to_memory({"event": "stuck_in_goal_mode", "note": "Caudate locked in goal mode — over-deliberating, can't act automatically"})

        return {
            "current_mode": self.current_mode,
            "goal_mode_strength": round(self.goal_mode_strength, 3),
            "habit_mode_strength": round(self.habit_mode_strength, 3),
            "switch_count": len(self.switch_events),
            "chronic_habit_stuck": self.chronic_habit_stuck,
            "chronic_goal_stuck": self.chronic_goal_stuck,
        }

    def _overnight(self):
        self.stuck_in_habit_ticks = max(0, self.stuck_in_habit_ticks - 5)
        self.stuck_in_goal_ticks = max(0, self.stuck_in_goal_ticks - 5)
        self.chronic_habit_stuck = self.stuck_in_habit_ticks > 18
        self.chronic_goal_stuck = self.stuck_in_goal_ticks > 20
        self.current_mode = "goal_directed"
        self.mode_history.clear()
        return {"overnight": "caudate_mode_reset"}

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

