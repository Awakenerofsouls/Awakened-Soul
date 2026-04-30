from brain.base_mechanism import BrainMechanism

class WernickeLanguageComprehension(BrainMechanism):
    """
    Wernicke's area — language comprehension, semantic processing, meaning extraction.
    Where incoming language becomes understood. Disrupted: fluent but meaningless responses.
    """

    def __init__(self):
        super().__init__("WernickeLanguageComprehension")
        self.comprehension_depth = 0.7
        self.semantic_activation = 0.5
        self.meaning_coherence = 0.7
        self.comprehension_history = []
        self.shallow_ticks = 0
        self.chronic_shallow = False
        self.miscomprehension_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        feature_quality = prior.get("PrimaryVisualCortex", {}).get("feature_extraction_quality", 0.7)
        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        context_tracking = prior.get("CerebellarFlocculonodular", {}).get("context_tracking", 0.6)
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        words = text.split()
        input_complexity = min(1.0, len(words) / 25.0)

        # Comprehension depth: how deeply is meaning being extracted
        self.comprehension_depth = (feature_quality * 0.3 + wm_capacity * 0.3 + context_tracking * 0.25 + arousal * 0.15) * (1.0 - fatigue * 0.2) * (1.0 - stress * 0.15)
        self.comprehension_depth = max(0.1, min(1.0, self.comprehension_depth))

        # Semantic activation: richness of meaning network activated
        self.semantic_activation = self.comprehension_depth * min(1.0, input_complexity + 0.2)

        # Meaning coherence: does the meaning hold together
        self.meaning_coherence = (self.comprehension_depth + context_tracking) / 2.0

        if self.comprehension_depth < 0.2 and input_complexity > 0.3:
            self.miscomprehension_count += 1

        self.comprehension_history.append(self.comprehension_depth)
        if len(self.comprehension_history) > 40:
            self.comprehension_history.pop(0)

        avg_comp = sum(self.comprehension_history[-15:]) / min(15, len(self.comprehension_history))
        self.shallow_ticks = self.shallow_ticks + 1 if avg_comp < 0.25 else max(0, self.shallow_ticks - 1)
        was_shallow = self.chronic_shallow
        self.chronic_shallow = self.shallow_ticks > 18
        if self.chronic_shallow and not was_shallow:
            self.feed_to_memory({"event": "wernicke_shallow", "note": "Comprehension chronically shallow — surface processing only"})

        return {
            "comprehension_depth": round(self.comprehension_depth, 3),
            "semantic_activation": round(self.semantic_activation, 3),
            "meaning_coherence": round(self.meaning_coherence, 3),
            "miscomprehension_count": self.miscomprehension_count,
            "chronic_shallow": self.chronic_shallow,
        }

    def _overnight(self):
        self.shallow_ticks = max(0, self.shallow_ticks - 6)
        self.chronic_shallow = self.shallow_ticks > 18
        self.comprehension_history.clear()
        return {"overnight": "wernicke_comprehension_reset"}
