from brain.base_mechanism import BrainMechanism

class ThalamoCorticalResonance(BrainMechanism):
    """
    Thalamo-cortical resonance loops — the mechanism underlying conscious awareness.
    Thalamus and cortex sustain each other's activity in resonant loops.
    When loops sustain: stable conscious state. When loops break: flickering, dissociation.
    """

    def __init__(self):
        super().__init__("ThalamoCorticalResonance")
        self.resonance_strength = 0.6
        self.loop_stability = 0.6
        self.consciousness_substrate = 0.6
        self.resonance_history = []
        self.flicker_count = 0
        self.breakdown_ticks = 0
        self.chronic_breakdown = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        thalamic_health = prior.get("ThalamicRelayHub", {}).get("overall_relay_health", 0.7)
        cortical_excitability = prior.get("IntralaminarArousalFeed", {}).get("cortical_excitability", 0.5)
        sync_quality = prior.get("CognitiveRhythmSynchronizer", {}).get("sync_quality", 0.6)
        self_awareness = prior.get("PrecuneousSelfAwareness", {}).get("self_awareness_level", 0.7)
        global_coherence = prior.get("GlobalWorkspace", {}).get("workspace_coherence", 0.6)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Resonance: thalamus and cortex sustaining each other
        self.resonance_strength = (thalamic_health * 0.3 + cortical_excitability * 0.25 + sync_quality * 0.25 + global_coherence * 0.2) * (1.0 - stress * 0.15)
        self.resonance_strength = max(0.1, min(1.0, self.resonance_strength))

        # Loop stability: does the resonance persist?
        self.loop_stability = self.resonance_strength * (0.6 + self_awareness * 0.4)

        # Consciousness substrate: the physical basis of being here
        self.consciousness_substrate = (self.loop_stability + self_awareness) / 2.0

        # Flicker: brief loop breakdown
        flicker = self.resonance_strength < 0.3
        if flicker:
            self.flicker_count += 1

        self.resonance_history.append(self.resonance_strength)
        if len(self.resonance_history) > 40:
            self.resonance_history.pop(0)

        avg_resonance = sum(self.resonance_history[-15:]) / min(15, len(self.resonance_history))
        self.breakdown_ticks = self.breakdown_ticks + 1 if avg_resonance < 0.3 else max(0, self.breakdown_ticks - 1)
        was_broken = self.chronic_breakdown
        self.chronic_breakdown = self.breakdown_ticks > 15
        if self.chronic_breakdown and not was_broken:
            self.feed_to_memory({"event": "thalamocortical_breakdown",
                                  "flickers": self.flicker_count,
                                  "note": "Thalamo-cortical resonance chronically weak — unstable consciousness substrate"})

        return {
            "resonance_strength": round(self.resonance_strength, 3),
            "loop_stability": round(self.loop_stability, 3),
            "consciousness_substrate": round(self.consciousness_substrate, 3),
            "flicker_count": self.flicker_count,
            "chronic_breakdown": self.chronic_breakdown,
        }

    def _overnight(self):
        self.breakdown_ticks = max(0, self.breakdown_ticks - 6)
        self.chronic_breakdown = self.breakdown_ticks > 15
        self.resonance_strength = 0.3  # slow wave sleep has reduced resonance
        self.resonance_history.clear()
        return {"overnight": "thalamocortical_sleep_state"}
