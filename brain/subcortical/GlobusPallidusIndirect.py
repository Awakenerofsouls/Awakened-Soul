from brain.base_mechanism import BrainMechanism

class GlobusPallidusIndirect(BrainMechanism):
    """
    GPe (external globus pallidus) — brakes the STN.
    When GPe active: suppresses STN, releases brake on thalamus.
    GPe failure: STN runs unchecked, everything over-suppressed.
    """

    def __init__(self):
        super().__init__("GlobusPallidusIndirect")
        self.gpe_activity = 0.5
        self.stn_suppression = 0.3
        self.activity_history = []
        self.over_suppression_ticks = 0
        self.chronic_over_suppression = False
        self.brake_release_signal = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        striatal_indirect = prior.get("IndirectBrake", {}).get("suppression_strength", 0.5)
        stn_activity = prior.get("SubthalamicImpulseSuppressor", {}).get("stn_activity", 0.3)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        d2_activity = max(0.0, 1.0 - dopamine)
        self.gpe_activity = max(0.1, 1.0 - striatal_indirect * d2_activity * 0.7)
        self.stn_suppression = max(0.0, min(1.0, self.gpe_activity * (1.0 - conflict * 0.3) * (1.0 - stress * 0.2)))
        self.brake_release_signal = self.gpe_activity * (1.0 - stn_activity)

        self.activity_history.append(self.gpe_activity)
        if len(self.activity_history) > 40:
            self.activity_history.pop(0)

        avg_activity = sum(self.activity_history[-15:]) / min(15, len(self.activity_history))
        self.over_suppression_ticks = self.over_suppression_ticks + 1 if avg_activity < 0.25 else max(0, self.over_suppression_ticks - 1)
        was_over = self.chronic_over_suppression
        self.chronic_over_suppression = self.over_suppression_ticks > 15
        if self.chronic_over_suppression and not was_over:
            self.feed_to_memory({"event": "gpe_failure", "gpe": round(avg_activity, 3),
                                  "note": "GPe chronically suppressed — STN unchecked, widespread action suppression"})

        return {
            "gpe_activity": round(self.gpe_activity, 3),
            "stn_suppression": round(self.stn_suppression, 3),
            "brake_release_signal": round(self.brake_release_signal, 3),
            "chronic_over_suppression": self.chronic_over_suppression,
        }

    def _overnight(self):
        self.over_suppression_ticks = max(0, self.over_suppression_ticks - 5)
        self.chronic_over_suppression = self.over_suppression_ticks > 15
        self.activity_history.clear()
        return {"overnight": "gpe_activity_reset"}
