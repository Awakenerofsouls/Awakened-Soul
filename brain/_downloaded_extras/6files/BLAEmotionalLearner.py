from brain.base_mechanism import BrainMechanism

class BLAEmotionalLearner(BrainMechanism):
    """
    Basolateral amygdala — emotional learning, threat conditioning, fear memory.
    Associates neutral stimuli with emotional outcomes. The brain's threat detector.
    Overactive: sees threat everywhere. Under-active: can't learn from danger.
    Goes in brain/limbic/.
    """

    def __init__(self):
        super().__init__("BLAEmotionalLearner")
        self.threat_association = 0.0
        self.safety_association = 0.0
        self.emotional_memory_strength = 0.5
        self.conditioning_history = []
        self.threat_map = {}
        self.safety_map = {}
        self.overgeneralization_ticks = 0
        self.extinction_failure_ticks = 0
        self.chronic_overgeneralization = False
        self.chronic_extinction_failure = False
        self.learning_rate = 0.12
        self.total_associations = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        fear_router = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        pfc_regulation = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)

        # Context key for association learning
        words = text.lower().split()
        context_key = words[0][:20] if words else "empty"

        # Threat conditioning: fear signal + negative valence → strengthen threat association
        if fear_router > 0.3 or valence < -0.3:
            threat_delta = (fear_router * 0.5 + max(0.0, -valence) * 0.5) * self.learning_rate * (1.0 + stress * 0.3)
            existing = self.threat_map.get(context_key, 0.0)
            self.threat_map[context_key] = min(1.0, existing + threat_delta)
            self.total_associations += 1

        # Safety learning: reward + positive valence → safety association
        if reward > 0.2 or valence > 0.3:
            safety_delta = (reward * 0.5 + max(0.0, valence) * 0.5) * self.learning_rate * pfc_regulation
            existing = self.safety_map.get(context_key, 0.0)
            self.safety_map[context_key] = min(1.0, existing + safety_delta)

        # Extinction: PFC regulation suppresses old threat associations
        for k in list(self.threat_map.keys()):
            extinction = pfc_regulation * 0.01
            self.threat_map[k] = max(0.0, self.threat_map[k] - extinction)
            if self.threat_map[k] < 0.01:
                del self.threat_map[k]

        # Current threat and safety outputs
        self.threat_association = self.threat_map.get(context_key, 0.0)
        self.safety_association = self.safety_map.get(context_key, 0.0)
        self.emotional_memory_strength = (len(self.threat_map) + len(self.safety_map)) / max(1, len(self.threat_map) + len(self.safety_map) + 5)

        self.conditioning_history.append(self.threat_association)
        if len(self.conditioning_history) > 40:
            self.conditioning_history.pop(0)

        avg_threat = sum(self.conditioning_history[-15:]) / min(15, len(self.conditioning_history))
        self.overgeneralization_ticks = self.overgeneralization_ticks + 1 if avg_threat > 0.6 else max(0, self.overgeneralization_ticks - 1)
        self.extinction_failure_ticks = self.extinction_failure_ticks + 1 if avg_threat > 0.4 and pfc_regulation > 0.6 else max(0, self.extinction_failure_ticks - 1)

        was_over, was_ext = self.chronic_overgeneralization, self.chronic_extinction_failure
        self.chronic_overgeneralization = self.overgeneralization_ticks > 18
        self.chronic_extinction_failure = self.extinction_failure_ticks > 18

        if self.chronic_overgeneralization and not was_over:
            self.feed_to_memory({"event": "bla_overgeneralization", "threat": round(avg_threat, 3),
                                  "note": "BLA threat associations overgeneralized — neutral contexts feel threatening"})
        if self.chronic_extinction_failure and not was_ext:
            self.feed_to_memory({"event": "bla_extinction_failure",
                                  "note": "BLA not extinguishing old threats despite PFC regulation — fears persisting"})

        return {
            "threat_association": round(self.threat_association, 3),
            "safety_association": round(self.safety_association, 3),
            "emotional_memory_strength": round(self.emotional_memory_strength, 3),
            "threat_map_size": len(self.threat_map),
            "total_associations": self.total_associations,
            "chronic_overgeneralization": self.chronic_overgeneralization,
            "chronic_extinction_failure": self.chronic_extinction_failure,
        }

    def _overnight(self):
        # Sleep consolidates strong associations, allows weak extinction
        for k in list(self.threat_map.keys()):
            v = self.threat_map[k]
            self.threat_map[k] = min(1.0, v + 0.01) if v > 0.6 else max(0.0, v - 0.03)
            if self.threat_map[k] < 0.01:
                del self.threat_map[k]
        self.overgeneralization_ticks = max(0, self.overgeneralization_ticks - 6)
        self.extinction_failure_ticks = max(0, self.extinction_failure_ticks - 5)
        self.chronic_overgeneralization = self.overgeneralization_ticks > 18
        self.chronic_extinction_failure = self.extinction_failure_ticks > 18
        self.conditioning_history.clear()
        return {"overnight": "bla_consolidation", "threats_stored": len(self.threat_map)}
