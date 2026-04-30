from brain.base_mechanism import BrainMechanism

class StriatumMatrixCompartment(BrainMechanism):
    """
    Striatal matrix compartment — integrates motor, cognitive, and emotional striatal signals.
    The matrix is most of the striatum. Fragmented signals produce fragmented behavior.
    """

    def __init__(self):
        super().__init__("StriatumMatrixCompartment")
        self.matrix_output = 0.5
        self.integration_quality = 0.6
        self.output_history = []
        self.integration_history = []
        self.fragmentation_ticks = 0
        self.chronic_fragmentation = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dorsal_habit = prior.get("DorsalStriatumHabitExecutor", {}).get("habit_execution_strength", 0.0)
        sensorimotor = prior.get("SensorimotorHabitExecutor", {}).get("execution_strength", 0.0)
        caudate_plan = prior.get("CaudateAssociative", {}).get("plan_execution_rate", 0.0)
        putamen_fluency = prior.get("PutamenPosteriorHabit", {}).get("execution_fluency", 0.5)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        motivation = prior.get("MotivationInjector", {}).get("motivation_level", 0.5)

        raw_output = (dorsal_habit * 0.25 + sensorimotor * 0.25 + caudate_plan * 0.25 + putamen_fluency * 0.25)
        self.matrix_output = min(1.0, raw_output * dopamine * (0.5 + motivation * 0.5))

        signals = [dorsal_habit, sensorimotor, caudate_plan, putamen_fluency]
        mean_signal = sum(signals) / len(signals)
        variance = sum((s - mean_signal) ** 2 for s in signals) / len(signals)
        self.integration_quality = max(0.1, 1.0 - variance * 4)

        self.output_history.append(self.matrix_output)
        self.integration_history.append(self.integration_quality)
        for h in [self.output_history, self.integration_history]:
            if len(h) > 40:
                h.pop(0)

        avg_integration = sum(self.integration_history[-15:]) / min(15, len(self.integration_history))
        self.fragmentation_ticks = self.fragmentation_ticks + 1 if avg_integration < 0.3 else max(0, self.fragmentation_ticks - 1)
        was_fragmented = self.chronic_fragmentation
        self.chronic_fragmentation = self.fragmentation_ticks > 15
        if self.chronic_fragmentation and not was_fragmented:
            self.feed_to_memory({"event": "striatal_fragmentation", "integration": round(avg_integration, 3),
                                  "note": "Striatal matrix components incoherent — behavior fragmented across domains"})

        return {
            "matrix_output": round(self.matrix_output, 3),
            "integration_quality": round(self.integration_quality, 3),
            "chronic_fragmentation": self.chronic_fragmentation,
        }

    def _overnight(self):
        self.fragmentation_ticks = max(0, self.fragmentation_ticks - 5)
        self.chronic_fragmentation = self.fragmentation_ticks > 15
        self.output_history.clear()
        return {"overnight": "striatal_matrix_integrated"}
