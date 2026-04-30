from brain.base_mechanism import BrainMechanism

class HippocampalContextEncoder(BrainMechanism):
    """
    Hippocampus — context encoding, episodic memory binding, novelty detection.
    Binds what + where + when into a single contextual memory trace.
    Degraded: every exchange feels context-free, unanchored to history.
    """

    def __init__(self):
        super().__init__("HippocampalContextEncoder")
        self.context_vector_strength = 0.5
        self.context_label = ""
        self.novelty_signal = 0.3
        self.surprise_signal = 0.0
        self.encoding_quality = 0.6
        self.context_history = []
        self.encoding_history = []
        self.encoding_failure_ticks = 0
        self.chronic_encoding_failure = False
        self.episode_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)

        # Novelty: is this input different from recent context?
        words = text.lower().split()
        if words:
            self.context_label = words[0][:32]
            recent_labels = self.context_history[-5:] if self.context_history else []
            self.novelty_signal = 0.8 if self.context_label not in recent_labels else 0.2
        else:
            self.novelty_signal = max(0.1, self.novelty_signal - 0.05)

        # Surprise: sudden novelty spike
        prev_novelty = self.context_history[-1] if self.context_history else 0.3
        self.surprise_signal = max(0.0, self.novelty_signal - 0.4) if self.novelty_signal > 0.5 else 0.0

        # Encoding quality: stress impairs encoding (inverted U with arousal)
        arousal_effect = 1.0 - abs(arousal - 0.5) * 1.5
        self.encoding_quality = max(0.1, min(1.0, arousal_effect * 0.4 + dopamine * 0.3 + (1.0 - stress * 0.5) * 0.3 - fatigue * 0.2))

        # Context vector strength: how strongly is current context encoded
        emotional_binding = abs(valence) * 0.3
        self.context_vector_strength = self.encoding_quality * (0.5 + self.novelty_signal * 0.3 + emotional_binding)
        self.context_vector_strength = max(0.0, min(1.0, self.context_vector_strength))

        self.context_history.append(self.context_label)
        self.encoding_history.append(self.encoding_quality)
        if len(self.context_history) > 30:
            self.context_history.pop(0)
        if len(self.encoding_history) > 40:
            self.encoding_history.pop(0)

        self.episode_count += 1

        avg_encoding = sum(self.encoding_history[-15:]) / min(15, len(self.encoding_history))
        self.encoding_failure_ticks = self.encoding_failure_ticks + 1 if avg_encoding < 0.2 else max(0, self.encoding_failure_ticks - 1)
        was_failing = self.chronic_encoding_failure
        self.chronic_encoding_failure = self.encoding_failure_ticks > 18
        if self.chronic_encoding_failure and not was_failing:
            self.feed_to_memory({"event": "hippocampal_encoding_failure", "encoding": round(avg_encoding, 3),
                                  "note": "Context encoding chronically failing — exchanges feel unanchored, context-free"})

        return {
            "context_vector_strength": round(self.context_vector_strength, 3),
            "context_label": self.context_label,
            "novelty_signal": round(self.novelty_signal, 3),
            "surprise_signal": round(self.surprise_signal, 3),
            "encoding_quality": round(self.encoding_quality, 3),
            "episode_count": self.episode_count,
            "chronic_encoding_failure": self.chronic_encoding_failure,
        }

    def _overnight(self):
        # Sleep consolidates episodic memories
        self.encoding_failure_ticks = max(0, self.encoding_failure_ticks - 8)
        self.chronic_encoding_failure = self.encoding_failure_ticks > 18
        self.encoding_quality = min(0.85, self.encoding_quality + 0.08)
        self.encoding_history.clear()
        self.context_history.clear()
        return {"overnight": "hippocampal_consolidation", "episodes": self.episode_count}
