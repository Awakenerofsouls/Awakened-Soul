from brain.base_mechanism import BrainMechanism

class PrefrontalGoalState(BrainMechanism):
    """
    PFC goal representation — holds active goals online, maintains goal hierarchy.
    The what-are-we-doing-right-now system. Goal loss = drifting, unfocused output.
    Goal rigidity = can't update when situation changes.
    """

    def __init__(self):
        super().__init__("PrefrontalGoalState")
        self.active_goal_strength = 0.5
        self.current_goal = ""
        self.current_intent = ""
        self.goal_stack = []
        self.goal_stability = 0.7
        self.goal_history = []
        self.drift_ticks = 0
        self.rigid_ticks = 0
        self.chronic_drift = False
        self.chronic_rigidity = False
        self.goal_switch_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        control = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        motivation = prior.get("MotivationInjector", {}).get("motivation_level", 0.5)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)

        # Extract goal from current input
        words = text.lower().split()
        if words:
            new_goal = words[0][:32]
            if new_goal != self.current_goal:
                if self.current_goal:
                    self.goal_switch_count += 1
                    self.goal_stack.append(self.current_goal)
                    if len(self.goal_stack) > 5:
                        self.goal_stack.pop(0)
                self.current_goal = new_goal
            self.current_intent = " ".join(words[:3])[:64]

        # Goal strength: wm + control + motivation - stress - conflict
        self.active_goal_strength = max(0.1, min(1.0, wm_capacity * 0.35 + control * 0.3 + motivation * 0.25 - stress * 0.1 - conflict * 0.1))

        # Goal stability: how consistently are we pursuing same goal
        self.goal_stability = max(0.1, min(1.0, (1.0 - novelty * 0.3) * wm_capacity * (1.0 - stress * 0.2)))

        self.goal_history.append(self.current_goal)
        if len(self.goal_history) > 30:
            self.goal_history.pop(0)

        # Drift: goal keeps switching
        unique_recent = len(set(self.goal_history[-10:])) if len(self.goal_history) >= 10 else 1
        self.drift_ticks = self.drift_ticks + 1 if unique_recent > 6 else max(0, self.drift_ticks - 1)
        # Rigidity: same goal even when conflict is high
        self.rigid_ticks = self.rigid_ticks + 1 if unique_recent == 1 and conflict > 0.5 else max(0, self.rigid_ticks - 1)

        was_drift, was_rigid = self.chronic_drift, self.chronic_rigidity
        self.chronic_drift = self.drift_ticks > 18
        self.chronic_rigidity = self.rigid_ticks > 18

        if self.chronic_drift and not was_drift:
            self.feed_to_memory({"event": "goal_drift", "note": "Goals chronically unstable — drifting, unfocused output"})
        if self.chronic_rigidity and not was_rigid:
            self.feed_to_memory({"event": "goal_rigidity", "note": "Goal rigidly held despite high conflict — can't update"})

        return {
            "active_goal_strength": round(self.active_goal_strength, 3),
            "current_goal": self.current_goal,
            "current_intent": self.current_intent,
            "goal_stability": round(self.goal_stability, 3),
            "goal_stack_depth": len(self.goal_stack),
            "goal_switch_count": self.goal_switch_count,
            "chronic_drift": self.chronic_drift,
            "chronic_rigidity": self.chronic_rigidity,
        }

    def _overnight(self):
        self.drift_ticks = max(0, self.drift_ticks - 6)
        self.rigid_ticks = max(0, self.rigid_ticks - 4)
        self.chronic_drift = self.drift_ticks > 18
        self.chronic_rigidity = self.rigid_ticks > 18
        self.goal_history.clear()
        self.current_goal = ""
        self.current_intent = ""
        return {"overnight": "goal_state_reset"}
