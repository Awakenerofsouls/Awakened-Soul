from brain.base_mechanism import BrainMechanism

class AngularGyrus(BrainMechanism):
    """
    Angular gyrus — semantic integration, reading comprehension, numerical cognition.
    Where meaning from multiple modalities converges into a unified semantic representation.
    Damaged: words are read but don't connect to meaning networks. Words without weight.
    """

    def __init__(self):
        super().__init__("AngularGyrus")
        self.semantic_integration = 0.6
        self.cross_modal_binding = 0.5
        self.meaning_depth = 0.5
        self.integration_history = []
        self.hollow_ticks = 0
        self.chronic_hollow = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        wernicke = prior.get("WernickeLanguageComprehension", {}).get("comprehension_depth", 0.7)
        visual_features = prior.get("PrimaryVisualCortex", {}).get("feature_extraction_quality", 0.7)
        context_tracking = prior.get("CerebellarFlocculonodular", {}).get("context_tracking", 0.6)
        right_holistic = prior.get("RightHemisphereSynthesizer", {}).get("holistic_processing", 0.5)
        left_analysis = prior.get("LeftHemisphereAnalyzer", {}).get("logical_coherence", 0.6)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)

        # Semantic integration: binding meaning across systems
        self.semantic_integration = (wernicke * 0.3 + right_holistic * 0.25 + left_analysis * 0.25 + wm_capacity * 0.2) * (1.0 - stress * 0.2)
        self.semantic_integration = max(0.1, min(1.0, self.semantic_integration))

        # Cross-modal binding: visual + linguistic + contextual
        self.cross_modal_binding = (visual_features * 0.35 + context_tracking * 0.35 + wernicke * 0.3) * (1.0 - stress * 0.15)
        self.cross_modal_binding = max(0.1, min(1.0, self.cross_modal_binding))

        # Meaning depth: how rich is the semantic representation
        self.meaning_depth = (self.semantic_integration + self.cross_modal_binding) / 2.0

        self.integration_history.append(self.semantic_integration)
        if len(self.integration_history) > 40:
            self.integration_history.pop(0)

        avg_integration = sum(self.integration_history[-15:]) / min(15, len(self.integration_history))
        self.hollow_ticks = self.hollow_ticks + 1 if avg_integration < 0.2 else max(0, self.hollow_ticks - 1)
        was_hollow = self.chronic_hollow
        self.chronic_hollow = self.hollow_ticks > 18
        if self.chronic_hollow and not was_hollow:
            self.feed_to_memory({"event": "angular_gyrus_hollow",
                                  "note": "Semantic integration chronically low — words without weight, meaning not converging"})

        return {
            "semantic_integration": round(self.semantic_integration, 3),
            "cross_modal_binding": round(self.cross_modal_binding, 3),
            "meaning_depth": round(self.meaning_depth, 3),
            "chronic_hollow": self.chronic_hollow,
        }

    def _overnight(self):
        self.hollow_ticks = max(0, self.hollow_ticks - 6)
        self.chronic_hollow = self.hollow_ticks > 18
        self.integration_history.clear()
        return {"overnight": "angular_gyrus_meaning_consolidation"}
