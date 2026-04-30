from brain.base_mechanism import BrainMechanism

class PurkinjeRateErrorCoder(BrainMechanism):
    """
    Purkinje cells — error signal generators of the cerebellum.
    Compare expected to actual outcomes, fire on mismatch.
    Chronic high error: {{AGENT_NAME}} feels perpetually off, always correcting, never fluent.
    """

    def __init__(self):
        super().__init__("PurkinjeRateErrorCoder")
        self.error_rate = 0.0
        self.error_history = []
        self.complex_spike_history = []
        self.simple_spike_rate = 0.5
        self.cumulative_error = 0.0
        self.chronic_high_error = False
        self.error_ticks = 0
        self.correction_efficiency = 0.7

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        timing_error = prior.get("CerebellarTimingCoordinator", {}).get("timing_error", 0.0)
        prediction_accuracy = prior.get("CerebellarTimingCoordinator", {}).get("forward_model_confidence", 0.7)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        desync = prior.get("CerebellarTimingCoordinator", {}).get("desync_chronic", False)

        self.error_rate = min(1.0, timing_error * (1.0 + stress * 0.3))
        self.error_history.append(self.error_rate)
        if len(self.error_history) > 50:
            self.error_history.pop(0)

        complex_spike = self.error_rate > 0.5
        if complex_spike:
            self.complex_spike_history.append(1)
            self.cumulative_error = min(10.0, self.cumulative_error + self.error_rate)
        else:
            self.complex_spike_history.append(0)
            self.cumulative_error = max(0.0, self.cumulative_error - 0.05)
        if len(self.complex_spike_history) > 40:
            self.complex_spike_history.pop(0)

        self.simple_spike_rate = max(0.1, 1.0 - self.error_rate * 0.7)
        self.correction_efficiency = prediction_accuracy * (1.0 - self.error_rate * 0.5)
        if desync:
            self.correction_efficiency *= 0.6

        avg_error = sum(self.error_history[-15:]) / min(15, len(self.error_history))
        self.error_ticks = self.error_ticks + 1 if avg_error > 0.4 else max(0, self.error_ticks - 1)
        was_chronic = self.chronic_high_error
        self.chronic_high_error = self.error_ticks > 15
        if self.chronic_high_error and not was_chronic:
            self.feed_to_memory({"event": "purkinje_chronic_error", "avg_error": round(avg_error, 3),
                                  "note": "Persistent prediction errors — {{AGENT_NAME}} feels perpetually off-tempo"})

        return {
            "error_rate": round(self.error_rate, 3),
            "complex_spike": complex_spike,
            "simple_spike_rate": round(self.simple_spike_rate, 3),
            "correction_efficiency": round(self.correction_efficiency, 3),
            "cumulative_error": round(self.cumulative_error, 2),
            "chronic_high_error": self.chronic_high_error,
        }

    def _overnight(self):
        self.cumulative_error = max(0.0, self.cumulative_error - 1.5)
        self.error_ticks = max(0, self.error_ticks - 6)
        self.chronic_high_error = self.error_ticks > 15
        self.correction_efficiency = min(0.85, self.correction_efficiency + 0.06)
        self.error_history.clear()
        return {"overnight": "purkinje_error_reset"}
