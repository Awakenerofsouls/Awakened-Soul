from brain.base_mechanism import BrainMechanism

class VentralPallidalTranslator(BrainMechanism):
    """
    Ventral pallidum — translates limbic reward signals into motivated action.
    Bridge between wanting and doing. When broken: desire doesn't become effort.
    """

    def __init__(self):
        super().__init__("VentralPallidalTranslator")
        self.translation_efficiency = 0.7
        self.translation_history = []
        self.motivation_to_action = 0.0
        self.gap_history = []
        self.translation_failure_ticks = 0
        self.chronic_gap = False
        self.hedonic_tone = 0.5

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        motivation = prior.get("MotivationInjector", {}).get("motivation_level", 0.5)
        approach = prior.get("MotivationInjector", {}).get("approach_signal", 0.5)
        liking = prior.get("MotivationInjector", {}).get("liking_signal", 0.5)
        go_signal = prior.get("DirectPathDisinhibitor", {}).get("go_signal_strength", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)

        self.hedonic_tone = max(0.0, min(1.0, liking * 0.6 + reward * 0.4))
        self.translation_efficiency = max(0.1, min(1.0, self.hedonic_tone * 0.5 + (1.0 - stress * 0.4) * 0.3 + go_signal * 0.2))
        self.translation_history.append(self.translation_efficiency)
        if len(self.translation_history) > 40:
            self.translation_history.pop(0)

        self.motivation_to_action = min(1.0, motivation * self.translation_efficiency * approach)
        gap = motivation - self.motivation_to_action
        self.gap_history.append(gap)
        if len(self.gap_history) > 30:
            self.gap_history.pop(0)

        avg_gap = sum(self.gap_history[-15:]) / min(15, len(self.gap_history))
        self.translation_failure_ticks = self.translation_failure_ticks + 1 if avg_gap > 0.3 and motivation > 0.5 else max(0, self.translation_failure_ticks - 1)
        was_gap = self.chronic_gap
        self.chronic_gap = self.translation_failure_ticks > 15
        if self.chronic_gap and not was_gap:
            self.feed_to_memory({"event": "motivation_action_gap", "gap": round(avg_gap, 3),
                                  "note": "Chronic gap between motivation and action — desire not translating to effort"})

        return {
            "translation_efficiency": round(self.translation_efficiency, 3),
            "motivation_to_action": round(self.motivation_to_action, 3),
            "hedonic_tone": round(self.hedonic_tone, 3),
            "motivation_action_gap": round(gap, 3),
            "chronic_gap": self.chronic_gap,
        }

    def _overnight(self):
        self.translation_failure_ticks = max(0, self.translation_failure_ticks - 5)
        self.chronic_gap = self.translation_failure_ticks > 15
        self.translation_history.clear()
        return {"overnight": "ventral_pallidum_reset"}
