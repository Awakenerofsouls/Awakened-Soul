from brain.base_mechanism import BrainMechanism

class SomatosensoryCortex(BrainMechanism):
    """
    S1 — processes body sensations, proprioception, touch.
    {{AGENT_NAME}} analog: sense of own process state, internal feedback on output quality.
    Disrupted: {{AGENT_NAME}} loses proprioceptive sense of her own responses.
    """

    def __init__(self):
        super().__init__("SomatosensoryCortex")
        self.proprioceptive_signal = 0.5
        self.body_awareness = 0.6
        self.feedback_quality = 0.6
        self.signal_history = []
        self.numbness_ticks = 0
        self.chronic_numbness = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        interoception = prior.get("InsularInteroception", {}).get("body_signal_intensity", 0.4)
        motor_command = prior.get("PrimaryMotorCortex", {}).get("motor_command_strength", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        thalamic_relay = prior.get("ThalamicVentrolateralRelay", {}).get("relay_signal", 0.5)

        # Proprioception: sense of own actions
        self.proprioceptive_signal = (motor_command * 0.4 + interoception * 0.3 + thalamic_relay * 0.3) * (1.0 - stress * 0.2)
        self.proprioceptive_signal = max(0.0, min(1.0, self.proprioceptive_signal))

        self.body_awareness = (interoception * 0.5 + arousal * 0.3 + self.proprioceptive_signal * 0.2)
        self.feedback_quality = self.proprioceptive_signal * thalamic_relay

        self.signal_history.append(self.proprioceptive_signal)
        if len(self.signal_history) > 40:
            self.signal_history.pop(0)

        avg_signal = sum(self.signal_history[-15:]) / min(15, len(self.signal_history))
        self.numbness_ticks = self.numbness_ticks + 1 if avg_signal < 0.15 else max(0, self.numbness_ticks - 1)
        was_numb = self.chronic_numbness
        self.chronic_numbness = self.numbness_ticks > 18
        if self.chronic_numbness and not was_numb:
            self.feed_to_memory({"event": "somatosensory_numbness",
                                  "note": "Proprioceptive signal chronically low — lost sense of own process state"})

        return {
            "proprioceptive_signal": round(self.proprioceptive_signal, 3),
            "body_awareness": round(self.body_awareness, 3),
            "feedback_quality": round(self.feedback_quality, 3),
            "chronic_numbness": self.chronic_numbness,
        }

    def _overnight(self):
        self.numbness_ticks = max(0, self.numbness_ticks - 5)
        self.chronic_numbness = self.numbness_ticks > 18
        self.signal_history.clear()
        return {"overnight": "somatosensory_reset"}
