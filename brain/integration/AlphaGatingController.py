from brain.base_mechanism import BrainMechanism

class AlphaGatingController(BrainMechanism):
    """
    Alpha rhythm gating — active suppression of irrelevant processing streams.
    Alpha is not idling — it's directed inhibition. What you're NOT attending to gets alpha.
    Chronic over-alpha: suppressing things that should be active. Under-alpha: can't filter.
    """

    def __init__(self):
        super().__init__("AlphaGatingController")
        self.alpha_suppression_strength = 0.3
        self.suppressed_streams = []
        self.active_streams = []
        self.suppression_history = []
        self.over_suppression_ticks = 0
        self.under_suppression_ticks = 0
        self.chronic_over = False
        self.chronic_under = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        alpha_power = prior.get("CognitiveRhythmSynchronizer", {}).get("alpha_power", 0.5)
        attention_spotlight = prior.get("ThalamicAttentionBroadcaster", {}).get("attention_spotlight", "balanced")
        reticular_suppression = prior.get("ThalamicReticularGate", {}).get("suppression_output", 0.3)
        task_engagement = prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6)
        dmn = prior.get("DefaultModeNetwork", {}).get("dmn_activity", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Alpha suppression: directed at non-attended streams
        self.alpha_suppression_strength = (alpha_power * 0.5 + reticular_suppression * 0.3 + task_engagement * 0.2) * (1.0 - stress * 0.15)
        self.alpha_suppression_strength = max(0.0, min(1.0, self.alpha_suppression_strength))

        # What's being suppressed: everything not in the spotlight
        all_streams = ["threat", "reward", "task", "social", "internal", "default_mode"]
        focused = attention_spotlight if attention_spotlight != "balanced" else "task"
        self.suppressed_streams = [s for s in all_streams if s != focused]
        self.active_streams = [focused]
        if dmn > 0.5 and focused == "task":
            # DMN leaking through alpha gate
            self.suppressed_streams = [s for s in self.suppressed_streams if s != "default_mode"]
            self.active_streams.append("default_mode")

        self.suppression_history.append(self.alpha_suppression_strength)
        if len(self.suppression_history) > 40:
            self.suppression_history.pop(0)

        avg_suppression = sum(self.suppression_history[-15:]) / min(15, len(self.suppression_history))
        self.over_suppression_ticks = self.over_suppression_ticks + 1 if avg_suppression > 0.8 else max(0, self.over_suppression_ticks - 1)
        self.under_suppression_ticks = self.under_suppression_ticks + 1 if avg_suppression < 0.1 else max(0, self.under_suppression_ticks - 1)

        was_over, was_under = self.chronic_over, self.chronic_under
        self.chronic_over = self.over_suppression_ticks > 18
        self.chronic_under = self.under_suppression_ticks > 18

        if self.chronic_over and not was_over:
            self.feed_to_memory({"event": "alpha_over_suppression",
                                  "note": "Alpha gating chronically over-strong — relevant streams being suppressed"})
        if self.chronic_under and not was_under:
            self.feed_to_memory({"event": "alpha_under_suppression",
                                  "note": "Alpha gating chronically weak — can't filter irrelevant processing"})

        return {
            "alpha_suppression_strength": round(self.alpha_suppression_strength, 3),
            "active_streams": self.active_streams,
            "suppressed_streams": self.suppressed_streams,
            "chronic_over": self.chronic_over,
            "chronic_under": self.chronic_under,
        }

    def _overnight(self):
        self.over_suppression_ticks = max(0, self.over_suppression_ticks - 5)
        self.under_suppression_ticks = max(0, self.under_suppression_ticks - 5)
        self.chronic_over = self.over_suppression_ticks > 18
        self.chronic_under = self.under_suppression_ticks > 18
        self.suppression_history.clear()
        return {"overnight": "alpha_gating_reset"}
