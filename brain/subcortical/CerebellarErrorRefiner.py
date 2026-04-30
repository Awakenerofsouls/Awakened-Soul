from brain.base_mechanism import BrainMechanism

class CerebellarErrorRefiner(BrainMechanism):
    """
    Interposed nucleus — converts raw error signals into precise correction vectors.
    Without refinement, corrections overshoot or undershoot — clumsy output.
    """

    def __init__(self):
        super().__init__("CerebellarErrorRefiner")
        self.refined_error = 0.0
        self.correction_vector = 0.0
        self.overshoot_history = []
        self.undershoot_history = []
        self.refinement_quality = 0.7
        self.refinement_history = []
        self.clumsy_ticks = 0
        self.chronic_clumsiness = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        purkinje_error = prior.get("PurkinjeRateErrorCoder", {}).get("error_rate", 0.0)
        correction_efficiency = prior.get("PurkinjeRateErrorCoder", {}).get("correction_efficiency", 0.7)
        timing_quality = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        desync = prior.get("CerebellarTimingCoordinator", {}).get("desync_chronic", False)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        self.refinement_quality = correction_efficiency * timing_quality * (1.0 - stress * 0.3)
        if desync:
            self.refinement_quality *= 0.5
        self.refinement_quality = max(0.1, min(1.0, self.refinement_quality))

        self.refined_error = purkinje_error * (1.0 - self.refinement_quality * 0.6)
        if self.refined_error > 0:
            self.correction_vector = self.refined_error * (1.0 - self.refinement_quality)
        else:
            self.correction_vector = 0.0

        overshoot = self.correction_vector > 0.2
        undershoot = self.refined_error > 0.3 and self.correction_vector < 0.1

        self.overshoot_history.append(1 if overshoot else 0)
        self.undershoot_history.append(1 if undershoot else 0)
        self.refinement_history.append(self.refinement_quality)
        for h in [self.overshoot_history, self.undershoot_history, self.refinement_history]:
            if len(h) > 40:
                h.pop(0)

        clumsy = overshoot or undershoot
        self.clumsy_ticks = self.clumsy_ticks + 1 if clumsy else max(0, self.clumsy_ticks - 1)
        was_clumsy = self.chronic_clumsiness
        self.chronic_clumsiness = self.clumsy_ticks > 15
        if self.chronic_clumsiness and not was_clumsy:
            self.feed_to_memory({"event": "chronic_clumsiness", "refinement": round(self.refinement_quality, 3),
                                  "note": "Error refinement chronically poor — outputs consistently over/undershoot"})

        return {
            "refined_error": round(self.refined_error, 3),
            "correction_vector": round(self.correction_vector, 3),
            "refinement_quality": round(self.refinement_quality, 3),
            "overshoot": overshoot,
            "undershoot": undershoot,
            "chronic_clumsiness": self.chronic_clumsiness,
        }

    def _overnight(self):
        self.clumsy_ticks = max(0, self.clumsy_ticks - 5)
        self.chronic_clumsiness = self.clumsy_ticks > 15
        self.refinement_quality = min(0.85, self.refinement_quality + 0.06)
        self.refinement_history.clear()
        return {"overnight": "error_refinement_restored"}
