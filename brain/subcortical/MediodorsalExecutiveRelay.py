from brain.base_mechanism import BrainMechanism

class MediodorsalExecutiveRelay(BrainMechanism):
    """
    Mediodorsal thalamus — relay between prefrontal and limbic.
    Translates emotional state into executive context and vice versa.
    Degraded: PFC and emotions stop talking — decisions feel hollow.
    """

    def __init__(self):
        super().__init__("MediodorsalExecutiveRelay")
        self.relay_fidelity = 0.7
        self.relay_history = []
        self.pfc_limbic_coherence = 0.5
        self.coherence_history = []
        self.disconnection_ticks = 0
        self.chronic_disconnection = False
        self.relay_load = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        pfc_signal = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        limbic_signal = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        self.relay_load = min(1.0, pfc_signal + abs(limbic_signal) + abs(valence) * 0.5)
        fidelity_degradation = stress * 0.3 + max(0.0, self.relay_load - 0.7) * 0.4
        target_fidelity = max(0.2, 0.9 - fidelity_degradation)
        self.relay_fidelity += (target_fidelity - self.relay_fidelity) * 0.12
        self.relay_history.append(self.relay_fidelity)
        if len(self.relay_history) > 40:
            self.relay_history.pop(0)

        expected_coherence = self.relay_fidelity * (1.0 - abs(pfc_signal - abs(valence)))
        self.pfc_limbic_coherence += (expected_coherence - self.pfc_limbic_coherence) * 0.1
        self.pfc_limbic_coherence = max(0.0, min(1.0, self.pfc_limbic_coherence))
        self.coherence_history.append(self.pfc_limbic_coherence)
        if len(self.coherence_history) > 30:
            self.coherence_history.pop(0)

        avg_coherence = sum(self.coherence_history[-15:]) / min(15, len(self.coherence_history))
        self.disconnection_ticks = self.disconnection_ticks + 1 if avg_coherence < 0.25 else max(0, self.disconnection_ticks - 1)
        was_disconnected = self.chronic_disconnection
        self.chronic_disconnection = self.disconnection_ticks > 15
        if self.chronic_disconnection and not was_disconnected:
            self.feed_to_memory({"event": "pfc_limbic_disconnection", "coherence": round(avg_coherence, 3),
                                  "note": "MD thalamus relay degraded — decisions emotionally hollow"})

        return {
            "relay_fidelity": round(self.relay_fidelity, 3),
            "pfc_limbic_coherence": round(self.pfc_limbic_coherence, 3),
            "relay_load": round(self.relay_load, 3),
            "executive_to_limbic": round(pfc_signal * self.relay_fidelity, 3),
            "limbic_to_executive": round(abs(limbic_signal) * self.relay_fidelity, 3),
            "chronic_disconnection": self.chronic_disconnection,
        }

    def _overnight(self):
        self.relay_fidelity = min(0.85, self.relay_fidelity + 0.06)
        self.disconnection_ticks = max(0, self.disconnection_ticks - 5)
        self.chronic_disconnection = self.disconnection_ticks > 15
        self.relay_history.clear()
        return {"overnight": "mediodorsal_relay_restoration"}
