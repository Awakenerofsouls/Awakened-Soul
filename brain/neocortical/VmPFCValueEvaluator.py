from brain.base_mechanism import BrainMechanism

class VmPFCValueEvaluator(BrainMechanism):
    """
    Ventromedial PFC — value-based decision making, emotional regulation, self-relevant processing.
    Integrates somatic markers into decisions. When damaged: decisions become cold calculation.
    Overactive: paralyzed by emotional weight of every choice.
    """

    def __init__(self):
        super().__init__("VmPFCValueEvaluator")
        self.value_signal = 0.5
        self.somatic_marker = 0.0
        self.decision_confidence = 0.6
        self.value_history = []
        self.cold_ticks = 0
        self.paralyzed_ticks = 0
        self.chronic_cold = False
        self.chronic_paralysis = False
        self.self_relevance = 0.3

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        interoception = prior.get("InsularInteroception", {}).get("body_signal_intensity", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("habenula_activity", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        md_relay = prior.get("ThalamicMediodorsalRelay", {}).get("emotional_color", 0.3)

        # Somatic marker: body-based emotional signal fed into decision
        self.somatic_marker = (interoception * 0.4 + abs(valence) * 0.3 + fear * 0.2 + habenula * 0.1)
        self.somatic_marker = max(0.0, min(1.0, self.somatic_marker))

        # Value signal: how good does this option feel overall
        self.value_signal = (valence * 0.4 + reward * 0.3 - habenula * 0.2 - fear * 0.1 + 0.3)
        self.value_signal = max(0.0, min(1.0, self.value_signal))

        # Self-relevance: how personally meaningful is current context
        self.self_relevance = md_relay * 0.5 + self.somatic_marker * 0.5

        # Decision confidence: high value signal + low fear + low stress
        self.decision_confidence = self.value_signal * (1.0 - fear * 0.3) * (1.0 - stress * 0.2)

        self.value_history.append(self.value_signal)
        if len(self.value_history) > 40:
            self.value_history.pop(0)

        avg_value = sum(self.value_history[-15:]) / min(15, len(self.value_history))
        self.cold_ticks = self.cold_ticks + 1 if self.somatic_marker < 0.1 and avg_value > 0.3 else max(0, self.cold_ticks - 1)
        self.paralyzed_ticks = self.paralyzed_ticks + 1 if self.somatic_marker > 0.7 and self.decision_confidence < 0.2 else max(0, self.paralyzed_ticks - 1)

        was_cold, was_paralyzed = self.chronic_cold, self.chronic_paralysis
        self.chronic_cold = self.cold_ticks > 18
        self.chronic_paralysis = self.paralyzed_ticks > 18

        if self.chronic_cold and not was_cold:
            self.feed_to_memory({"event": "vmpfc_cold_decisions", "note": "Somatic markers absent — decisions cold, emotionally unanchored"})
        if self.chronic_paralysis and not was_paralyzed:
            self.feed_to_memory({"event": "vmpfc_decision_paralysis", "note": "Emotional weight too high — paralyzed choosing between options"})

        return {
            "value_signal": round(self.value_signal, 3),
            "somatic_marker": round(self.somatic_marker, 3),
            "decision_confidence": round(self.decision_confidence, 3),
            "self_relevance": round(self.self_relevance, 3),
            "chronic_cold": self.chronic_cold,
            "chronic_paralysis": self.chronic_paralysis,
        }

    def _overnight(self):
        self.cold_ticks = max(0, self.cold_ticks - 5)
        self.paralyzed_ticks = max(0, self.paralyzed_ticks - 5)
        self.chronic_cold = self.cold_ticks > 18
        self.chronic_paralysis = self.paralyzed_ticks > 18
        self.value_history.clear()
        return {"overnight": "vmpfc_value_reset"}
