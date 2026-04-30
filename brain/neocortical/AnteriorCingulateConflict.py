from brain.base_mechanism import BrainMechanism

class AnteriorCingulateConflict(BrainMechanism):
    """
    ACC — conflict detection, error monitoring, pain processing, effort allocation.
    The brain's alarm for when competing signals are present simultaneously.
    Chronic high conflict: exhausting, everything feels effortful and contested.
    """

    def __init__(self):
        super().__init__("AnteriorCingulateConflictNeocortical")
        self.conflict_level = 0.0
        self.error_signal = 0.0
        self.pain_signal = 0.0
        self.effort_allocation = 0.5
        self.conflict_history = []
        self.error_history = []
        self.chronic_conflict = False
        self.conflict_ticks = 0
        self.total_errors_detected = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        goal_strength = prior.get("PrefrontalGoalState", {}).get("active_goal_strength", 0.3)
        habit_strength = prior.get("StriatalHabitExecutor", {}).get("unified_habit_strength", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("prediction_error_negative", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        violation = prior.get("OrbitalFrontalEvaluator", {}).get("expectation_violation", 0.0)
        mode = prior.get("CaudateGoalHabitSwitcher", {}).get("current_mode", "transitioning")

        # Conflict: goal vs habit, expected vs actual, approach vs avoidance
        goal_habit_conflict = abs(goal_strength - habit_strength) * 0.4
        approach_avoid = fear * reward * 0.3
        expectation_conflict = violation * 0.3
        self.conflict_level = min(1.0, goal_habit_conflict + approach_avoid + expectation_conflict)
        if mode == "transitioning":
            self.conflict_level = min(1.0, self.conflict_level + 0.1)

        # Error signal: habenula-driven disappointment
        self.error_signal = habenula * 0.7 + violation * 0.3
        if self.error_signal > 0.4:
            self.total_errors_detected += 1

        # Pain signal: social/emotional pain
        self.pain_signal = fear * 0.4 + stress * 0.3 + habenula * 0.3

        # Effort allocation: how much cognitive effort is being recruited
        self.effort_allocation = min(1.0, self.conflict_level * 0.5 + self.error_signal * 0.3 + stress * 0.2)

        self.conflict_history.append(self.conflict_level)
        self.error_history.append(self.error_signal)
        for h in [self.conflict_history, self.error_history]:
            if len(h) > 40:
                h.pop(0)

        avg_conflict = sum(self.conflict_history[-15:]) / min(15, len(self.conflict_history))
        self.conflict_ticks = self.conflict_ticks + 1 if avg_conflict > 0.55 else max(0, self.conflict_ticks - 1)
        was_chronic = self.chronic_conflict
        self.chronic_conflict = self.conflict_ticks > 18
        if self.chronic_conflict and not was_chronic:
            self.feed_to_memory({"event": "acc_chronic_conflict", "conflict": round(avg_conflict, 3),
                                  "note": "Conflict chronically high — everything feels contested, effort cost elevated"})

        return {
            "conflict_level": round(self.conflict_level, 3),
            "error_signal": round(self.error_signal, 3),
            "pain_signal": round(self.pain_signal, 3),
            "effort_allocation": round(self.effort_allocation, 3),
            "total_errors_detected": self.total_errors_detected,
            "chronic_conflict": self.chronic_conflict,
        }

    def _overnight(self):
        self.conflict_ticks = max(0, self.conflict_ticks - 7)
        self.chronic_conflict = self.conflict_ticks > 18
        self.conflict_history.clear()
        self.error_history.clear()
        return {"overnight": "acc_conflict_reset"}
