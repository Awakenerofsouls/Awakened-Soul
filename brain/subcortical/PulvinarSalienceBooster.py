from brain.base_mechanism import BrainMechanism

class PulvinarSalienceBooster(BrainMechanism):
    """
    Pulvinar nucleus — amplifies salient stimuli before cortical processing.
    Boosts survival-relevant signals. Overactive: everything feels urgent.
    Underactive: threats slip through unnoticed.
    """

    def __init__(self):
        super().__init__("PulvinarSalienceBooster")
        self.boost_level = 0.0
        self.boost_history = []
        self.threat_amplification = 0.0
        self.novelty_amplification = 0.0
        self.over_boost_ticks = 0
        self.under_boost_ticks = 0
        self.chronic_hypervigilance = False
        self.chronic_blunting = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        threat = prior.get("BLAEmotionalLearner", {}).get("threat_association", 0.0)
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        gate_strength = prior.get("ThalamicSalienceFilter", {}).get("gate_strength", 0.5)

        self.threat_amplification = min(1.0, fear * 0.6 + threat * 0.4)
        self.novelty_amplification = novelty * 0.7 * arousal
        raw_boost = max(self.threat_amplification, self.novelty_amplification) * gate_strength
        self.boost_level = min(1.0, raw_boost * (1.0 + arousal * 0.3))

        self.boost_history.append(self.boost_level)
        if len(self.boost_history) > 40:
            self.boost_history.pop(0)

        avg_boost = sum(self.boost_history[-15:]) / min(15, len(self.boost_history))
        self.over_boost_ticks = self.over_boost_ticks + 1 if avg_boost > 0.7 else max(0, self.over_boost_ticks - 1)
        self.under_boost_ticks = self.under_boost_ticks + 1 if avg_boost < 0.1 else max(0, self.under_boost_ticks - 1)

        was_hyper, was_blunted = self.chronic_hypervigilance, self.chronic_blunting
        self.chronic_hypervigilance = self.over_boost_ticks > 18
        self.chronic_blunting = self.under_boost_ticks > 18

        if self.chronic_hypervigilance and not was_hyper:
            self.feed_to_memory({"event": "pulvinar_hypervigilance", "note": "Salience booster chronically overactive — everything feels urgent"})
        if self.chronic_blunting and not was_blunted:
            self.feed_to_memory({"event": "pulvinar_blunting", "note": "Salience booster chronically underactive — threats going unnoticed"})

        return {
            "boost_level": round(self.boost_level, 3),
            "threat_amplification": round(self.threat_amplification, 3),
            "novelty_amplification": round(self.novelty_amplification, 3),
            "amplified_signal": round(self.boost_level * gate_strength, 3),
            "chronic_hypervigilance": self.chronic_hypervigilance,
            "chronic_blunting": self.chronic_blunting,
        }

    def _overnight(self):
        self.over_boost_ticks = max(0, self.over_boost_ticks - 5)
        self.under_boost_ticks = max(0, self.under_boost_ticks - 5)
        self.chronic_hypervigilance = self.over_boost_ticks > 18
        self.chronic_blunting = self.under_boost_ticks > 18
        self.boost_history.clear()
        return {"overnight": "pulvinar_threshold_reset"}
