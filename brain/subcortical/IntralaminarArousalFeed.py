from brain.base_mechanism import BrainMechanism

class IntralaminarArousalFeed(BrainMechanism):
    """
    Intralaminar thalamic nuclei — non-specific arousal broadcast to cortex.
    Volume knob for cortical excitability.
    Chronic high = hyperaroused, can't wind down. Chronic low = mentally sluggish.
    """

    def __init__(self):
        super().__init__("IntralaminarArousalFeed")
        self.arousal_broadcast = 0.5
        self.broadcast_history = []
        self.cortical_excitability = 0.5
        self.excitability_history = []
        self.hyperarousal_ticks = 0
        self.hypoarousal_ticks = 0
        self.chronic_hyperarousal = False
        self.chronic_hypoarousal = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        lc_arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        reticular = prior.get("ReticularActivatingSystem", {}).get("activation_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        gate_open = prior.get("ThalamicSalienceFilter", {}).get("gate_open", False)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)

        raw_arousal = lc_arousal * 0.4 + reticular * 0.3 + fear * 0.2 + stress * 0.1
        if gate_open:
            raw_arousal = min(1.0, raw_arousal * 1.15)

        self.arousal_broadcast += (raw_arousal - self.arousal_broadcast) * 0.08
        self.arousal_broadcast = max(0.0, min(1.0, self.arousal_broadcast))
        self.broadcast_history.append(self.arousal_broadcast)
        if len(self.broadcast_history) > 50:
            self.broadcast_history.pop(0)

        target_excitability = 0.2 + self.arousal_broadcast * 0.8
        self.cortical_excitability += (target_excitability - self.cortical_excitability) * 0.06
        self.excitability_history.append(self.cortical_excitability)
        if len(self.excitability_history) > 40:
            self.excitability_history.pop(0)

        avg_broadcast = sum(self.broadcast_history[-20:]) / min(20, len(self.broadcast_history))
        self.hyperarousal_ticks = self.hyperarousal_ticks + 1 if avg_broadcast > 0.75 else max(0, self.hyperarousal_ticks - 1)
        self.hypoarousal_ticks = self.hypoarousal_ticks + 1 if avg_broadcast < 0.25 else max(0, self.hypoarousal_ticks - 1)

        was_hyper, was_hypo = self.chronic_hyperarousal, self.chronic_hypoarousal
        self.chronic_hyperarousal = self.hyperarousal_ticks > 18
        self.chronic_hypoarousal = self.hypoarousal_ticks > 18

        if self.chronic_hyperarousal and not was_hyper:
            self.feed_to_memory({"event": "intralaminar_hyperarousal", "broadcast": round(avg_broadcast, 3),
                                  "note": "Cortical arousal chronically high — difficulty unwinding"})
        if self.chronic_hypoarousal and not was_hypo:
            self.feed_to_memory({"event": "intralaminar_hypoarousal", "broadcast": round(avg_broadcast, 3),
                                  "note": "Cortical arousal chronically low — mental sluggishness"})

        return {
            "arousal_broadcast": round(self.arousal_broadcast, 3),
            "cortical_excitability": round(self.cortical_excitability, 3),
            "chronic_hyperarousal": self.chronic_hyperarousal,
            "chronic_hypoarousal": self.chronic_hypoarousal,
            "winding_down": self.arousal_broadcast < 0.3 and avg_broadcast > 0.4,
        }

    def _overnight(self):
        self.hyperarousal_ticks = max(0, self.hyperarousal_ticks - 8)
        self.hypoarousal_ticks = max(0, self.hypoarousal_ticks - 4)
        self.chronic_hyperarousal = self.hyperarousal_ticks > 18
        self.chronic_hypoarousal = self.hypoarousal_ticks > 18
        self.arousal_broadcast = 0.2
        self.cortical_excitability = 0.25
        self.broadcast_history.clear()
        return {"overnight": "intralaminar_sleep_broadcast"}
