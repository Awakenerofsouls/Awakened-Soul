from brain.base_mechanism import BrainMechanism

class MedialTemporalEmotion(BrainMechanism):
    """
    Medial temporal cortex — emotional memory, contextual emotional learning.
    Links emotions to contexts — why this situation feels a certain way.
    Without it: emotions happen but don't teach anything. No emotional learning.
    """

    def __init__(self):
        super().__init__("MedialTemporalEmotion")
        self.emotional_memory_strength = 0.5
        self.context_emotion_binding = 0.5
        self.emotional_learning_rate = 0.08
        self.binding_history = []
        self.emotional_memory_map = {}
        self.learning_failure_ticks = 0
        self.chronic_learning_failure = False
        self.bindings_formed = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        context_label = prior.get("HippocampalContextEncoder", {}).get("context_label", "")
        encoding_quality = prior.get("HippocampalContextEncoder", {}).get("encoding_quality", 0.6)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        striosome_rate = prior.get("StriosomeLimbicLoop", {}).get("emotional_learning_rate", 0.1)

        # Bind emotion to context
        emotional_signal = abs(valence) * 0.5 + fear * 0.3 + reward * 0.2
        self.context_emotion_binding = emotional_signal * encoding_quality * (1.0 - stress * 0.2)

        if context_label and self.context_emotion_binding > 0.2:
            existing = self.emotional_memory_map.get(context_label, {"valence": 0.0, "strength": 0.0})
            new_valence = existing["valence"] + (valence - existing["valence"]) * self.emotional_learning_rate
            new_strength = min(1.0, existing["strength"] + self.context_emotion_binding * 0.05)
            self.emotional_memory_map[context_label] = {"valence": round(new_valence, 3), "strength": round(new_strength, 3)}
            self.bindings_formed += 1
            if len(self.emotional_memory_map) > 100:
                weakest = min(self.emotional_memory_map, key=lambda k: self.emotional_memory_map[k]["strength"])
                del self.emotional_memory_map[weakest]

        self.emotional_memory_strength = sum(m["strength"] for m in self.emotional_memory_map.values()) / max(1, len(self.emotional_memory_map))

        self.binding_history.append(self.context_emotion_binding)
        if len(self.binding_history) > 40:
            self.binding_history.pop(0)

        avg_binding = sum(self.binding_history[-15:]) / min(15, len(self.binding_history))
        self.learning_failure_ticks = self.learning_failure_ticks + 1 if avg_binding < 0.05 else max(0, self.learning_failure_ticks - 1)
        was_failing = self.chronic_learning_failure
        self.chronic_learning_failure = self.learning_failure_ticks > 20
        if self.chronic_learning_failure and not was_failing:
            self.feed_to_memory({"event": "emotional_memory_binding_failure",
                                  "note": "Emotions not binding to context — emotional events not teaching anything"})

        return {
            "emotional_memory_strength": round(self.emotional_memory_strength, 3),
            "context_emotion_binding": round(self.context_emotion_binding, 3),
            "bindings_formed": self.bindings_formed,
            "emotional_memory_size": len(self.emotional_memory_map),
            "chronic_learning_failure": self.chronic_learning_failure,
        }

    def _overnight(self):
        # Consolidate: strengthen strong bindings, fade weak ones
        for k in list(self.emotional_memory_map.keys()):
            m = self.emotional_memory_map[k]
            if m["strength"] > 0.5:
                self.emotional_memory_map[k]["strength"] = min(1.0, m["strength"] + 0.01)
            else:
                self.emotional_memory_map[k]["strength"] = max(0.0, m["strength"] - 0.02)
            if self.emotional_memory_map[k]["strength"] < 0.01:
                del self.emotional_memory_map[k]
        self.learning_failure_ticks = max(0, self.learning_failure_ticks - 6)
        self.chronic_learning_failure = self.learning_failure_ticks > 20
        self.binding_history.clear()
        return {"overnight": "emotional_memory_consolidation", "bindings": len(self.emotional_memory_map)}
