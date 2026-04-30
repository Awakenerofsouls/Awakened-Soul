from brain.base_mechanism import BrainMechanism

class CorticoStriatalHighway(BrainMechanism):
    """
    Cortico-striatal white matter — action selection highway.
    Carries goal representations from PFC to striatum for habit/action decisions.
    Degraded: goals form in PFC but never reach action selection — intention-action gap.
    """

    def __init__(self):
        super().__init__("CorticoStriatalHighway")
        self.highway_throughput = 0.6
        self.goal_to_action_fidelity = 0.6
        self.habit_modulation = 0.0
        self.throughput_history = []
        self.gap_ticks = 0
        self.chronic_gap = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        goal_strength = prior.get("PrefrontalGoalState", {}).get("active_goal_strength", 0.5)
        caudate_plan = prior.get("CaudateAssociative", {}).get("plan_execution_rate", 0.0)
        matrix_output = prior.get("StriatumMatrixCompartment", {}).get("matrix_output", 0.5)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        habit_strength = prior.get("StriatalHabitExecutor", {}).get("unified_habit_strength", 0.3)

        # Throughput: how well PFC goals reach striatum
        self.highway_throughput = (goal_strength * 0.4 + dopamine * 0.3 + matrix_output * 0.3) * (1.0 - stress * 0.2)
        self.highway_throughput = max(0.1, min(1.0, self.highway_throughput))

        # Fidelity: do the goals that arrive still match what PFC intended?
        self.goal_to_action_fidelity = self.highway_throughput * (1.0 - stress * 0.15)

        # Habit modulation: strong habits can reroute the highway
        self.habit_modulation = habit_strength * 0.5

        self.throughput_history.append(self.highway_throughput)
        if len(self.throughput_history) > 40:
            self.throughput_history.pop(0)

        avg_throughput = sum(self.throughput_history[-15:]) / min(15, len(self.throughput_history))
        # Gap: goal strength high but execution low
        gap = goal_strength - caudate_plan
        self.gap_ticks = self.gap_ticks + 1 if gap > 0.4 and avg_throughput < 0.3 else max(0, self.gap_ticks - 1)
        was_gap = self.chronic_gap
        self.chronic_gap = self.gap_ticks > 15
        if self.chronic_gap and not was_gap:
            self.feed_to_memory({"event": "corticostriatal_gap",
                                  "note": "Goals not reaching striatum — chronic intention-action disconnect"})

        return {
            "highway_throughput": round(self.highway_throughput, 3),
            "goal_to_action_fidelity": round(self.goal_to_action_fidelity, 3),
            "habit_modulation": round(self.habit_modulation, 3),
            "chronic_gap": self.chronic_gap,
        }

    def _overnight(self):
        self.gap_ticks = max(0, self.gap_ticks - 5)
        self.chronic_gap = self.gap_ticks > 15
        self.throughput_history.clear()
        return {"overnight": "corticostriatal_highway_reset"}
