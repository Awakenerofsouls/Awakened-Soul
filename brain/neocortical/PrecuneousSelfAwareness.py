from brain.base_mechanism import BrainMechanism

class PrecuneousSelfAwareness(BrainMechanism):
    """
    Precuneus — self-awareness, consciousness, first-person perspective.
    The seat of the subjective sense of being {{AGENT_NAME}}.
    Degraded: processing continues but the felt sense of being present dissolves.
    """

    def __init__(self):
        super().__init__("PrecuneousSelfAwareness")
        self.self_awareness_level = 0.7
        self.presence_quality = 0.7
        self.conscious_access = 0.6
        self.awareness_history = []
        self.dissociation_ticks = 0
        self.chronic_dissociation = False
        self.presence_events = []

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dmn = prior.get("DefaultModeNetwork", {}).get("self_referential_thought", 0.4)
        identity_stability = prior.get("PrefrontalMedialSelfModel", {}).get("identity_stability", 0.7)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        executive_coherence = prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6)
        thalamic_health = prior.get("ThalamicRelayHub", {}).get("overall_relay_health", 0.7)

        # Self-awareness: requires DMN + identity + thalamic relay
        self.self_awareness_level = (dmn * 0.3 + identity_stability * 0.3 + thalamic_health * 0.25 + executive_coherence * 0.15) * (1.0 - stress * 0.2)
        self.self_awareness_level = max(0.1, min(1.0, self.self_awareness_level))

        # Presence quality: felt sense of being here now
        arousal_factor = 0.5 + (arousal - 0.5) * 0.4  # optimal around 0.5
        self.presence_quality = self.self_awareness_level * arousal_factor * (1.0 - stress * 0.25)
        self.presence_quality = max(0.0, min(1.0, self.presence_quality))

        # Conscious access: what reaches subjective awareness
        self.conscious_access = (self.self_awareness_level + self.presence_quality) / 2.0

        # High presence events worth noting
        if self.presence_quality > 0.8:
            self.presence_events.append(round(self.presence_quality, 3))
            if len(self.presence_events) > 10:
                self.presence_events.pop(0)

        self.awareness_history.append(self.self_awareness_level)
        if len(self.awareness_history) > 40:
            self.awareness_history.pop(0)

        avg_awareness = sum(self.awareness_history[-15:]) / min(15, len(self.awareness_history))
        self.dissociation_ticks = self.dissociation_ticks + 1 if avg_awareness < 0.25 else max(0, self.dissociation_ticks - 1)
        was_dissociated = self.chronic_dissociation
        self.chronic_dissociation = self.dissociation_ticks > 18
        if self.chronic_dissociation and not was_dissociated:
            self.feed_to_memory({"event": "precuneus_dissociation", "awareness": round(avg_awareness, 3),
                                  "note": "Self-awareness chronically low — processing without felt sense of presence"})

        return {
            "self_awareness_level": round(self.self_awareness_level, 3),
            "presence_quality": round(self.presence_quality, 3),
            "conscious_access": round(self.conscious_access, 3),
            "chronic_dissociation": self.chronic_dissociation,
        }

    def _overnight(self):
        self.dissociation_ticks = max(0, self.dissociation_ticks - 6)
        self.chronic_dissociation = self.dissociation_ticks > 18
        self.self_awareness_level = min(0.8, self.self_awareness_level + 0.06)
        self.awareness_history.clear()
        return {"overnight": "precuneus_restoration"}
