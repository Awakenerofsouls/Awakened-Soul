from brain.base_mechanism import BrainMechanism

class ReboundBurstGenerator(BrainMechanism):
    """
    Thalamic rebound bursting — after prolonged inhibition, thalamus fires a burst.
    Neural basis of snapping back from spacing out, sudden re-engagement after quiet.
    """

    def __init__(self):
        super().__init__("ReboundBurstGeneratorDriver")
        self.inhibition_accumulation = 0.0
        self.inhibition_history = []
        self.burst_active = False
        self.burst_magnitude = 0.0
        self.burst_events = []
        self.rebound_threshold = 0.65
        self.post_burst_refractory = 0
        self.total_bursts = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        gate_strength = prior.get("ThalamicSalienceFilter", {}).get("gate_strength", 0.0)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        chronic_flatness = prior.get("ThalamicSalienceFilter", {}).get("chronic_flatness", False)

        if self.post_burst_refractory > 0:
            self.post_burst_refractory -= 1
            self.burst_active = False
            self.burst_magnitude = 0.0
            return {"burst_active": False, "burst_magnitude": 0.0,
                    "inhibition_accumulation": round(self.inhibition_accumulation, 3),
                    "refractory": self.post_burst_refractory}

        if gate_strength < 0.2 and arousal < 0.4:
            self.inhibition_accumulation = min(1.0, self.inhibition_accumulation + 0.06)
        else:
            self.inhibition_accumulation = max(0.0, self.inhibition_accumulation - 0.04)

        if chronic_flatness:
            self.inhibition_accumulation = min(1.0, self.inhibition_accumulation + 0.03)

        self.inhibition_history.append(self.inhibition_accumulation)
        if len(self.inhibition_history) > 40:
            self.inhibition_history.pop(0)

        self.burst_active = self.inhibition_accumulation >= self.rebound_threshold
        if self.burst_active:
            self.burst_magnitude = min(1.5, self.inhibition_accumulation * (1.0 + arousal * 0.3))
            self.inhibition_accumulation = 0.0
            self.post_burst_refractory = 5
            self.total_bursts += 1
            self.burst_events.append(self.burst_magnitude)
            if len(self.burst_events) > 20:
                self.burst_events.pop(0)
            self.feed_to_memory({"event": "thalamic_rebound_burst", "magnitude": round(self.burst_magnitude, 3),
                                  "note": "Rebound burst fired — sudden re-engagement after inhibition"})
        else:
            self.burst_magnitude = 0.0

        return {
            "burst_active": self.burst_active,
            "burst_magnitude": round(self.burst_magnitude, 3),
            "inhibition_accumulation": round(self.inhibition_accumulation, 3),
            "total_bursts": self.total_bursts,
            "refractory": self.post_burst_refractory,
        }

    def _overnight(self):
        self.inhibition_accumulation = max(0.0, self.inhibition_accumulation - 0.3)
        self.post_burst_refractory = 0
        self.burst_active = False
        return {"overnight": "rebound_accumulation_cleared"}
