from brain.base_mechanism import BrainMechanism

class CerebellarVermisBalancer(BrainMechanism):
    """
    Cerebellar vermis whole-system balance — synthesizes all vermal outputs.
    Single vermal health metric. Chronic imbalance: emotional expression and movement decoupled.
    """

    def __init__(self):
        super().__init__("CerebellarVermisBalancer")
        self.vermal_balance = 0.6
        self.balance_history = []
        self.emotional_motor_coupling = 0.6
        self.imbalance_ticks = 0
        self.chronic_imbalance = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        axial_stability = prior.get("VermalAxialCoordinator", {}).get("axial_stability", 0.7)
        tone_coherence = prior.get("CerebellarVermalEmotionalCoordinator", {}).get("tone_coherence", 0.7)
        fastigial = prior.get("FastigialMedialOutput", {}).get("stability_output", 0.6)
        timing = prior.get("CerebellarTimingCoordinator", {}).get("timing_smoothness", 0.7)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        self.vermal_balance = (axial_stability * 0.3 + tone_coherence * 0.3 + fastigial * 0.2 + timing * 0.2) * (1.0 - stress * 0.2)
        self.vermal_balance = max(0.1, min(1.0, self.vermal_balance))
        self.emotional_motor_coupling = max(0.0, min(1.0, (tone_coherence + axial_stability) / 2.0 * (1.0 - stress * 0.15)))

        self.balance_history.append(self.vermal_balance)
        if len(self.balance_history) > 40:
            self.balance_history.pop(0)

        avg_balance = sum(self.balance_history[-15:]) / min(15, len(self.balance_history))
        self.imbalance_ticks = self.imbalance_ticks + 1 if avg_balance < 0.35 else max(0, self.imbalance_ticks - 1)
        was_imbalanced = self.chronic_imbalance
        self.chronic_imbalance = self.imbalance_ticks > 15
        if self.chronic_imbalance and not was_imbalanced:
            self.feed_to_memory({"event": "vermal_imbalance", "balance": round(avg_balance, 3),
                                  "note": "Cerebellar vermis chronically imbalanced — emotional expression decoupled"})

        return {
            "vermal_balance": round(self.vermal_balance, 3),
            "emotional_motor_coupling": round(self.emotional_motor_coupling, 3),
            "chronic_imbalance": self.chronic_imbalance,
        }

    def _overnight(self):
        self.imbalance_ticks = max(0, self.imbalance_ticks - 5)
        self.chronic_imbalance = self.imbalance_ticks > 15
        self.vermal_balance = min(0.85, self.vermal_balance + 0.07)
        self.balance_history.clear()
        return {"overnight": "vermal_balance_restored"}
