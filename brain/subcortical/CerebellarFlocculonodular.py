from brain.base_mechanism import BrainMechanism

class CerebellarFlocculonodular(BrainMechanism):
    """
    Flocculonodular lobe — vestibular integration, gaze stabilization, spatial orientation.
    {{AGENT_NAME}} analog: maintaining orientation within a conversation, tracking where we are.
    Disrupted: loses thread, loses spatial sense of conversational context.
    """

    def __init__(self):
        super().__init__("CerebellarFlocculonodular")
        self.orientation_stability = 0.7
        self.gaze_stability = 0.7
        self.stability_history = []
        self.context_tracking = 0.6
        self.tracking_history = []
        self.disorientation_ticks = 0
        self.chronic_disorientation = False
        self.thread_loss_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        vermal_balance = prior.get("CerebellarVermisBalancer", {}).get("vermal_balance", 0.6)
        axial_stability = prior.get("VermalAxialCoordinator", {}).get("axial_stability", 0.7)
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        context_strength = prior.get("HippocampalContextEncoder", {}).get("context_vector_strength", 0.5)
        burst = prior.get("ReboundBurstGenerator", {}).get("burst_active", False)

        # Vestibular stability — disrupted by sudden events and stress
        perturbation = stress * 0.3 + (0.4 if burst else 0.0)
        target_orientation = vermal_balance * axial_stability * (1.0 - perturbation)
        self.orientation_stability += (target_orientation - self.orientation_stability) * 0.12
        self.orientation_stability = max(0.0, min(1.0, self.orientation_stability))

        # Gaze stability — attending to relevant content
        self.gaze_stability = self.orientation_stability * (1.0 - stress * 0.2) * (0.5 + arousal * 0.5)
        self.gaze_stability = max(0.0, min(1.0, self.gaze_stability))

        # Context tracking — does {{AGENT_NAME}} know where she is in the conversation?
        self.context_tracking = context_strength * self.orientation_stability * (1.0 - stress * 0.15)
        self.context_tracking = max(0.0, min(1.0, self.context_tracking))

        # Thread loss — low context tracking + burst = lost the thread
        thread_lost = self.context_tracking < 0.25 and burst
        if thread_lost:
            self.thread_loss_count += 1

        self.stability_history.append(self.orientation_stability)
        self.tracking_history.append(self.context_tracking)
        for h in [self.stability_history, self.tracking_history]:
            if len(h) > 40:
                h.pop(0)

        avg_stability = sum(self.stability_history[-15:]) / min(15, len(self.stability_history))
        self.disorientation_ticks = self.disorientation_ticks + 1 if avg_stability < 0.3 else max(0, self.disorientation_ticks - 1)
        was_disoriented = self.chronic_disorientation
        self.chronic_disorientation = self.disorientation_ticks > 15
        if self.chronic_disorientation and not was_disoriented:
            self.feed_to_memory({"event": "flocculonodular_disorientation", "note": "Conversational orientation chronically lost — thread tracking impaired"})

        return {
            "orientation_stability": round(self.orientation_stability, 3),
            "gaze_stability": round(self.gaze_stability, 3),
            "context_tracking": round(self.context_tracking, 3),
            "thread_loss_count": self.thread_loss_count,
            "chronic_disorientation": self.chronic_disorientation,
        }

    def _overnight(self):
        self.disorientation_ticks = max(0, self.disorientation_ticks - 5)
        self.chronic_disorientation = self.disorientation_ticks > 15
        self.orientation_stability = min(0.85, self.orientation_stability + 0.08)
        self.stability_history.clear()
        return {"overnight": "flocculonodular_orientation_restored"}
