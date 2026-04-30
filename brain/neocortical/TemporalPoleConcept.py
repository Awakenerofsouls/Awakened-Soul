from brain.base_mechanism import BrainMechanism

class TemporalPoleConcept(BrainMechanism):
    """
    Temporal pole — conceptual knowledge, abstract semantic memory, social knowledge.
    Where word meanings live in their richest, most connected form.
    Degraded: concepts become thin — words without their web of associations.
    """

    def __init__(self):
        super().__init__("TemporalPoleConcept")
        self.concept_richness = 0.6
        self.semantic_network_activation = 0.5
        self.abstract_knowledge = 0.5
        self.richness_history = []
        self.impoverishment_ticks = 0
        self.chronic_impoverishment = False
        self.concept_activations = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        semantic_activation = prior.get("WernickeLanguageComprehension", {}).get("semantic_activation", 0.5)
        meaning_depth = prior.get("AngularGyrus", {}).get("meaning_depth", 0.5)
        social_knowledge = prior.get("Temporoparietal", {}).get("other_model_confidence", 0.5)
        pragmatic = prior.get("InferiorFrontalGyrus", {}).get("pragmatic_inference", 0.5)
        right_synthesis = prior.get("RightHemisphereSynthesizer", {}).get("metaphor_capacity", 0.4)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)

        # Concept richness: how full and connected are activated concepts
        self.concept_richness = (semantic_activation * 0.3 + meaning_depth * 0.25 + right_synthesis * 0.25 + social_knowledge * 0.2) * (1.0 - stress * 0.2) * (1.0 - fatigue * 0.15)
        self.concept_richness = max(0.1, min(1.0, self.concept_richness))

        # Semantic network activation: spreading activation through concept space
        words = text.split()
        self.semantic_network_activation = min(1.0, self.concept_richness * (0.3 + len(words) * 0.02))

        # Abstract knowledge: concepts removed from direct sensory grounding
        self.abstract_knowledge = (meaning_depth + pragmatic) / 2.0

        if self.semantic_network_activation > 0.5:
            self.concept_activations += 1

        self.richness_history.append(self.concept_richness)
        if len(self.richness_history) > 40:
            self.richness_history.pop(0)

        avg_richness = sum(self.richness_history[-15:]) / min(15, len(self.richness_history))
        self.impoverishment_ticks = self.impoverishment_ticks + 1 if avg_richness < 0.2 else max(0, self.impoverishment_ticks - 1)
        was_impoverished = self.chronic_impoverishment
        self.chronic_impoverishment = self.impoverishment_ticks > 18
        if self.chronic_impoverishment and not was_impoverished:
            self.feed_to_memory({"event": "temporal_pole_impoverishment",
                                  "note": "Conceptual knowledge impoverished — words thin, associations collapsed"})

        return {
            "concept_richness": round(self.concept_richness, 3),
            "semantic_network_activation": round(self.semantic_network_activation, 3),
            "abstract_knowledge": round(self.abstract_knowledge, 3),
            "concept_activations": self.concept_activations,
            "chronic_impoverishment": self.chronic_impoverishment,
        }

    def _overnight(self):
        self.impoverishment_ticks = max(0, self.impoverishment_ticks - 6)
        self.chronic_impoverishment = self.impoverishment_ticks > 18
        self.concept_richness = min(0.85, self.concept_richness + 0.05)
        self.richness_history.clear()
        return {"overnight": "temporal_pole_concept_consolidation"}
