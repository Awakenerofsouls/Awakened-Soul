from brain.base_mechanism import BrainMechanism

class VisualSalienceFilter(BrainMechanism):
    """
    Superior colliculus / visual thalamus — pre-attentive salience detection.
    {{AGENT_NAME}} analog: catching important details in text before full processing.
    Overactive = distracted by everything. Underactive = misses signals.
    """

    def __init__(self):
        super().__init__("VisualSalienceFilter")
        self.detected_salience = 0.0
        self.salience_history = []
        self.detail_capture_rate = 0.7
        self.distraction_level = 0.0
        self.miss_rate = 0.0
        self.chronic_distraction = False
        self.chronic_neglect = False
        self.distraction_ticks = 0
        self.neglect_ticks = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        pulvinar_boost = prior.get("PulvinarSalienceBooster", {}).get("amplified_signal", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        cortical_excitability = prior.get("IntralaminarArousalFeed", {}).get("cortical_excitability", 0.5)

        text_features = self._compute_text_salience(text)
        raw_salience = text_features * 0.4 + pulvinar_boost * 0.3 + fear * 0.2 + arousal * 0.1
        self.detected_salience = min(1.0, raw_salience * cortical_excitability)
        self.salience_history.append(self.detected_salience)
        if len(self.salience_history) > 40:
            self.salience_history.pop(0)

        self.detail_capture_rate = min(1.0, 0.3 + self.detected_salience * 0.5 + arousal * 0.2)

        avg_salience = sum(self.salience_history[-10:]) / min(10, len(self.salience_history))
        self.distraction_level = min(1.0, avg_salience * arousal * 1.2) if avg_salience > 0.6 else 0.0
        self.miss_rate = max(0.0, 0.5 - cortical_excitability * 0.8) if arousal < 0.3 else 0.0

        self.distraction_ticks = self.distraction_ticks + 1 if self.distraction_level > 0.6 else max(0, self.distraction_ticks - 1)
        self.neglect_ticks = self.neglect_ticks + 1 if self.miss_rate > 0.3 else max(0, self.neglect_ticks - 1)

        was_distracted, was_neglecting = self.chronic_distraction, self.chronic_neglect
        self.chronic_distraction = self.distraction_ticks > 18
        self.chronic_neglect = self.neglect_ticks > 18

        if self.chronic_distraction and not was_distracted:
            self.feed_to_memory({"event": "visual_salience_overload", "note": "Pre-attentive filter overloaded — distracted"})
        if self.chronic_neglect and not was_neglecting:
            self.feed_to_memory({"event": "visual_salience_neglect", "note": "Pre-attentive filter underactive — missing signals"})

        return {
            "detected_salience": round(self.detected_salience, 3),
            "detail_capture_rate": round(self.detail_capture_rate, 3),
            "distraction_level": round(self.distraction_level, 3),
            "miss_rate": round(self.miss_rate, 3),
            "chronic_distraction": self.chronic_distraction,
            "chronic_neglect": self.chronic_neglect,
        }

    def _compute_text_salience(self, text):
        if not text:
            return 0.1
        words = text.split()
        length_factor = min(1.0, len(words) / 30.0)
        caps = sum(1 for w in words if w.isupper() and len(w) > 1)
        punct = text.count("!") + text.count("?") * 0.5
        signal_words = sum(1 for w in ["why", "how", "what", "when", "who", "help", "urgent", "important"] if w in text.lower())
        return min(1.0, length_factor * 0.4 + caps * 0.1 + punct * 0.1 + signal_words * 0.1)

    def _overnight(self):
        self.distraction_ticks = max(0, self.distraction_ticks - 5)
        self.neglect_ticks = max(0, self.neglect_ticks - 5)
        self.chronic_distraction = self.distraction_ticks > 18
        self.chronic_neglect = self.neglect_ticks > 18
        self.salience_history.clear()
        return {"overnight": "visual_salience_reset"}
