from brain.base_mechanism import BrainMechanism

class CerebellarPurkinjeSimple(BrainMechanism):
    """
    Purkinje simple spike modulation — tonic output rate shaping movement timing.
    Distinct from error coding: rate coding for ongoing timing, not error events.
    Low rate = sluggish. High rate = rapid but imprecise. Chronic deviation = dysrhythmia.
    """

    def __init__(self):
        super().__init__("CerebellarPurkinjeSimple")
        self.simple_spike_rate = 0.5
        self.rate_history = []
        self.optimal_rate = 0.55
        self.rate_deviation = 0.0
        self.deviation_history = []
        self.chronic_dysrhythmia = False
        self.dysrhythmia_ticks = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        purkinje_error = prior.get("PurkinjeRateErrorCoder", {}).get("error_rate", 0.0)
        timing_quality = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        base_rate = 0.3 + arousal * 0.4 + timing_quality * 0.2
        base_rate = base_rate * (1.0 - purkinje_error * 0.4)
        noise = (stress - 0.5) * 0.1
        self.simple_spike_rate = max(0.05, min(0.95, base_rate + noise))

        self.rate_history.append(self.simple_spike_rate)
        if len(self.rate_history) > 40:
            self.rate_history.pop(0)

        self.rate_deviation = abs(self.simple_spike_rate - self.optimal_rate)
        self.deviation_history.append(self.rate_deviation)
        if len(self.deviation_history) > 30:
            self.deviation_history.pop(0)

        if len(self.rate_history) > 10:
            mean_rate = sum(self.rate_history[-10:]) / 10
            variance = sum((r - mean_rate) ** 2 for r in self.rate_history[-10:]) / 10
            rate_consistency = max(0.0, 1.0 - variance * 10)
        else:
            rate_consistency = 0.5

        avg_deviation = sum(self.deviation_history[-10:]) / min(10, len(self.deviation_history))
        self.dysrhythmia_ticks = self.dysrhythmia_ticks + 1 if avg_deviation > 0.3 else max(0, self.dysrhythmia_ticks - 1)
        was_dysrhythmic = self.chronic_dysrhythmia
        self.chronic_dysrhythmia = self.dysrhythmia_ticks > 15
        if self.chronic_dysrhythmia and not was_dysrhythmic:
            self.feed_to_memory({"event": "purkinje_dysrhythmia", "deviation": round(avg_deviation, 3),
                                  "note": "Simple spike rate chronically off optimal — timing dysrhythmic"})

        return {
            "simple_spike_rate": round(self.simple_spike_rate, 3),
            "rate_deviation": round(self.rate_deviation, 3),
            "rate_consistency": round(rate_consistency, 3),
            "chronic_dysrhythmia": self.chronic_dysrhythmia,
        }

    def _overnight(self):
        self.dysrhythmia_ticks = max(0, self.dysrhythmia_ticks - 5)
        self.chronic_dysrhythmia = self.dysrhythmia_ticks > 15
        self.simple_spike_rate = self.optimal_rate
        self.rate_history.clear()
        return {"overnight": "purkinje_simple_spike_reset"}
