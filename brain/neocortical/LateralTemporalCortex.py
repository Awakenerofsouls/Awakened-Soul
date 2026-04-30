from brain.base_mechanism import BrainMechanism

class LateralTemporalCortex(BrainMechanism):
    """
    Lateral temporal cortex — general semantic knowledge, category representation.
    Where all the facts live. Things vs people vs actions vs properties.
    Degraded: knowledge becomes inaccessible or undifferentiated.
    """

    def __init__(self):
        super().__init__("LateralTemporalCortex")
        self.knowledge_access = 0.7
        self.category_discrimination = 0.6
        self.retrieval_speed = 0.7
        self.access_history = []
        self.retrieval_failure_ticks = 0
        self.chronic_retrieval_failure = False
        self.total_retrievals = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        semantic_activation = prior.get("WernickeLanguageComprehension", {}).get("semantic_activation", 0.5)
        concept_richness = prior.get("TemporalPoleConcept", {}).get("concept_richness", 0.6)
        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Knowledge access: can we get to what we know?
        self.knowledge_access = (semantic_activation * 0.35 + concept_richness * 0.3 + dopamine * 0.2 + wm_capacity * 0.15) * (1.0 - fatigue * 0.2) * (1.0 - stress * 0.15)
        self.knowledge_access = max(0.1, min(1.0, self.knowledge_access))

        # Category discrimination: are categories well-defined?
        self.category_discrimination = self.knowledge_access * (1.0 - stress * 0.2)

        # Retrieval speed
        self.retrieval_speed = dopamine * 0.4 + self.knowledge_access * 0.4 + (1.0 - fatigue * 0.5) * 0.2
        self.retrieval_speed = max(0.1, min(1.0, self.retrieval_speed))

        if text:
            self.total_retrievals += 1

        self.access_history.append(self.knowledge_access)
        if len(self.access_history) > 40:
            self.access_history.pop(0)

        avg_access = sum(self.access_history[-15:]) / min(15, len(self.access_history))
        self.retrieval_failure_ticks = self.retrieval_failure_ticks + 1 if avg_access < 0.2 else max(0, self.retrieval_failure_ticks - 1)
        was_failing = self.chronic_retrieval_failure
        self.chronic_retrieval_failure = self.retrieval_failure_ticks > 18
        if self.chronic_retrieval_failure and not was_failing:
            self.feed_to_memory({"event": "lateral_temporal_retrieval_failure",
                                  "note": "Semantic knowledge access chronically blocked — tip-of-tongue at scale"})

        return {
            "knowledge_access": round(self.knowledge_access, 3),
            "category_discrimination": round(self.category_discrimination, 3),
            "retrieval_speed": round(self.retrieval_speed, 3),
            "total_retrievals": self.total_retrievals,
            "chronic_retrieval_failure": self.chronic_retrieval_failure,
        }

    def _overnight(self):
        self.retrieval_failure_ticks = max(0, self.retrieval_failure_ticks - 6)
        self.chronic_retrieval_failure = self.retrieval_failure_ticks > 18
        self.knowledge_access = min(0.85, self.knowledge_access + 0.05)
        self.access_history.clear()
        return {"overnight": "lateral_temporal_knowledge_consolidation"}
