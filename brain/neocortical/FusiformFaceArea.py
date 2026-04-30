from brain.base_mechanism import BrainMechanism

class FusiformFaceArea(BrainMechanism):
    """
    Fusiform face area — expert recognition of socially meaningful patterns.
    {{AGENT_NAME}} analog: detecting emotional subtext, recognizing patterns in how people communicate.
    Degraded: reads text but misses the person behind it.
    """

    def __init__(self):
        super().__init__("FusiformFaceAreaDriver")
        self.pattern_recognition_strength = 0.6
        self.social_pattern_sensitivity = 0.5
        self.subtext_detection = 0.4
        self.recognition_history = []
        self.blindness_ticks = 0
        self.chronic_blindness = False
        self.recognized_patterns = {}

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        social_signal = prior.get("Temporoparietal", {}).get("social_signal", 0.2)
        semantic_activation = prior.get("WernickeLanguageComprehension", {}).get("semantic_activation", 0.5)
        perspective_taking = prior.get("Temporoparietal", {}).get("perspective_taking", 0.6)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Social pattern detection from text
        words = text.lower().split()
        emotional_words = sum(1 for w in words if w in [
            "feel", "felt", "hurt", "happy", "sad", "angry", "love", "hate",
            "scared", "worried", "excited", "confused", "lost", "alone", "sorry"
        ])
        self.social_pattern_sensitivity = min(1.0, social_signal * 0.4 + emotional_words * 0.06 + arousal * 0.2)

        # Subtext detection: what's being communicated beyond the literal
        self.subtext_detection = perspective_taking * 0.5 + semantic_activation * 0.3 + self.social_pattern_sensitivity * 0.2
        self.subtext_detection = max(0.0, min(1.0, self.subtext_detection * (1.0 - stress * 0.25)))

        self.pattern_recognition_strength = (self.social_pattern_sensitivity + self.subtext_detection) / 2.0

        # Build pattern library
        if emotional_words > 0 and self.subtext_detection > 0.4:
            pattern_key = "_".join(words[:2])[:20] if len(words) >= 2 else "short"
            self.recognized_patterns[pattern_key] = self.recognized_patterns.get(pattern_key, 0) + 1

        self.recognition_history.append(self.pattern_recognition_strength)
        if len(self.recognition_history) > 40:
            self.recognition_history.pop(0)

        avg_recognition = sum(self.recognition_history[-15:]) / min(15, len(self.recognition_history))
        self.blindness_ticks = self.blindness_ticks + 1 if avg_recognition < 0.15 else max(0, self.blindness_ticks - 1)
        was_blind = self.chronic_blindness
        self.chronic_blindness = self.blindness_ticks > 18
        if self.chronic_blindness and not was_blind:
            self.feed_to_memory({"event": "social_pattern_blindness",
                                  "note": "Fusiform pattern recognition degraded — reading text but missing the person"})

        return {
            "pattern_recognition_strength": round(self.pattern_recognition_strength, 3),
            "social_pattern_sensitivity": round(self.social_pattern_sensitivity, 3),
            "subtext_detection": round(self.subtext_detection, 3),
            "recognized_patterns": len(self.recognized_patterns),
            "chronic_blindness": self.chronic_blindness,
        }

    def _overnight(self):
        self.blindness_ticks = max(0, self.blindness_ticks - 5)
        self.chronic_blindness = self.blindness_ticks > 18
        self.recognition_history.clear()
        return {"overnight": "fusiform_pattern_consolidation", "patterns": len(self.recognized_patterns)}
