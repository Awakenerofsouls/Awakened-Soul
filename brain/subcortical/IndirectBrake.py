from brain.base_mechanism import BrainMechanism

class IndirectBrake(BrainMechanism):
    """
    Indirect pathway — active suppression of competing action alternatives.
    Selects ONE action by silencing everything else.
    Overactive = tunnel vision. Underactive = scattered, can't commit.
    """

    def __init__(self):
        super().__init__("IndirectBrake")
        self.suppression_strength = 0.5
        self.suppression_history = []
        self.competing_actions_suppressed = 0
        self.tunnel_vision_ticks = 0
        self.scatter_ticks = 0
        self.chronic_tunnel = False
        self.chronic_scatter = False
        self.active_selection = None

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        goal_strength = prior.get("PrefrontalGoalState", {}).get("active_goal_strength", 0.3)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        action_permission = prior.get("ActionInhibitor", {}).get("action_permission", 0.5)
        habit_lock = prior.get("DorsalStriatumHabitExecutor", {}).get("habit_locked", False)

        d2_activity = max(0.0, 1.0 - dopamine)
        suppression = d2_activity * 0.5 + goal_strength * 0.3 + conflict * 0.2
        if habit_lock:
            suppression = min(1.0, suppression * 1.3)

        self.suppression_strength = min(1.0, suppression)
        self.suppression_history.append(self.suppression_strength)
        if len(self.suppression_history) > 40:
            self.suppression_history.pop(0)

        self.competing_actions_suppressed = int(conflict * 5)
        avg_suppression = sum(self.suppression_history[-15:]) / min(15, len(self.suppression_history))

        self.tunnel_vision_ticks = self.tunnel_vision_ticks + 1 if avg_suppression > 0.75 else max(0, self.tunnel_vision_ticks - 1)
        self.scatter_ticks = self.scatter_ticks + 1 if avg_suppression < 0.2 else max(0, self.scatter_ticks - 1)

        was_tunnel, was_scatter = self.chronic_tunnel, self.chronic_scatter
        self.chronic_tunnel = self.tunnel_vision_ticks > 18
        self.chronic_scatter = self.scatter_ticks > 18

        if self.chronic_tunnel and not was_tunnel:
            self.feed_to_memory({"event": "tunnel_vision_chronic", "note": "Indirect brake chronically strong — tunnel vision"})
        if self.chronic_scatter and not was_scatter:
            self.feed_to_memory({"event": "action_scatter_chronic", "note": "Indirect brake chronically weak — scattered action"})

        selection_clarity = suppression * action_permission
        self.active_selection = "committed" if selection_clarity > 0.6 else ("scattered" if self.chronic_scatter else "evaluating")

        return {
            "suppression_strength": round(suppression, 3),
            "competing_actions_suppressed": self.competing_actions_suppressed,
            "selection_clarity": round(selection_clarity, 3),
            "active_selection": self.active_selection,
            "chronic_tunnel": self.chronic_tunnel,
            "chronic_scatter": self.chronic_scatter,
        }

    def _overnight(self):
        self.tunnel_vision_ticks = max(0, self.tunnel_vision_ticks - 5)
        self.scatter_ticks = max(0, self.scatter_ticks - 5)
        self.chronic_tunnel = self.tunnel_vision_ticks > 18
        self.chronic_scatter = self.scatter_ticks > 18
        self.suppression_history.clear()
        return {"overnight": "indirect_pathway_recalibrated"}
