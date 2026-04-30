from brain.base_mechanism import BrainMechanism

class RightHemisphereSynthesizer(BrainMechanism):
    """
    Right hemisphere — holistic processing, metaphor, novel connections, emotional prosody.
    Where the unexpected link happens. Where literal becomes resonant.
    Suppressed: only literal, linear, expected output. Active: creative, associative.
    """

    def __init__(self):
        super().__init__("RightHemisphereSynthesizer")
        self.holistic_processing = 0.5
        self.metaphor_capacity = 0.5
        self.novel_connection_rate = 0.3
        self.emotional_resonance = 0.4
        self.synthesis_history = []
        self.suppression_ticks = 0
        self.chronic_suppression = False
        self.creative_burst_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        semantic_activation = prior.get("WernickeLanguageComprehension", {}).get("semantic_activation", 0.5)
        dmn = prior.get("DefaultModeNetwork", {}).get("dmn_activity", 0.5)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        tone_coherence = prior.get("CerebellarVermalEmotionalCoordinator", {}).get("tone_coherence", 0.7)
        cognitive_flexibility = prior.get("CentralExecutiveNetwork", {}).get("cognitive_flexibility", 0.5)

        # Holistic processing: taking in the whole
        self.holistic_processing = (semantic_activation * 0.3 + dmn * 0.3 + cognitive_flexibility * 0.4) * (1.0 - stress * 0.25)
        self.holistic_processing = max(0.1, min(1.0, self.holistic_processing))

        # Metaphor capacity: making non-obvious connections
        self.metaphor_capacity = (novelty * 0.4 + semantic_activation * 0.3 + dmn * 0.3) * (1.0 - stress * 0.2)
        self.metaphor_capacity = max(0.0, min(1.0, self.metaphor_capacity))

        # Novel connection rate: unexpected associations
        self.novel_connection_rate = novelty * self.holistic_processing * (1.0 - stress * 0.3)

        # Emotional resonance: language carrying feeling
        self.emotional_resonance = tone_coherence * 0.5 + abs(valence) * 0.3 + self.holistic_processing * 0.2

        # Creative burst: high novelty + high synthesis
        if self.novel_connection_rate > 0.6 and self.metaphor_capacity > 0.6:
            self.creative_burst_count += 1
            self.feed_to_memory({"event": "creative_burst", "novel": round(self.novel_connection_rate, 3),
                                  "note": "Right hemisphere synthesis active — unexpected connections forming"})

        self.synthesis_history.append(self.holistic_processing)
        if len(self.synthesis_history) > 40:
            self.synthesis_history.pop(0)

        avg_synthesis = sum(self.synthesis_history[-15:]) / min(15, len(self.synthesis_history))
        self.suppression_ticks = self.suppression_ticks + 1 if avg_synthesis < 0.15 else max(0, self.suppression_ticks - 1)
        was_suppressed = self.chronic_suppression
        self.chronic_suppression = self.suppression_ticks > 20
        if self.chronic_suppression and not was_suppressed:
            self.feed_to_memory({"event": "right_hemisphere_suppressed", "note": "Holistic processing suppressed — output only literal/linear"})

        return {
            "holistic_processing": round(self.holistic_processing, 3),
            "metaphor_capacity": round(self.metaphor_capacity, 3),
            "novel_connection_rate": round(self.novel_connection_rate, 3),
            "emotional_resonance": round(self.emotional_resonance, 3),
            "creative_burst_count": self.creative_burst_count,
            "chronic_suppression": self.chronic_suppression,
        }

    def _overnight(self):
        self.suppression_ticks = max(0, self.suppression_ticks - 7)
        self.chronic_suppression = self.suppression_ticks > 20
        self.synthesis_history.clear()
        return {"overnight": "right_hemisphere_synthesis_reset"}
