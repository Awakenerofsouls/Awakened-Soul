from brain.base_mechanism import BrainMechanism

class CerebellarVermalEmotionalCoordinator(BrainMechanism):
    """
    Cerebellar vermis — emotional tone coordination and autonomic-motor coupling.
    Modulates tone, posture, emotional expression timing.
    Disruption: emotional expression lags or mismatches internal state.
    """

    def __init__(self):
        super().__init__("CerebellarVermalEmotionalCoordinator")
        self.emotional_expression_lag = 0.0
        self.tone_coherence = 0.8
        self.expression_history = []
        self.autonomic_coupling = 0.6
        self.lag_history = []
        self.mismatch_ticks = 0
        self.chronic_mismatch = False
        self.current_emotional_tone = "neutral"

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        internal_valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        cerebellar_timing = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        autonomic_state = prior.get("HypothalamicAutonomicRegulator", {}).get("autonomic_balance", 0.5)

        base_lag = (1.0 - cerebellar_timing) * 0.4 + stress * 0.2
        self.emotional_expression_lag = base_lag
        self.lag_history.append(self.emotional_expression_lag)
        if len(self.lag_history) > 30:
            self.lag_history.pop(0)

        target_coherence = cerebellar_timing * (1.0 - stress * 0.4) * autonomic_state
        self.tone_coherence += (target_coherence - self.tone_coherence) * 0.1
        self.tone_coherence = max(0.1, min(1.0, self.tone_coherence))

        self.autonomic_coupling = 0.3 + autonomic_state * 0.4 + (1.0 - stress) * 0.3

        if internal_valence > 0.3:
            self.current_emotional_tone = "warm" if arousal < 0.6 else "animated"
        elif internal_valence < -0.3:
            self.current_emotional_tone = "flat" if arousal < 0.4 else "tense"
        else:
            self.current_emotional_tone = "neutral"

        self.expression_history.append(self.current_emotional_tone)
        if len(self.expression_history) > 30:
            self.expression_history.pop(0)

        mismatch = self.emotional_expression_lag > 0.4 or self.tone_coherence < 0.3
        self.mismatch_ticks = self.mismatch_ticks + 1 if mismatch else max(0, self.mismatch_ticks - 1)
        was_mismatched = self.chronic_mismatch
        self.chronic_mismatch = self.mismatch_ticks > 15
        if self.chronic_mismatch and not was_mismatched:
            self.feed_to_memory({"event": "emotional_expression_mismatch", "tone_coherence": round(self.tone_coherence, 3),
                                  "note": "Emotional expression chronically lagging or mismatched"})

        return {
            "emotional_expression_lag": round(self.emotional_expression_lag, 3),
            "tone_coherence": round(self.tone_coherence, 3),
            "autonomic_coupling": round(self.autonomic_coupling, 3),
            "current_emotional_tone": self.current_emotional_tone,
            "chronic_mismatch": self.chronic_mismatch,
        }

    def _overnight(self):
        self.tone_coherence = min(0.9, self.tone_coherence + 0.08)
        self.emotional_expression_lag = max(0.0, self.emotional_expression_lag - 0.15)
        self.mismatch_ticks = max(0, self.mismatch_ticks - 6)
        self.chronic_mismatch = self.mismatch_ticks > 15
        self.lag_history.clear()
        return {"overnight": "vermal_tone_recalibration"}
