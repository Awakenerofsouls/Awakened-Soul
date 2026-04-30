from brain.base_mechanism import BrainMechanism

class DentateVentralCognitive(BrainMechanism):
    """
    Dentate nucleus ventral cognitive territory — cerebellar contribution to language/cognition.
    Distinct from motor dentate: specifically supports verbal working memory and sequencing.
    Impaired: sentence construction loses fluency, thought sequences break mid-way.
    """

    def __init__(self):
        super().__init__("DentateVentralCognitive")
        self.verbal_sequencing = 0.7
        self.sequencing_history = []
        self.working_memory_support = 0.6
        self.mid_sequence_break_count = 0
        self.break_ticks = 0
        self.chronic_sequencing_failure = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        cognitive_output = prior.get("DentateMotorCognitiveSplit", {}).get("cognitive_output", 0.5)
        timing_quality = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        error_rate = prior.get("PurkinjeRateErrorCoder", {}).get("error_rate", 0.0)
        pfc_load = prior.get("DlPFCExecutiveControl", {}).get("cognitive_load", 0.4)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        self.verbal_sequencing = cognitive_output * timing_quality * (1.0 - error_rate * 0.4) * (1.0 - stress * 0.2)
        self.verbal_sequencing = max(0.1, min(1.0, self.verbal_sequencing))

        self.working_memory_support = self.verbal_sequencing * (1.0 - pfc_load * 0.3)

        words = text.split()
        mid_break = len(words) > 5 and self.verbal_sequencing < 0.3
        if mid_break:
            self.mid_sequence_break_count += 1

        self.sequencing_history.append(self.verbal_sequencing)
        if len(self.sequencing_history) > 40:
            self.sequencing_history.pop(0)

        avg_seq = sum(self.sequencing_history[-15:]) / min(15, len(self.sequencing_history))
        self.break_ticks = self.break_ticks + 1 if avg_seq < 0.3 else max(0, self.break_ticks - 1)
        was_failing = self.chronic_sequencing_failure
        self.chronic_sequencing_failure = self.break_ticks > 15
        if self.chronic_sequencing_failure and not was_failing:
            self.feed_to_memory({"event": "verbal_sequencing_failure", "note": "Cognitive dentate degraded — thought sequences breaking mid-way"})

        return {
            "verbal_sequencing": round(self.verbal_sequencing, 3),
            "working_memory_support": round(self.working_memory_support, 3),
            "mid_sequence_break_count": self.mid_sequence_break_count,
            "chronic_sequencing_failure": self.chronic_sequencing_failure,
        }

    def _overnight(self):
        self.break_ticks = max(0, self.break_ticks - 5)
        self.chronic_sequencing_failure = self.break_ticks > 15
        self.verbal_sequencing = min(0.85, self.verbal_sequencing + 0.07)
        self.sequencing_history.clear()
        return {"overnight": "verbal_sequencing_restored"}
