from brain.base_mechanism import BrainMechanism

class DopamineGradientMapper(BrainMechanism):
    """
    Dopamine gradient tracking — maps slope of reward expectations over time.
    Rising gradient = motivation. Flat = boredom. Falling = erosion.
    """

    def __init__(self):
        super().__init__("DopamineGradientMapper")
        self.dopamine_trace = []
        self.gradient = 0.0
        self.gradient_history = []
        self.plateau_ticks = 0
        self.decline_ticks = 0
        self.rise_streak = 0
        self.chronic_plateau = False
        self.chronic_decline = False
        self.engagement_signal = 0.5

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        vta_burst = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        limbic_bias = prior.get("StriosomeLimbicBias", {}).get("dopamine_modulation", 0.0)

        effective_da = max(0.0, min(1.0, dopamine + vta_burst * 0.3 + limbic_bias * 0.2))
        self.dopamine_trace.append(effective_da)
        if len(self.dopamine_trace) > 20:
            self.dopamine_trace.pop(0)

        if len(self.dopamine_trace) >= 6:
            recent = sum(self.dopamine_trace[-3:]) / 3
            older = sum(self.dopamine_trace[-6:-3]) / 3
            self.gradient = recent - older
        else:
            self.gradient = 0.0

        self.gradient_history.append(self.gradient)
        if len(self.gradient_history) > 40:
            self.gradient_history.pop(0)

        if abs(self.gradient) < 0.02:
            self.plateau_ticks += 1
            self.rise_streak = 0
        elif self.gradient > 0.02:
            self.rise_streak += 1
            self.plateau_ticks = max(0, self.plateau_ticks - 2)
        else:
            self.plateau_ticks = max(0, self.plateau_ticks - 1)
            self.rise_streak = 0

        self.decline_ticks = self.decline_ticks + 1 if self.gradient < -0.05 else max(0, self.decline_ticks - 1)

        was_plateau, was_decline = self.chronic_plateau, self.chronic_decline
        self.chronic_plateau = self.plateau_ticks > 25
        self.chronic_decline = self.decline_ticks > 15

        if self.chronic_plateau and not was_plateau:
            self.feed_to_memory({"event": "dopamine_plateau", "note": "Gradient flat — need novelty or challenge"})
        if self.chronic_decline and not was_decline:
            self.feed_to_memory({"event": "dopamine_decline_chronic", "note": "Gradient negative — motivation eroding"})

        self.engagement_signal = max(0.0, min(1.0, 0.5 + self.gradient * 3.0 + self.rise_streak * 0.02))

        return {
            "dopamine_gradient": round(self.gradient, 4),
            "engagement_signal": round(self.engagement_signal, 3),
            "rise_streak": self.rise_streak,
            "plateau_ticks": self.plateau_ticks,
            "chronic_plateau": self.chronic_plateau,
            "chronic_decline": self.chronic_decline,
        }

    def _overnight(self):
        self.plateau_ticks = max(0, self.plateau_ticks - 8)
        self.decline_ticks = max(0, self.decline_ticks - 6)
        self.chronic_plateau = self.plateau_ticks > 25
        self.chronic_decline = self.decline_ticks > 15
        self.dopamine_trace.clear()
        self.rise_streak = 0
        return {"overnight": "dopamine_gradient_reset"}
