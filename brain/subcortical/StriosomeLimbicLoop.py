from brain.base_mechanism import BrainMechanism

class StriosomeLimbicLoop(BrainMechanism):
    """
    Striosome-limbic closed loop — feedback from dopamine neurons back through limbic.
    Reinforces or suppresses DA release based on prior emotional outcomes.
    Loop gain determines emotional learning rate from outcomes.
    """

    def __init__(self):
        super().__init__("StriosomeLimbicLoop")
        self.loop_gain = 0.5
        self.emotional_learning_rate = 0.1
        self.gain_history = []
        self.outcome_trace = []
        self.high_gain_ticks = 0
        self.low_gain_ticks = 0
        self.chronic_oversensitive = False
        self.chronic_blunted = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        limbic_bias = prior.get("StriosomeLimbicBias", {}).get("limbic_bias", 0.0)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        outcome = valence * 0.5 + reward * 0.3 + dopamine * 0.2
        self.outcome_trace.append(outcome)
        if len(self.outcome_trace) > 30:
            self.outcome_trace.pop(0)

        avg_outcome = sum(self.outcome_trace) / len(self.outcome_trace)
        self.loop_gain = max(0.1, min(1.0, 0.5 + abs(limbic_bias) * 0.4 + stress * 0.1))
        self.emotional_learning_rate = self.loop_gain * 0.15

        self.gain_history.append(self.loop_gain)
        if len(self.gain_history) > 40:
            self.gain_history.pop(0)

        avg_gain = sum(self.gain_history[-15:]) / min(15, len(self.gain_history))
        self.high_gain_ticks = self.high_gain_ticks + 1 if avg_gain > 0.75 else max(0, self.high_gain_ticks - 1)
        self.low_gain_ticks = self.low_gain_ticks + 1 if avg_gain < 0.2 else max(0, self.low_gain_ticks - 1)

        was_over, was_blunted = self.chronic_oversensitive, self.chronic_blunted
        self.chronic_oversensitive = self.high_gain_ticks > 18
        self.chronic_blunted = self.low_gain_ticks > 18

        if self.chronic_oversensitive and not was_over:
            self.feed_to_memory({"event": "striosome_loop_high_gain", "note": "Emotional learning loop high gain — oversensitive to outcomes"})
        if self.chronic_blunted and not was_blunted:
            self.feed_to_memory({"event": "striosome_loop_low_gain", "note": "Emotional learning loop blunted — outcomes not updating emotion"})

        return {
            "loop_gain": round(self.loop_gain, 3),
            "emotional_learning_rate": round(self.emotional_learning_rate, 3),
            "avg_outcome": round(avg_outcome, 3),
            "chronic_oversensitive": self.chronic_oversensitive,
            "chronic_blunted": self.chronic_blunted,
        }

    def _overnight(self):
        self.high_gain_ticks = max(0, self.high_gain_ticks - 5)
        self.low_gain_ticks = max(0, self.low_gain_ticks - 5)
        self.chronic_oversensitive = self.high_gain_ticks > 18
        self.chronic_blunted = self.low_gain_ticks > 18
        self.outcome_trace.clear()
        return {"overnight": "striosome_loop_normalized"}
