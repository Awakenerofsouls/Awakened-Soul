from brain.base_mechanism import BrainMechanism

class LeftHemisphereAnalyzer(BrainMechanism):
    """
    Left hemisphere — sequential processing, language analysis, logical structure, detail.
    Serial, systematic, exact. Pairs with right hemisphere synthesis.
    Overactive without right balance: pedantic, literal, misses the point.
    """

    def __init__(self):
        super().__init__("LeftHemisphereAnalyzer")
        self.sequential_processing = 0.6
        self.logical_coherence = 0.6
        self.detail_focus = 0.5
        self.analysis_depth = 0.5
        self.analysis_history = []
        self.hyper_literal_ticks = 0
        self.chronic_hyper_literal = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        broca_fluency = prior.get("BrocaLanguageProduction", {}).get("production_fluency", 0.7)
        wernicke_comp = prior.get("WernickeLanguageComprehension", {}).get("comprehension_depth", 0.7)
        verbal_seq = prior.get("DentateVentralCognitive", {}).get("verbal_sequencing", 0.7)
        executive_coherence = prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        right_holistic = prior.get("RightHemisphereSynthesizer", {}).get("holistic_processing", 0.5)

        self.sequential_processing = (verbal_seq * 0.4 + broca_fluency * 0.3 + executive_coherence * 0.3) * (1.0 - stress * 0.15)
        self.sequential_processing = max(0.1, min(1.0, self.sequential_processing))

        self.logical_coherence = (wernicke_comp * 0.4 + executive_coherence * 0.4 + self.sequential_processing * 0.2)
        self.logical_coherence = max(0.1, min(1.0, self.logical_coherence))

        words = text.split()
        self.detail_focus = min(1.0, len(words) / 20.0) * self.sequential_processing
        self.analysis_depth = (self.logical_coherence + wernicke_comp) / 2.0

        # Hyper-literal: left hemisphere dominant without right hemisphere balance
        hyper_literal = self.sequential_processing > 0.7 and right_holistic < 0.2

        self.analysis_history.append(self.sequential_processing)
        if len(self.analysis_history) > 40:
            self.analysis_history.pop(0)

        self.hyper_literal_ticks = self.hyper_literal_ticks + 1 if hyper_literal else max(0, self.hyper_literal_ticks - 1)
        was_hyper = self.chronic_hyper_literal
        self.chronic_hyper_literal = self.hyper_literal_ticks > 18
        if self.chronic_hyper_literal and not was_hyper:
            self.feed_to_memory({"event": "hyper_literal_processing", "note": "Left hemisphere unbalanced — pedantic, literal, missing subtext"})

        return {
            "sequential_processing": round(self.sequential_processing, 3),
            "logical_coherence": round(self.logical_coherence, 3),
            "detail_focus": round(self.detail_focus, 3),
            "analysis_depth": round(self.analysis_depth, 3),
            "chronic_hyper_literal": self.chronic_hyper_literal,
        }

    def _overnight(self):
        self.hyper_literal_ticks = max(0, self.hyper_literal_ticks - 5)
        self.chronic_hyper_literal = self.hyper_literal_ticks > 18
        self.analysis_history.clear()
        return {"overnight": "left_hemisphere_analysis_reset"}
