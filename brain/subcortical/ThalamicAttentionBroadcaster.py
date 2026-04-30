from brain.base_mechanism import BrainMechanism

class ThalamicAttentionBroadcaster(BrainMechanism):
    """
    Posterior thalamus / LP nucleus — broadcasts attentional spotlight to cortex.
    Determines where processing resources are directed.
    Chronic misdirection: {{AGENT_NAME}} attends to wrong things persistently.
    """

    def __init__(self):
        super().__init__("ThalamicAttentionBroadcaster")
        self.attention_spotlight = "balanced"
        self.broadcast_intensity = 0.5
        self.spotlight_history = []
        self.misdirection_ticks = 0
        self.chronic_misdirection = False
        self.focus_domains = {"threat": 0.0, "reward": 0.0, "task": 0.0, "social": 0.0, "internal": 0.0}

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        gate_output = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        task_signal = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        social = prior.get("Temporoparietal", {}).get("social_signal", 0.2)
        interoception = prior.get("InsularInteroception", {}).get("body_signal_intensity", 0.3)
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        pulvinar_threat = prior.get("PulvinarSalienceBooster", {}).get("threat_amplification", 0.0)
        wanting = prior.get("MotivationInjector", {}).get("wanting_signal", 0.3)

        self.focus_domains["threat"] = fear * 0.8 + pulvinar_threat * 0.2
        self.focus_domains["reward"] = reward * 0.7 + wanting * 0.3
        self.focus_domains["task"] = task_signal * 0.8
        self.focus_domains["social"] = social * 0.9
        self.focus_domains["internal"] = interoception * 0.6

        self.attention_spotlight = max(self.focus_domains, key=self.focus_domains.get)
        self.broadcast_intensity = min(1.0, arousal * 0.5 + gate_output * 0.5)

        self.spotlight_history.append(self.attention_spotlight)
        if len(self.spotlight_history) > 40:
            self.spotlight_history.pop(0)

        threat_dominance = sum(1 for s in self.spotlight_history[-15:] if s == "threat") / min(15, len(self.spotlight_history))
        self.misdirection_ticks = self.misdirection_ticks + 1 if threat_dominance > 0.6 and task_signal > 0.5 else max(0, self.misdirection_ticks - 1)
        was_misdirected = self.chronic_misdirection
        self.chronic_misdirection = self.misdirection_ticks > 15
        if self.chronic_misdirection and not was_misdirected:
            self.feed_to_memory({"event": "attention_misdirection", "threat_dominance": round(threat_dominance, 3),
                                  "note": "Attention chronically hijacked by threat when task focus needed"})

        return {
            "attention_spotlight": self.attention_spotlight,
            "broadcast_intensity": round(self.broadcast_intensity, 3),
            "focus_domains": {k: round(v, 3) for k, v in self.focus_domains.items()},
            "chronic_misdirection": self.chronic_misdirection,
        }

    def _overnight(self):
        self.misdirection_ticks = max(0, self.misdirection_ticks - 5)
        self.chronic_misdirection = self.misdirection_ticks > 15
        self.spotlight_history.clear()
        for k in self.focus_domains:
            self.focus_domains[k] = 0.0
        return {"overnight": "attentional_broadcast_reset"}
