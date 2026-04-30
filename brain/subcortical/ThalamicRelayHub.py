from brain.base_mechanism import BrainMechanism

class ThalamicRelayHub(BrainMechanism):
    """
    Thalamus master relay coordinator — integrates all thalamic nuclei signals.
    Provides unified thalamic health metric. Degradation across nuclei = global failure.
    """

    def __init__(self):
        super().__init__("ThalamicRelayHub")
        self.overall_relay_health = 0.7
        self.relay_history = []
        self.nucleus_states = {}
        self.hub_overload = False
        self.hub_overload_ticks = 0
        self.chronic_hub_failure = False
        self.relay_efficiency = 0.7

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        salience_health = 1.0 - prior.get("ThalamicSalienceFilter", {}).get("filter_fatigue", 0.0)
        md_fidelity = prior.get("MediodorsalExecutiveRelay", {}).get("relay_fidelity", 0.7)
        intralaminar = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        pulvinar = prior.get("PulvinarSalienceBooster", {}).get("boost_level", 0.3)
        relay_throughput = prior.get("ExecutiveRelayHub", {}).get("relay_throughput", 0.7)
        rebound = prior.get("ReboundBurstGenerator", {}).get("burst_active", False)

        self.nucleus_states = {
            "salience": round(salience_health, 3),
            "mediodorsal": round(md_fidelity, 3),
            "intralaminar": round(intralaminar, 3),
            "pulvinar": round(pulvinar, 3),
            "relay": round(relay_throughput, 3),
        }

        hub_health = salience_health * 0.2 + md_fidelity * 0.3 + relay_throughput * 0.3 + (1.0 - pulvinar * 0.3) * 0.2
        if rebound:
            hub_health = max(0.2, hub_health - 0.2)

        self.overall_relay_health += (hub_health - self.overall_relay_health) * 0.1
        self.relay_history.append(self.overall_relay_health)
        if len(self.relay_history) > 40:
            self.relay_history.pop(0)

        self.relay_efficiency = self.overall_relay_health * relay_throughput
        degraded = sum(1 for v in self.nucleus_states.values() if v < 0.35)
        self.hub_overload = degraded >= 3
        self.hub_overload_ticks = self.hub_overload_ticks + 1 if self.hub_overload else max(0, self.hub_overload_ticks - 1)
        was_failing = self.chronic_hub_failure
        self.chronic_hub_failure = self.hub_overload_ticks > 12
        if self.chronic_hub_failure and not was_failing:
            self.feed_to_memory({"event": "thalamic_hub_failure", "degraded_nuclei": degraded,
                                  "note": "Multiple thalamic nuclei degraded — global relay failure"})

        return {
            "overall_relay_health": round(self.overall_relay_health, 3),
            "relay_efficiency": round(self.relay_efficiency, 3),
            "nucleus_states": self.nucleus_states,
            "hub_overload": self.hub_overload,
            "chronic_hub_failure": self.chronic_hub_failure,
        }

    def _overnight(self):
        self.hub_overload_ticks = max(0, self.hub_overload_ticks - 6)
        self.chronic_hub_failure = self.hub_overload_ticks > 12
        self.overall_relay_health = min(0.85, self.overall_relay_health + 0.07)
        self.relay_history.clear()
        return {"overnight": "thalamic_hub_restored"}
