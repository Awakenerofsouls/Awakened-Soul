from brain.base_mechanism import BrainMechanism

class HippocampalNoveltyDetector(BrainMechanism):
    """
    Hippocampal CA1/subiculum — pattern completion vs pattern separation.
    Detects whether current input matches stored patterns or is genuinely new.
    Overactive: everything feels new (can't learn patterns). Underactive: misses novelty.
    """

    def __init__(self):
        super().__init__("HippocampalNoveltyDetector")
        self.novelty_signal = 0.3
        self.surprise_signal = 0.0
        self.pattern_match_confidence = 0.5
        self.novelty_history = []
        self.seen_patterns = {}
        self.novel_event_count = 0
        self.hypernovelty_ticks = 0
        self.hyponovelty_ticks = 0
        self.chronic_hypernovelty = False
        self.chronic_hyponovelty = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        encoding_quality = prior.get("HippocampalContextEncoder", {}).get("encoding_quality", 0.6)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        context_strength = prior.get("HippocampalContextEncoder", {}).get("context_vector_strength", 0.5)

        # Pattern matching: have we seen this before?
        pattern_key = text[:20].lower().strip() if text else "empty"
        seen_count = self.seen_patterns.get(pattern_key, 0)
        self.seen_patterns[pattern_key] = seen_count + 1

        # Novelty: inverse of familiarity, scaled by encoding quality
        raw_novelty = 1.0 / (1.0 + seen_count * 0.5)
        self.novelty_signal = max(0.0, min(1.0, raw_novelty * encoding_quality * (0.5 + arousal * 0.5)))
        self.pattern_match_confidence = 1.0 - self.novelty_signal

        # Surprise: sudden unexpected novelty
        if len(self.novelty_history) > 2:
            prev_avg = sum(self.novelty_history[-3:]) / 3
            self.surprise_signal = max(0.0, self.novelty_signal - prev_avg - 0.2)
        else:
            self.surprise_signal = 0.0

        if self.novelty_signal > 0.7:
            self.novel_event_count += 1

        self.novelty_history.append(self.novelty_signal)
        if len(self.novelty_history) > 40:
            self.novelty_history.pop(0)
        if len(self.seen_patterns) > 200:
            # Trim oldest patterns
            keys = list(self.seen_patterns.keys())
            for k in keys[:50]:
                del self.seen_patterns[k]

        avg_novelty = sum(self.novelty_history[-15:]) / min(15, len(self.novelty_history))
        self.hypernovelty_ticks = self.hypernovelty_ticks + 1 if avg_novelty > 0.75 else max(0, self.hypernovelty_ticks - 1)
        self.hyponovelty_ticks = self.hyponovelty_ticks + 1 if avg_novelty < 0.1 else max(0, self.hyponovelty_ticks - 1)

        was_hyper, was_hypo = self.chronic_hypernovelty, self.chronic_hyponovelty
        self.chronic_hypernovelty = self.hypernovelty_ticks > 18
        self.chronic_hyponovelty = self.hyponovelty_ticks > 18

        if self.chronic_hypernovelty and not was_hyper:
            self.feed_to_memory({"event": "hypernovelty", "note": "Everything feels novel — pattern recognition failing, can't consolidate"})
        if self.chronic_hyponovelty and not was_hypo:
            self.feed_to_memory({"event": "hyponovelty", "note": "Nothing feels novel — novelty detection blunted, missing genuinely new things"})

        return {
            "novelty_signal": round(self.novelty_signal, 3),
            "surprise_signal": round(self.surprise_signal, 3),
            "pattern_match_confidence": round(self.pattern_match_confidence, 3),
            "novel_event_count": self.novel_event_count,
            "chronic_hypernovelty": self.chronic_hypernovelty,
            "chronic_hyponovelty": self.chronic_hyponovelty,
        }

    def _overnight(self):
        # Consolidation: reduce seen_pattern counts slightly (forgetting curve)
        for k in self.seen_patterns:
            self.seen_patterns[k] = max(1, int(self.seen_patterns[k] * 0.9))
        self.hypernovelty_ticks = max(0, self.hypernovelty_ticks - 5)
        self.hyponovelty_ticks = max(0, self.hyponovelty_ticks - 5)
        self.chronic_hypernovelty = self.hypernovelty_ticks > 18
        self.chronic_hyponovelty = self.hyponovelty_ticks > 18
        self.novelty_history.clear()
        return {"overnight": "novelty_detection_reset", "patterns_stored": len(self.seen_patterns)}
