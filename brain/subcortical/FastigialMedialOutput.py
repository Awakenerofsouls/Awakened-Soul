from brain.base_mechanism import BrainMechanism

class FastigialMedialOutput(BrainMechanism):
    """
    Fastigial nucleus — medial cerebellar output for postural/vestibular stability.
    Nova analog: baseline conversational stability, recovery speed after disruption.
    Depleted: knocked off-balance easily, slow to restabilize.
    """

    def __init__(self):
        super().__init__("FastigialMedialOutput")
        self.stability_output = 0.6
        self.recovery_rate = 0.15
        self.perturbation_history = []
        self.stability_history = []
        self.slow_recovery_ticks = 0
        self.chronic_slow_recovery = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        axial_stability = prior.get("VermalAxialCoordinator", {}).get("axial_stability", 0.7)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        burst = prior.get("ReboundBurstGenerator", {}).get("burst_active", False)
        timing = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)

        perturbation = fear * 0.4 + stress * 0.3 + (0.3 if burst else 0.0)
        self.perturbation_history.append(perturbation)
        if len(self.perturbation_history) > 30:
            self.perturbation_history.pop(0)

        target_stability = axial_stability * timing * (1.0 - perturbation * 0.5)
        self.stability_output += (target_stability - self.stability_output) * self.recovery_rate
        self.stability_output = max(0.0, min(1.0, self.stability_output))

        recent_perturb = sum(self.perturbation_history[-5:]) / min(5, len(self.perturbation_history))
        effective_recovery = self.recovery_rate * (1.0 - stress * 0.3) * timing
        if recent_perturb > 0.4:
            effective_recovery *= 0.5

        self.stability_history.append(self.stability_output)
        if len(self.stability_history) > 40:
            self.stability_history.pop(0)

        self.slow_recovery_ticks = self.slow_recovery_ticks + 1 if effective_recovery < 0.05 and recent_perturb > 0.3 else max(0, self.slow_recovery_ticks - 1)
        was_slow = self.chronic_slow_recovery
        self.chronic_slow_recovery = self.slow_recovery_ticks > 15
        if self.chronic_slow_recovery and not was_slow:
            self.feed_to_memory({"event": "fastigial_slow_recovery", "note": "Recovery from disruption chronically slow"})

        return {
            "stability_output": round(self.stability_output, 3),
            "recovery_rate": round(effective_recovery, 3),
            "perturbation_level": round(perturbation, 3),
            "chronic_slow_recovery": self.chronic_slow_recovery,
        }

    def _overnight(self):
        self.slow_recovery_ticks = max(0, self.slow_recovery_ticks - 5)
        self.chronic_slow_recovery = self.slow_recovery_ticks > 15
        self.stability_output = min(0.85, self.stability_output + 0.1)
        self.perturbation_history.clear()
        return {"overnight": "fastigial_stability_restored"}
