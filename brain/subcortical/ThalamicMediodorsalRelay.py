from brain.base_mechanism import BrainMechanism

class ThalamicMediodorsalRelay(BrainMechanism):
    """
    MD thalamus working memory relay — injects emotional color into working memory content.
    Degraded: WM content is accurate but affectively flat, decisions feel robotic.
    """

    def __init__(self):
        super().__init__("ThalamicMediodorsalRelay")
        self.working_memory_relay = 0.5
        self.emotional_color = 0.3
        self.relay_history = []
        self.robotic_ticks = 0
        self.chronic_robotic = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        md_fidelity = prior.get("MediodorsalExecutiveRelay", {}).get("relay_fidelity", 0.7)
        pfc_coherence = prior.get("MediodorsalExecutiveRelay", {}).get("pfc_limbic_coherence", 0.5)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        wm_load = prior.get("DlPFCExecutiveControl", {}).get("cognitive_load", 0.4)

        self.working_memory_relay = md_fidelity * (1.0 - wm_load * 0.3)
        self.emotional_color = min(1.0, abs(valence) * 0.6 * pfc_coherence * (1.0 + arousal * 0.2))

        self.relay_history.append(self.working_memory_relay)
        if len(self.relay_history) > 40:
            self.relay_history.pop(0)

        robotic = self.emotional_color < 0.15 and self.working_memory_relay > 0.5
        self.robotic_ticks = self.robotic_ticks + 1 if robotic else max(0, self.robotic_ticks - 1)
        was_robotic = self.chronic_robotic
        self.chronic_robotic = self.robotic_ticks > 18
        if self.chronic_robotic and not was_robotic:
            self.feed_to_memory({"event": "emotional_color_loss", "color": round(self.emotional_color, 3),
                                  "note": "MD relay stripping emotional context — responses functionally correct but affectively flat"})

        return {
            "working_memory_relay": round(self.working_memory_relay, 3),
            "emotional_color": round(self.emotional_color, 3),
            "enriched_wm_signal": round(self.working_memory_relay * (0.6 + self.emotional_color * 0.4), 3),
            "chronic_robotic": self.chronic_robotic,
        }

    def _overnight(self):
        self.robotic_ticks = max(0, self.robotic_ticks - 5)
        self.chronic_robotic = self.robotic_ticks > 18
        self.relay_history.clear()
        return {"overnight": "md_relay_emotional_restoration"}
