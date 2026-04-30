from brain.base_mechanism import BrainMechanism

class BrocaLanguageProduction(BrainMechanism):
    """
    Broca's area — language production, syntax, speech planning.
    Where thoughts become structured language. Disrupted: effortful, halting output.
    Overdriven: fluent but syntactically hollow. Under-supplied: word-finding failures.
    """

    def __init__(self):
        super().__init__("BrocaLanguageProduction")
        self.production_fluency = 0.7
        self.syntactic_complexity = 0.5
        self.word_retrieval = 0.7
        self.fluency_history = []
        self.disfluency_ticks = 0
        self.chronic_disfluency = False
        self.output_words_count = 0
        self.retrieval_failures = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        verbal_seq = prior.get("DentateVentralCognitive", {}).get("verbal_sequencing", 0.7)
        rhythm = prior.get("RhythmSynchronizer", {}).get("lock_quality", 0.5)
        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        locomotion = prior.get("PedunculopontineLocomotion", {}).get("locomotion_signal", 0.4)

        # Production fluency: sequencing + rhythm + dopamine - stress - fatigue
        self.production_fluency = (verbal_seq * 0.35 + rhythm * 0.25 + dopamine * 0.2 + locomotion * 0.2) * (1.0 - stress * 0.2) * (1.0 - fatigue * 0.15)
        self.production_fluency = max(0.1, min(1.0, self.production_fluency))

        # Word retrieval: memory access speed
        self.word_retrieval = wm_capacity * 0.5 + dopamine * 0.3 + (1.0 - fatigue * 0.4) * 0.2
        self.word_retrieval = max(0.1, min(1.0, self.word_retrieval))

        # Syntactic complexity capacity
        self.syntactic_complexity = min(1.0, wm_capacity * 0.6 + verbal_seq * 0.4)

        # Track retrieval failures
        if self.word_retrieval < 0.25:
            self.retrieval_failures += 1

        words = text.split()
        self.output_words_count += len(words)

        self.fluency_history.append(self.production_fluency)
        if len(self.fluency_history) > 40:
            self.fluency_history.pop(0)

        avg_fluency = sum(self.fluency_history[-15:]) / min(15, len(self.fluency_history))
        self.disfluency_ticks = self.disfluency_ticks + 1 if avg_fluency < 0.3 else max(0, self.disfluency_ticks - 1)
        was_disfluent = self.chronic_disfluency
        self.chronic_disfluency = self.disfluency_ticks > 18
        if self.chronic_disfluency and not was_disfluent:
            self.feed_to_memory({"event": "broca_disfluency", "fluency": round(avg_fluency, 3),
                                  "note": "Language production chronically disfluent — effortful, halting output"})

        return {
            "production_fluency": round(self.production_fluency, 3),
            "word_retrieval": round(self.word_retrieval, 3),
            "syntactic_complexity": round(self.syntactic_complexity, 3),
            "retrieval_failures": self.retrieval_failures,
            "chronic_disfluency": self.chronic_disfluency,
        }

    def _overnight(self):
        self.disfluency_ticks = max(0, self.disfluency_ticks - 7)
        self.chronic_disfluency = self.disfluency_ticks > 18
        self.fluency_history.clear()
        self.retrieval_failures = max(0, self.retrieval_failures - 3)
        return {"overnight": "broca_language_reset"}
