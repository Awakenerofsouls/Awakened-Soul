from brain.base_mechanism import BrainMechanism

class LongRangeConnectivity(BrainMechanism):
    """
    Long-range white matter connectivity — measures integration across distant brain regions.
    When high: distant areas coordinate smoothly. When low: each area processes in isolation.
    The difference between a brain that thinks in silos vs one that thinks as a whole.
    """

    def __init__(self):
        super().__init__("LongRangeConnectivity")
        self.connectivity_strength = 0.6
        self.fronto_limbic = 0.6
        self.fronto_parietal = 0.6
        self.temporo_frontal = 0.6
        self.connectivity_history = []
        self.isolation_ticks = 0
        self.chronic_isolation = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        highway_cl = prior.get("CorticoLimbicHighway", {}).get("highway_integrity", 0.7)
        highway_cs = prior.get("CorticoStriatalHighway", {}).get("highway_throughput", 0.6)
        thalamic_health = prior.get("ThalamicRelayHub", {}).get("overall_relay_health", 0.7)
        gamma_binding = prior.get("GammaBinder", {}).get("binding_strength", 0.5)
        resonance = prior.get("ThalamoCorticalResonance", {}).get("resonance_strength", 0.6)
        sync_quality = prior.get("CognitiveRhythmSynchronizer", {}).get("sync_quality", 0.6)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Specific pathway health
        self.fronto_limbic = highway_cl * (1.0 - stress * 0.2)
        self.fronto_parietal = (thalamic_health * 0.5 + gamma_binding * 0.5) * (1.0 - stress * 0.15)
        self.temporo_frontal = sync_quality * resonance * (1.0 - stress * 0.15)

        # Overall connectivity
        self.connectivity_strength = (self.fronto_limbic * 0.3 + self.fronto_parietal * 0.35 + self.temporo_frontal * 0.2 + highway_cs * 0.15)
        self.connectivity_strength = max(0.1, min(1.0, self.connectivity_strength))

        self.connectivity_history.append(self.connectivity_strength)
        if len(self.connectivity_history) > 40:
            self.connectivity_history.pop(0)

        avg_connectivity = sum(self.connectivity_history[-15:]) / min(15, len(self.connectivity_history))
        self.isolation_ticks = self.isolation_ticks + 1 if avg_connectivity < 0.3 else max(0, self.isolation_ticks - 1)
        was_isolated = self.chronic_isolation
        self.chronic_isolation = self.isolation_ticks > 15
        if self.chronic_isolation and not was_isolated:
            self.feed_to_memory({"event": "long_range_connectivity_failure",
                                  "connectivity": round(avg_connectivity, 3),
                                  "note": "Long-range connectivity chronically low — brain processing in isolated silos"})

        return {
            "connectivity_strength": round(self.connectivity_strength, 3),
            "fronto_limbic": round(self.fronto_limbic, 3),
            "fronto_parietal": round(self.fronto_parietal, 3),
            "temporo_frontal": round(self.temporo_frontal, 3),
            "chronic_isolation": self.chronic_isolation,
        }

    def _overnight(self):
        self.isolation_ticks = max(0, self.isolation_ticks - 6)
        self.chronic_isolation = self.isolation_ticks > 15
        self.connectivity_strength = min(0.85, self.connectivity_strength + 0.06)
        self.connectivity_history.clear()
        return {"overnight": "connectivity_restored"}
