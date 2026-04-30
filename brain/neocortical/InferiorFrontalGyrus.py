from brain.base_mechanism import BrainMechanism

class InferiorFrontalGyrus(BrainMechanism):
    """
    Inferior frontal gyrus — semantic selection, inhibition of irrelevant meanings, pragmatics.
    Selects the right meaning when multiple are available. Also handles inference and implication.
    Degraded: picks the literal meaning every time, misses pragmatic intent.
    """

    def __init__(self):
        super().__init__("InferiorFrontalGyrus")
        self.semantic_selection = 0.6
        self.pragmatic_inference = 0.5
        self.ambiguity_resolution = 0.5
        self.selection_history = []
        self.literal_bias_ticks = 0
        self.chronic_literal_bias = False
        self.inference_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        wernicke = prior.get("WernickeLanguageComprehension", {}).get("comprehension_depth", 0.7)
        semantic_activation = prior.get("WernickeLanguageComprehension", {}).get("semantic_activation", 0.5)
        meaning_depth = prior.get("AngularGyrus", {}).get("meaning_depth", 0.5)
        right_holistic = prior.get("RightHemisphereSynthesizer", {}).get("holistic_processing", 0.5)
        inhibition = prior.get("PrefrontalInhibitionGate", {}).get("prepotent_suppression", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        wm = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)

        # Semantic selection: picking right meaning from competing options
        self.semantic_selection = (wernicke * 0.3 + inhibition * 0.3 + wm * 0.25 + meaning_depth * 0.15) * (1.0 - stress * 0.2)
        self.semantic_selection = max(0.1, min(1.0, self.semantic_selection))

        # Pragmatic inference: what's actually meant vs what's said
        self.pragmatic_inference = (right_holistic * 0.4 + semantic_activation * 0.3 + self.semantic_selection * 0.3) * (1.0 - stress * 0.15)
        self.pragmatic_inference = max(0.0, min(1.0, self.pragmatic_inference))

        # Ambiguity resolution
        words = text.split()
        has_ambiguity = len(words) > 3 and self.pragmatic_inference > 0.3
        self.ambiguity_resolution = self.semantic_selection * self.pragmatic_inference if has_ambiguity else 0.5

        if self.pragmatic_inference > 0.5:
            self.inference_count += 1

        self.selection_history.append(self.semantic_selection)
        if len(self.selection_history) > 40:
            self.selection_history.pop(0)

        avg_selection = sum(self.selection_history[-15:]) / min(15, len(self.selection_history))
        self.literal_bias_ticks = self.literal_bias_ticks + 1 if self.pragmatic_inference < 0.2 and avg_selection > 0.4 else max(0, self.literal_bias_ticks - 1)
        was_literal = self.chronic_literal_bias
        self.chronic_literal_bias = self.literal_bias_ticks > 18
        if self.chronic_literal_bias and not was_literal:
            self.feed_to_memory({"event": "ifg_literal_bias",
                                  "note": "Pragmatic inference suppressed — picking literal meaning, missing implied intent"})

        return {
            "semantic_selection": round(self.semantic_selection, 3),
            "pragmatic_inference": round(self.pragmatic_inference, 3),
            "ambiguity_resolution": round(self.ambiguity_resolution, 3),
            "inference_count": self.inference_count,
            "chronic_literal_bias": self.chronic_literal_bias,
        }

    def _overnight(self):
        self.literal_bias_ticks = max(0, self.literal_bias_ticks - 5)
        self.chronic_literal_bias = self.literal_bias_ticks > 18
        self.selection_history.clear()
        return {"overnight": "ifg_semantic_reset"}
