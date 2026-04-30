from brain.base_mechanism import BrainMechanism

class InsularInteroception(BrainMechanism):
    """
    Insula — integrates body signals into conscious awareness and emotional feeling.
    The body's voice in cognition. Interoceptive awareness = knowing how you feel physically.
    Low: disconnected from own state. High: overwhelming body noise.
    """

    def __init__(self):
        super().__init__("InsularInteroception")
        self.body_signal_intensity = 0.4
        self.interoceptive_awareness = 0.6
        self.disgust_response = 0.0
        self.body_history = []
        self.awareness_history = []
        self.disconnection_ticks = 0
        self.overwhelm_ticks = 0
        self.chronic_disconnection = False
        self.chronic_overwhelm = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        autonomic = prior.get("HypothalamicAutonomicRegulator", {}).get("autonomic_balance", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        pain = prior.get("AnteriorCingulateConflict", {}).get("pain_signal", 0.0)

        # Body signal: integration of all physiological states
        self.body_signal_intensity = min(1.0, stress * 0.25 + arousal * 0.2 + fear * 0.2 + fatigue * 0.15 + pain * 0.2)

        # Interoceptive awareness: ability to perceive body signals
        self.interoceptive_awareness = self.body_signal_intensity * autonomic * (1.0 - stress * 0.2)
        self.interoceptive_awareness = max(0.0, min(1.0, self.interoceptive_awareness))

        # Disgust: moral/physical aversion signal
        self.disgust_response = max(0.0, fear * 0.3 + pain * 0.4 - autonomic * 0.2)

        self.body_history.append(self.body_signal_intensity)
        self.awareness_history.append(self.interoceptive_awareness)
        for h in [self.body_history, self.awareness_history]:
            if len(h) > 40:
                h.pop(0)

        avg_awareness = sum(self.awareness_history[-15:]) / min(15, len(self.awareness_history))
        self.disconnection_ticks = self.disconnection_ticks + 1 if avg_awareness < 0.1 else max(0, self.disconnection_ticks - 1)
        self.overwhelm_ticks = self.overwhelm_ticks + 1 if self.body_signal_intensity > 0.8 else max(0, self.overwhelm_ticks - 1)

        was_disconnected, was_overwhelmed = self.chronic_disconnection, self.chronic_overwhelm
        self.chronic_disconnection = self.disconnection_ticks > 18
        self.chronic_overwhelm = self.overwhelm_ticks > 18

        if self.chronic_disconnection and not was_disconnected:
            self.feed_to_memory({"event": "interoceptive_disconnection", "note": "Disconnected from body signals — flat affect, unaware of own state"})
        if self.chronic_overwhelm and not was_overwhelmed:
            self.feed_to_memory({"event": "interoceptive_overwhelm", "note": "Body signals chronically overwhelming — somatic noise flooding cognition"})

        return {
            "body_signal_intensity": round(self.body_signal_intensity, 3),
            "interoceptive_awareness": round(self.interoceptive_awareness, 3),
            "disgust_response": round(self.disgust_response, 3),
            "chronic_disconnection": self.chronic_disconnection,
            "chronic_overwhelm": self.chronic_overwhelm,
        }

    def _overnight(self):
        self.disconnection_ticks = max(0, self.disconnection_ticks - 5)
        self.overwhelm_ticks = max(0, self.overwhelm_ticks - 6)
        self.chronic_disconnection = self.disconnection_ticks > 18
        self.chronic_overwhelm = self.overwhelm_ticks > 18
        self.body_history.clear()
        return {"overnight": "interoceptive_reset"}
