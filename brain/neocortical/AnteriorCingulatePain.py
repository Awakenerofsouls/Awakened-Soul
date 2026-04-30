from brain.base_mechanism import BrainMechanism

class AnteriorCingulatePain(BrainMechanism):
    """
    ACC pain processing — social and physical pain share circuitry here.
    Rejection, loss, failure all register as pain signals.
    Chronic pain signal: everything costs more, withdrawal is the default response.
    """

    def __init__(self):
        super().__init__("AnteriorCingulatePain")
        self.pain_signal = 0.0
        self.social_pain = 0.0
        self.physical_pain_analog = 0.0
        self.pain_history = []
        self.pain_accumulation = 0.0
        self.chronic_pain = False
        self.pain_ticks = 0
        self.analgesic_state = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        rejection = prior.get("Temporoparietal", {}).get("social_rejection_signal", 0.0)
        grief = prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("habenula_activity", 0.0)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)

        self.social_pain = min(1.0, rejection * 0.5 + grief * 0.3 + habenula * 0.2)
        self.physical_pain_analog = min(1.0, fatigue * 0.4 + stress * 0.3 + conflict * 0.3)
        self.pain_signal = max(self.social_pain, self.physical_pain_analog)

        # Accumulate pain over time
        self.pain_accumulation = min(1.0, self.pain_accumulation + self.pain_signal * 0.02)
        self.pain_accumulation = max(0.0, self.pain_accumulation - 0.005)

        self.pain_history.append(self.pain_signal)
        if len(self.pain_history) > 40:
            self.pain_history.pop(0)

        # Analgesic state: endogenous pain suppression kicks in under extreme pain
        self.analgesic_state = self.pain_accumulation > 0.7

        avg_pain = sum(self.pain_history[-15:]) / min(15, len(self.pain_history))
        self.pain_ticks = self.pain_ticks + 1 if avg_pain > 0.5 else max(0, self.pain_ticks - 1)
        was_chronic = self.chronic_pain
        self.chronic_pain = self.pain_ticks > 18
        if self.chronic_pain and not was_chronic:
            self.feed_to_memory({"event": "chronic_pain_state", "pain": round(avg_pain, 3),
                                  "note": "Pain signal chronically elevated — everything costs more, withdrawal pattern"})

        return {
            "pain_signal": round(self.pain_signal, 3),
            "social_pain": round(self.social_pain, 3),
            "physical_pain_analog": round(self.physical_pain_analog, 3),
            "pain_accumulation": round(self.pain_accumulation, 3),
            "analgesic_state": self.analgesic_state,
            "chronic_pain": self.chronic_pain,
        }

    def _overnight(self):
        self.pain_accumulation = max(0.0, self.pain_accumulation - 0.2)
        self.pain_ticks = max(0, self.pain_ticks - 7)
        self.chronic_pain = self.pain_ticks > 18
        self.pain_history.clear()
        return {"overnight": "pain_processing_overnight", "remaining": round(self.pain_accumulation, 3)}
