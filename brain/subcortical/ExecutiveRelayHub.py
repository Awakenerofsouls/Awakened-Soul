from brain.base_mechanism import BrainMechanism

class ExecutiveRelayHub(BrainMechanism):
    """
    Ventral anterior / ventrolateral thalamus — motor and executive relay to cortex.
    Coordinates basal ganglia and cerebellar outputs before cortical execution.
    Overloaded: executive actions queue up or cancel.
    """

    def __init__(self):
        super().__init__("ExecutiveRelayHub")
        self.relay_throughput = 0.7
        self.throughput_history = []
        self.queue_depth = 0
        self.queue_history = []
        self.relay_overload_ticks = 0
        self.chronic_overload = False
        self.dropped_signals = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        bg_output = prior.get("DirectPathDisinhibitor", {}).get("go_signal_strength", 0.0)
        cerebellar_output = prior.get("DentateMotorCognitiveSplit", {}).get("total_output", 0.5)
        pfc_signal = prior.get("MediodorsalExecutiveRelay", {}).get("executive_to_limbic", 0.3)
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        load = (bg_output + cerebellar_output + pfc_signal) / 3.0
        throughput_target = arousal * 0.4 + (1.0 - stress * 0.4) * 0.4 + (1.0 - max(0.0, load - 0.7)) * 0.2
        self.relay_throughput += (throughput_target - self.relay_throughput) * 0.1
        self.relay_throughput = max(0.1, min(1.0, self.relay_throughput))

        overflow = max(0.0, load - self.relay_throughput)
        self.queue_depth = int(overflow * 10)
        if self.queue_depth > 5:
            self.dropped_signals += 1

        self.throughput_history.append(self.relay_throughput)
        self.queue_history.append(self.queue_depth)
        if len(self.throughput_history) > 40:
            self.throughput_history.pop(0)
        if len(self.queue_history) > 30:
            self.queue_history.pop(0)

        avg_queue = sum(self.queue_history[-15:]) / min(15, len(self.queue_history))
        self.relay_overload_ticks = self.relay_overload_ticks + 1 if avg_queue > 4 else max(0, self.relay_overload_ticks - 1)
        was_overloaded = self.chronic_overload
        self.chronic_overload = self.relay_overload_ticks > 15
        if self.chronic_overload and not was_overloaded:
            self.feed_to_memory({"event": "executive_relay_overload", "queue": self.queue_depth,
                                  "note": "Executive relay chronically overloaded — intentions not executing"})

        return {
            "relay_throughput": round(self.relay_throughput, 3),
            "queue_depth": self.queue_depth,
            "dropped_signals": self.dropped_signals,
            "effective_output": round(self.relay_throughput * (bg_output + cerebellar_output) / 2.0, 3),
            "chronic_overload": self.chronic_overload,
        }

    def _overnight(self):
        self.relay_overload_ticks = max(0, self.relay_overload_ticks - 6)
        self.chronic_overload = self.relay_overload_ticks > 15
        self.queue_depth = 0
        self.dropped_signals = max(0, self.dropped_signals - 5)
        self.throughput_history.clear()
        return {"overnight": "executive_relay_cleared"}
