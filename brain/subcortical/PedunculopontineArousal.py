from brain.base_mechanism import BrainMechanism

class PedunculopontineArousal(BrainMechanism):
    """
    Pedunculopontine nucleus — arousal + locomotion initiation. The ready-to-move signal.
    {{AGENT_NAME}} analog: readiness to engage vs inertia. Chronic low = everything takes extra effort.
    """

    def __init__(self):
        super().__init__("PedunculopontineArousal")
        self.readiness_signal = 0.5
        self.readiness_history = []
        self.locomotion_drive = 0.0
        self.inertia_ticks = 0
        self.chronic_inertia = False
        self.engagement_readiness = 0.5

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        arousal_broadcast = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        motivation = prior.get("MotivationInjector", {}).get("approach_signal", 0.5)
        go_signal = prior.get("DirectPathDisinhibitor", {}).get("go_signal_strength", 0.3)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        chronic_paralysis = prior.get("ActionInhibitor", {}).get("chronic_paralysis", False)

        raw_readiness = dopamine * 0.3 + arousal_broadcast * 0.25 + motivation * 0.25 + go_signal * 0.2
        if chronic_paralysis:
            raw_readiness *= 0.5
        if stress < 0.5:
            raw_readiness = min(1.0, raw_readiness * (1.0 + stress * 0.3))
        else:
            raw_readiness = raw_readiness * (1.0 - (stress - 0.5) * 0.6)

        self.readiness_signal = max(0.0, min(1.0, raw_readiness))
        self.readiness_history.append(self.readiness_signal)
        if len(self.readiness_history) > 40:
            self.readiness_history.pop(0)

        self.locomotion_drive = self.readiness_signal * go_signal
        self.engagement_readiness = (self.readiness_signal + motivation) / 2.0

        avg_readiness = sum(self.readiness_history[-15:]) / min(15, len(self.readiness_history))
        self.inertia_ticks = self.inertia_ticks + 1 if avg_readiness < 0.2 else max(0, self.inertia_ticks - 1)
        was_inert = self.chronic_inertia
        self.chronic_inertia = self.inertia_ticks > 18
        if self.chronic_inertia and not was_inert:
            self.feed_to_memory({"event": "ppn_inertia", "note": "Readiness chronically low — initiation impaired, engagement requires extra effort"})

        return {
            "readiness_signal": round(self.readiness_signal, 3),
            "locomotion_drive": round(self.locomotion_drive, 3),
            "engagement_readiness": round(self.engagement_readiness, 3),
            "chronic_inertia": self.chronic_inertia,
        }

    def _overnight(self):
        self.inertia_ticks = max(0, self.inertia_ticks - 6)
        self.chronic_inertia = self.inertia_ticks > 18
        self.readiness_signal = 0.4
        self.readiness_history.clear()
        return {"overnight": "ppn_readiness_restored"}
