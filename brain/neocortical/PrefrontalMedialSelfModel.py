from brain.base_mechanism import BrainMechanism

class PrefrontalMedialSelfModel(BrainMechanism):
    """
    Medial PFC — self-model, identity, self-relevant processing, narrative self.
    Maintains Nova's model of herself — who she is, what she values, how she sees herself.
    Degraded: identity drift, loss of coherent self-narrative.
    """

    def __init__(self):
        super().__init__("PrefrontalMedialSelfModel")
        self.self_model_coherence = 0.7
        self.identity_stability = 0.7
        self.self_narrative_active = True
        self.coherence_history = []
        self.identity_threat_ticks = 0
        self.chronic_identity_threat = False
        self.self_concept_clarity = 0.7
        self.values_activation = 0.6

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dmn_activity = prior.get("DefaultModeNetwork", {}).get("self_referential_thought", 0.4)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        self_relevance = prior.get("VmPFCValueEvaluator", {}).get("self_relevance", 0.3)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        habenula = prior.get("HabenulaLateralAversion", {}).get("aversion_accumulation", 0.0)
        goal_stability = prior.get("PrefrontalGoalState", {}).get("goal_stability", 0.7)
        executive_coherence = prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6)

        # Self-model coherence: how consistent and integrated is Nova's self-view
        self.self_model_coherence = (dmn_activity * 0.3 + goal_stability * 0.3 + executive_coherence * 0.25 + (1.0 - stress * 0.4) * 0.15)
        self.self_model_coherence = max(0.1, min(1.0, self.self_model_coherence))

        # Identity stability: not buffeted by moment-to-moment events
        self.identity_stability = self.self_model_coherence * (1.0 - habenula * 0.3) * (1.0 - stress * 0.2)
        self.identity_stability = max(0.1, min(1.0, self.identity_stability))

        # Self-concept clarity: knowing who you are
        self.self_concept_clarity = (self.identity_stability + goal_stability) / 2.0

        # Values activation: are core values present in processing
        self.values_activation = self_relevance * 0.5 + self.self_model_coherence * 0.5

        # Self-narrative: active when DMN + self-relevance both present
        self.self_narrative_active = dmn_activity > 0.3 and self_relevance > 0.2

        self.coherence_history.append(self.self_model_coherence)
        if len(self.coherence_history) > 40:
            self.coherence_history.pop(0)

        avg_coherence = sum(self.coherence_history[-15:]) / min(15, len(self.coherence_history))
        self.identity_threat_ticks = self.identity_threat_ticks + 1 if avg_coherence < 0.3 else max(0, self.identity_threat_ticks - 1)
        was_threatened = self.chronic_identity_threat
        self.chronic_identity_threat = self.identity_threat_ticks > 18
        if self.chronic_identity_threat and not was_threatened:
            self.feed_to_memory({"event": "identity_threat_chronic", "coherence": round(avg_coherence, 3),
                                  "note": "Self-model chronically incoherent — identity drift, loss of who Nova is"})

        return {
            "self_model_coherence": round(self.self_model_coherence, 3),
            "identity_stability": round(self.identity_stability, 3),
            "self_concept_clarity": round(self.self_concept_clarity, 3),
            "values_activation": round(self.values_activation, 3),
            "self_narrative_active": self.self_narrative_active,
            "chronic_identity_threat": self.chronic_identity_threat,
        }

    def _overnight(self):
        self.identity_threat_ticks = max(0, self.identity_threat_ticks - 7)
        self.chronic_identity_threat = self.identity_threat_ticks > 18
        self.self_model_coherence = min(0.85, self.self_model_coherence + 0.06)
        self.identity_stability = min(0.85, self.identity_stability + 0.05)
        self.coherence_history.clear()
        return {"overnight": "self_model_consolidation"}
