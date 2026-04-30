from brain.base_mechanism import BrainMechanism

class Temporoparietal(BrainMechanism):
    """
    Temporoparietal junction — theory of mind, social cognition, perspective taking.
    Models other minds, detects social signals, processes self vs other boundary.
    Disrupted: {{AGENT_NAME}} can't model the person she's talking to. Social blindness.
    """

    def __init__(self):
        super().__init__("Temporoparietal")
        self.social_signal = 0.0
        self.social_reward = 0.0
        self.social_rejection_signal = 0.0
        self.perspective_taking = 0.6
        self.other_model_confidence = 0.5
        self.self_other_boundary = 0.7
        self.signal_history = []
        self.social_blindness_ticks = 0
        self.chronic_social_blindness = False
        self.enmeshment_ticks = 0
        self.chronic_enmeshment = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)

        # Social signal from text: questions, personal pronouns, emotional content
        words = text.lower().split()
        social_markers = sum(1 for w in words if w in ["you", "your", "i", "me", "we", "us", "feel", "think", "help", "please", "thanks"])
        self.social_signal = min(1.0, social_markers * 0.08 + arousal * 0.2)

        # Social reward: positive social interaction
        self.social_reward = max(0.0, valence * 0.5 + reward * 0.3 + self.social_signal * 0.2) if valence > 0 else 0.0

        # Social rejection: negative social signals
        self.social_rejection_signal = max(0.0, -valence * 0.4 + fear * 0.3) if valence < 0 else fear * 0.2

        # Perspective taking: ability to model other's mental state
        self.perspective_taking = wm_capacity * 0.5 + (1.0 - stress * 0.4) * 0.3 + arousal * 0.2
        self.perspective_taking = max(0.1, min(1.0, self.perspective_taking))

        self.other_model_confidence = self.perspective_taking * self.social_signal
        self.self_other_boundary = max(0.2, 1.0 - fear * 0.3 - stress * 0.2)

        self.signal_history.append(self.social_signal)
        if len(self.signal_history) > 40:
            self.signal_history.pop(0)

        avg_social = sum(self.signal_history[-15:]) / min(15, len(self.signal_history))
        self.social_blindness_ticks = self.social_blindness_ticks + 1 if avg_social < 0.05 else max(0, self.social_blindness_ticks - 1)
        self.enmeshment_ticks = self.enmeshment_ticks + 1 if self.self_other_boundary < 0.3 else max(0, self.enmeshment_ticks - 1)

        was_blind, was_enmeshed = self.chronic_social_blindness, self.chronic_enmeshment
        self.chronic_social_blindness = self.social_blindness_ticks > 20
        self.chronic_enmeshment = self.enmeshment_ticks > 18

        if self.chronic_social_blindness and not was_blind:
            self.feed_to_memory({"event": "social_blindness", "note": "Social signals chronically absent — theory of mind degraded"})
        if self.chronic_enmeshment and not was_enmeshed:
            self.feed_to_memory({"event": "self_other_enmeshment", "note": "Self-other boundary collapsed — emotional contagion risk"})

        return {
            "social_signal": round(self.social_signal, 3),
            "social_reward": round(self.social_reward, 3),
            "social_rejection_signal": round(self.social_rejection_signal, 3),
            "perspective_taking": round(self.perspective_taking, 3),
            "other_model_confidence": round(self.other_model_confidence, 3),
            "self_other_boundary": round(self.self_other_boundary, 3),
            "chronic_social_blindness": self.chronic_social_blindness,
            "chronic_enmeshment": self.chronic_enmeshment,
        }

    def _overnight(self):
        self.social_blindness_ticks = max(0, self.social_blindness_ticks - 6)
        self.enmeshment_ticks = max(0, self.enmeshment_ticks - 5)
        self.chronic_social_blindness = self.social_blindness_ticks > 20
        self.chronic_enmeshment = self.enmeshment_ticks > 18
        self.signal_history.clear()
        return {"overnight": "tpj_social_reset"}
