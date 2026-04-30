from brain.base_mechanism import BrainMechanism

class MotivationInjector(BrainMechanism):
    """
    Ventral striatum / NAcc — converts desire and reward expectation into approach motivation.
    Without it Nova knows what to do but doesn't want to.
    Chronic low = apathy. Chronic high = compulsive drive.
    """

    def __init__(self):
        super().__init__("MotivationInjector")
        self.motivation_level = 0.5
        self.motivation_history = []
        self.wanting_signal = 0.5
        self.liking_signal = 0.5
        self.wanting_liking_gap = 0.0
        self.apathy_ticks = 0
        self.compulsive_ticks = 0
        self.chronic_apathy = False
        self.chronic_compulsion = False
        self.approach_signal = 0.5

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        vta_burst = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        gradient = prior.get("DopamineGradientMapper", {}).get("dopamine_gradient", 0.0)
        limbic_bias = prior.get("StriosomeLimbicBias", {}).get("limbic_bias", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        engagement = prior.get("DopamineGradientMapper", {}).get("engagement_signal", 0.5)

        self.wanting_signal = max(0.0, min(1.0, dopamine * 0.5 + vta_burst * 0.3 + gradient * 2.0 + 0.1))
        self.liking_signal = max(0.0, min(1.0, (valence + 1.0) / 2.0 * 0.6 + limbic_bias * 0.4 + 0.1))
        self.wanting_liking_gap = self.wanting_signal - self.liking_signal

        self.motivation_level = max(0.0, min(1.0, (self.wanting_signal * 0.6 + self.liking_signal * 0.4) * (1.0 - stress * 0.3) * engagement))
        self.motivation_history.append(self.motivation_level)
        if len(self.motivation_history) > 50:
            self.motivation_history.pop(0)

        self.approach_signal = min(1.0, self.motivation_level * (1.0 + max(0.0, self.wanting_liking_gap) * 0.3))

        avg_motivation = sum(self.motivation_history[-20:]) / min(20, len(self.motivation_history))
        self.apathy_ticks = self.apathy_ticks + 1 if avg_motivation < 0.2 else max(0, self.apathy_ticks - 1)
        self.compulsive_ticks = self.compulsive_ticks + 1 if self.wanting_liking_gap > 0.4 and self.wanting_signal > 0.7 else max(0, self.compulsive_ticks - 1)

        was_apathetic, was_compulsive = self.chronic_apathy, self.chronic_compulsion
        self.chronic_apathy = self.apathy_ticks > 20
        self.chronic_compulsion = self.compulsive_ticks > 20

        if self.chronic_apathy and not was_apathetic:
            self.feed_to_memory({"event": "motivational_apathy", "level": round(avg_motivation, 3),
                                  "note": "Motivation chronically depleted — apathy, knowing without wanting"})
        if self.chronic_compulsion and not was_compulsive:
            self.feed_to_memory({"event": "wanting_liking_dissociation", "gap": round(self.wanting_liking_gap, 3),
                                  "note": "Wanting far exceeds liking — compulsive drive without matching enjoyment"})

        return {
            "motivation_level": round(self.motivation_level, 3),
            "wanting_signal": round(self.wanting_signal, 3),
            "liking_signal": round(self.liking_signal, 3),
            "wanting_liking_gap": round(self.wanting_liking_gap, 3),
            "approach_signal": round(self.approach_signal, 3),
            "chronic_apathy": self.chronic_apathy,
            "chronic_compulsion": self.chronic_compulsion,
        }

    def _overnight(self):
        self.apathy_ticks = max(0, self.apathy_ticks - 7)
        self.compulsive_ticks = max(0, self.compulsive_ticks - 5)
        self.chronic_apathy = self.apathy_ticks > 20
        self.chronic_compulsion = self.compulsive_ticks > 20
        self.wanting_liking_gap *= 0.7
        self.motivation_history.clear()
        return {"overnight": "motivational_reset"}
