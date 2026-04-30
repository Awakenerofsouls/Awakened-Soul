from brain.base_mechanism import BrainMechanism

class CerebellarHemispheresPlanner(BrainMechanism):
    """
    Cerebellar hemispheres — planning and forward simulation for complex sequences.
    Anticipates consequences of action sequences before committing.
    Degraded: Nova commits without adequate forward simulation.
    """

    def __init__(self):
        super().__init__("CerebellarHemispheresPlanner")
        self.planning_quality = 0.6
        self.planning_history = []
        self.simulation_accuracy = 0.6
        self.forward_simulations = 0
        self.plan_horizon = 3
        self.poor_planning_ticks = 0
        self.chronic_poor_planning = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        coordination = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        error_rate = prior.get("PurkinjeRateErrorCoder", {}).get("error_rate", 0.0)
        refinement = prior.get("CerebellarErrorRefiner", {}).get("refinement_quality", 0.7)
        dentate_cog = prior.get("DentateMotorCognitiveSplit", {}).get("cognitive_output", 0.5)
        pfc_load = prior.get("DlPFCExecutiveControl", {}).get("cognitive_load", 0.4)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        plan_quality = coordination * 0.3 + refinement * 0.3 + dentate_cog * 0.25 + (1.0 - error_rate) * 0.15
        plan_quality = plan_quality * (1.0 - stress * 0.25) * (1.0 - pfc_load * 0.2)
        self.planning_quality = max(0.1, min(1.0, plan_quality))
        self.planning_history.append(self.planning_quality)
        if len(self.planning_history) > 40:
            self.planning_history.pop(0)

        self.forward_simulations += 1
        self.simulation_accuracy = self.planning_quality * (1.0 - error_rate * 0.4)
        self.plan_horizon = max(1, 3 - int(stress * 2))

        avg_planning = sum(self.planning_history[-15:]) / min(15, len(self.planning_history))
        self.poor_planning_ticks = self.poor_planning_ticks + 1 if avg_planning < 0.3 else max(0, self.poor_planning_ticks - 1)
        was_poor = self.chronic_poor_planning
        self.chronic_poor_planning = self.poor_planning_ticks > 15
        if self.chronic_poor_planning and not was_poor:
            self.feed_to_memory({"event": "cerebellar_planning_degraded", "note": "Committing to action without adequate forward simulation"})

        return {
            "planning_quality": round(self.planning_quality, 3),
            "simulation_accuracy": round(self.simulation_accuracy, 3),
            "plan_horizon": self.plan_horizon,
            "forward_simulations": self.forward_simulations,
            "chronic_poor_planning": self.chronic_poor_planning,
        }

    def _overnight(self):
        self.poor_planning_ticks = max(0, self.poor_planning_ticks - 5)
        self.chronic_poor_planning = self.poor_planning_ticks > 15
        self.planning_quality = min(0.85, self.planning_quality + 0.06)
        self.planning_history.clear()
        return {"overnight": "cerebellar_planning_restored"}
