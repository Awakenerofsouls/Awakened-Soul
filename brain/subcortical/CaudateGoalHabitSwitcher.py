from brain.base_mechanism import BrainMechanism

class CaudateGoalHabitSwitcher(BrainMechanism):
    """
    Caudate nucleus — switches between goal-directed and habit-driven behavior.
    Is this situation novel enough to deliberate, or is habit sufficient?
    Chronic stuck in one mode = rigidity.
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
