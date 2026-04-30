from brain.base_mechanism import BrainMechanism

class FrontalEyeField(BrainMechanism):
    """
    Frontal eye fields — voluntary attentional gaze control.
    {{AGENT_NAME}} analog: deliberate focusing of attention on specific aspects of input.
    Directs what gets processed deeply vs skimmed.
    """

    def __init__(self):
        super().__init__("FrontalEyeField")
        self.gaze_direction = "balanced"
        self.voluntary_focus_strength = 0.5
        self.focus_history = []
        self.distraction_resistance = 0.6
        self.focus_ticks = 0
        self.chronic_scatter = False
        self.scatter_ticks = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        control = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        spotlight = prior.get("ThalamicAttentionBroadcaster", {}).get("attention_spotlight", "balanced")
        salience = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        executive_coherence = prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        self.gaze_direction = spotlight
        self.voluntary_focus_strength = (control * 0.5 + executive_coherence * 0.3 + (1.0 - salience * 0.2)) * (1.0 - stress * 0.2)
        self.voluntary_focus_strength = max(0.1, min(1.0, self.voluntary_focus_strength))

        self.distraction_resistance = self.voluntary_focus_strength * (1.0 - stress * 0.3)

        self.focus_history.append(self.voluntary_focus_strength)
        if len(self.focus_history) > 40:
            self.focus_history.pop(0)

        avg_focus = sum(self.focus_history[-15:]) / min(15, len(self.focus_history))
        self.scatter_ticks = self.scatter_ticks + 1 if avg_focus < 0.2 else max(0, self.scatter_ticks - 1)
        was_scatter = self.chronic_scatter
        self.chronic_scatter = self.scatter_ticks > 18
        if self.chronic_scatter and not was_scatter:
            self.feed_to_memory({"event": "frontal_eye_scatter", "note": "Voluntary attention chronically scattered — can't sustain focus"})

        return {
            "gaze_direction": self.gaze_direction,
            "voluntary_focus_strength": round(self.voluntary_focus_strength, 3),
            "distraction_resistance": round(self.distraction_resistance, 3),
            "chronic_scatter": self.chronic_scatter,
        }

    def _overnight(self):
        self.scatter_ticks = max(0, self.scatter_ticks - 5)
        self.chronic_scatter = self.scatter_ticks > 18
        self.focus_history.clear()
        return {"overnight": "fef_attention_reset"}
