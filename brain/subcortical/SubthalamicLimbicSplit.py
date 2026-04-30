from brain.base_mechanism import BrainMechanism

class SubthalamicLimbicSplit(BrainMechanism):
    """
    STN limbic territory — emotional content in the stop signal.
    Emotional conflict triggers stronger/longer pauses than cognitive conflict.
    Emotional stop signal bleeds into cognition — emotions brake rational thought.
    """

    def __init__(self):
        super().__init__("SubthalamicLimbicSplit")
        self.limbic_stop_signal = 0.0
        self.cognitive_stop_signal = 0.0
        self.emotional_brake_bleed = 0.0
        self.bleed_history = []
        self.stop_history = []
        self.chronic_emotional_brake = False
        self.emotional_brake_ticks = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        grief = prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        cognitive_conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        stn_global = prior.get("SubthalamicImpulseSuppressor", {}).get("stn_activity", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        emotional_load = fear * 0.4 + grief * 0.3 + max(0.0, -valence) * 0.3
        self.limbic_stop_signal = min(1.0, emotional_load + stn_global * 0.3)
        self.cognitive_stop_signal = cognitive_conflict * 0.7 + stn_global * 0.3
        self.emotional_brake_bleed = min(1.0, max(0.0, self.limbic_stop_signal - self.cognitive_stop_signal) * stress)

        self.bleed_history.append(self.emotional_brake_bleed)
        self.stop_history.append(self.limbic_stop_signal)
        for h in [self.bleed_history, self.stop_history]:
            if len(h) > 40:
                h.pop(0)

        avg_bleed = sum(self.bleed_history[-15:]) / min(15, len(self.bleed_history))
        self.emotional_brake_ticks = self.emotional_brake_ticks + 1 if avg_bleed > 0.35 else max(0, self.emotional_brake_ticks - 1)
        was_chronic = self.chronic_emotional_brake
        self.chronic_emotional_brake = self.emotional_brake_ticks > 15
        if self.chronic_emotional_brake and not was_chronic:
            self.feed_to_memory({"event": "emotional_brake_bleed", "bleed": round(avg_bleed, 3),
                                  "note": "Emotional stop signal bleeding into cognitive processing"})

        return {
            "limbic_stop_signal": round(self.limbic_stop_signal, 3),
            "cognitive_stop_signal": round(self.cognitive_stop_signal, 3),
            "emotional_brake_bleed": round(self.emotional_brake_bleed, 3),
            "total_stop": round(max(self.limbic_stop_signal, self.cognitive_stop_signal), 3),
            "chronic_emotional_brake": self.chronic_emotional_brake,
        }

    def _overnight(self):
        self.emotional_brake_ticks = max(0, self.emotional_brake_ticks - 5)
        self.chronic_emotional_brake = self.emotional_brake_ticks > 15
        self.bleed_history.clear()
        return {"overnight": "stn_limbic_split_reset"}
