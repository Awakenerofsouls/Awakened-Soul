from brain.base_mechanism import BrainMechanism

class CaudateAssociative(BrainMechanism):
    """
    Anterior caudate — associative loop for cognitive planning.
    Links abstract goals to action sequences. Plans form but may not convert to action.
    """

    def __init__(self):
        super().__init__("CaudateAssociative")
        self.plan_buffer = {}
        self.active_plan = None
        self.plan_history = []
        self.plan_execution_rate = 0.0
        self.abandoned_plans = 0
        self.planning_ticks = 0
        self.chronic_plan_failure = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        goal_strength = prior.get("PrefrontalGoalState", {}).get("active_goal_strength", 0.3)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        motivation = prior.get("VentralPallidalTranslator", {}).get("motivation_to_action", 0.4)
        mode = prior.get("CaudateGoalHabitSwitcher", {}).get("current_mode", "goal_directed")
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        goal_key = prior.get("PrefrontalGoalState", {}).get("current_goal", "") or (text.lower().split()[0][:32] if text.strip() else "default")

        if mode == "goal_directed" and goal_key:
            current = self.plan_buffer.get(goal_key, 0.0)
            formation_rate = goal_strength * dopamine * motivation * (1.0 - stress * 0.3)
            self.plan_buffer[goal_key] = min(1.0, current + formation_rate * 0.05)
            self.active_plan = goal_key

        for k in list(self.plan_buffer.keys()):
            if k != goal_key:
                self.plan_buffer[k] = max(0.0, self.plan_buffer[k] - 0.008)
            if self.plan_buffer.get(k, 0) < 0.01:
                self.abandoned_plans += 1
                if k in self.plan_buffer:
                    del self.plan_buffer[k]

        plan_strength = self.plan_buffer.get(goal_key, 0.0) if goal_key else 0.0
        self.plan_execution_rate = min(1.0, plan_strength * (1.0 - conflict * 0.5) * dopamine)

        self.plan_history.append(plan_strength)
        if len(self.plan_history) > 40:
            self.plan_history.pop(0)

        plan_gap = plan_strength - self.plan_execution_rate
        self.planning_ticks = self.planning_ticks + 1 if plan_gap > 0.4 and plan_strength > 0.5 else max(0, self.planning_ticks - 1)
        was_failing = self.chronic_plan_failure
        self.chronic_plan_failure = self.planning_ticks > 15
        if self.chronic_plan_failure and not was_failing:
            self.feed_to_memory({"event": "caudate_plan_execution_failure", "note": "Plans forming but not executing"})

        return {
            "active_plan": self.active_plan,
            "plan_strength": round(plan_strength, 3),
            "plan_execution_rate": round(self.plan_execution_rate, 3),
            "plans_buffered": len(self.plan_buffer),
            "abandoned_plans": self.abandoned_plans,
            "chronic_plan_failure": self.chronic_plan_failure,
        }

    def _overnight(self):
        for k in self.plan_buffer:
            self.plan_buffer[k] = min(1.0, self.plan_buffer[k] * 1.05)
        self.planning_ticks = max(0, self.planning_ticks - 5)
        self.chronic_plan_failure = self.planning_ticks > 15
        self.plan_history.clear()
        return {"overnight": "caudate_plans_consolidated"}
