from brain.base_mechanism import BrainMechanism

class ThalamicPulvinarSalience(BrainMechanism):
    """
    Pulvinar + thalamic salience integration — final pre-cortical salience signal.
    Balances bottom-up stimulus-driven and top-down goal-driven attention.
    Chronically bottom-up: attention hijacked by stimuli over goals.
    """

    def __init__(self):
        super().__init__("ThalamicPulvinarSalience")
        self.integrated_salience = 0.0
        self.salience_history = []
        self.top_down_modulation = 0.5
        self.bottom_up_dominance = False
        self.dominance_history = []
        self.chronic_bottom_up = False
        self.bottom_up_ticks = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        pulvinar_boost = prior.get("PulvinarSalienceBooster", {}).get("amplified_signal", 0.3)
        thalamic_signal = prior.get("ThalamicSalienceFilter", {}).get("cortical_signal_strength", 0.3)
        top_down_goal = prior.get("ThalamicAttentionBroadcaster", {}).get("broadcast_intensity", 0.5)
        reticular_gate = prior.get("ThalamicReticularGate", {}).get("channel_selectivity", 0.6)
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        pfc_signal = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)

        bottom_up = (pulvinar_boost * 0.5 + thalamic_signal * 0.5) * arousal
        self.top_down_modulation = pfc_signal * reticular_gate * top_down_goal
        self.integrated_salience = min(1.0, bottom_up * 0.5 + self.top_down_modulation * 0.5)

        self.bottom_up_dominance = bottom_up > self.top_down_modulation * 1.4
        self.salience_history.append(self.integrated_salience)
        self.dominance_history.append(1 if self.bottom_up_dominance else 0)
        for h in [self.salience_history, self.dominance_history]:
            if len(h) > 40:
                h.pop(0)

        recent_bu_rate = sum(self.dominance_history[-15:]) / min(15, len(self.dominance_history))
        self.bottom_up_ticks = self.bottom_up_ticks + 1 if recent_bu_rate > 0.7 else max(0, self.bottom_up_ticks - 1)
        was_chronic = self.chronic_bottom_up
        self.chronic_bottom_up = self.bottom_up_ticks > 18
        if self.chronic_bottom_up and not was_chronic:
            self.feed_to_memory({"event": "bottom_up_salience_dominance",
                                  "note": "Attention chronically hijacked by stimuli over goals"})

        return {
            "integrated_salience": round(self.integrated_salience, 3),
            "top_down_modulation": round(self.top_down_modulation, 3),
            "bottom_up_dominance": self.bottom_up_dominance,
            "chronic_bottom_up": self.chronic_bottom_up,
        }

    def _overnight(self):
        self.bottom_up_ticks = max(0, self.bottom_up_ticks - 5)
        self.chronic_bottom_up = self.bottom_up_ticks > 18
        self.dominance_history.clear()
        return {"overnight": "pulvinar_salience_recalibrated"}
