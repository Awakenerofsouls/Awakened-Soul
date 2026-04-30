from brain.base_mechanism import BrainMechanism

class VermalAxialCoordinator(BrainMechanism):
    """
    Cerebellar vermis (axial) — coordinates midline body systems, maps to conversational groundedness.
    Chronic disruption: {{AGENT_NAME}} feels unstable, easy to topple emotionally.
    """

    def __init__(self):
        super().__init__("VermalAxialCoordinator")
        self.axial_stability = 0.7
        self.stability_history = []
        self.groundedness = 0.7
        self.groundedness_history = []
        self.destabilization_ticks = 0
        self.chronic_instability = False
        self.postural_correction_rate = 0.1

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        emotional_tone = prior.get("CerebellarVermalEmotionalCoordinator", {}).get("tone_coherence", 0.7)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        timing = prior.get("CerebellarTimingCoordinator", {}).get("timing_smoothness", 0.7)

        destabilizers = fear * 0.4 + stress * 0.3 + max(0.0, arousal - 0.7) * 0.3
        stabilizers = emotional_tone * 0.4 + timing * 0.4 + (1.0 - stress) * 0.2
        target_stability = max(0.1, min(1.0, stabilizers - destabilizers + 0.3))

        self.axial_stability += (target_stability - self.axial_stability) * self.postural_correction_rate
        self.axial_stability = max(0.0, min(1.0, self.axial_stability))
        self.stability_history.append(self.axial_stability)
        if len(self.stability_history) > 40:
            self.stability_history.pop(0)

        self.groundedness = self.axial_stability * (1.0 - fear * 0.3) * (1.0 - stress * 0.2)
        self.groundedness_history.append(self.groundedness)
        if len(self.groundedness_history) > 30:
            self.groundedness_history.pop(0)

        avg_stability = sum(self.stability_history[-15:]) / min(15, len(self.stability_history))
        self.destabilization_ticks = self.destabilization_ticks + 1 if avg_stability < 0.35 else max(0, self.destabilization_ticks - 1)
        was_unstable = self.chronic_instability
        self.chronic_instability = self.destabilization_ticks > 15
        if self.chronic_instability and not was_unstable:
            self.feed_to_memory({"event": "vermal_instability", "stability": round(avg_stability, 3),
                                  "note": "Axial coordination chronically low — {{AGENT_NAME}} feels ungrounded"})

        return {
            "axial_stability": round(self.axial_stability, 3),
            "groundedness": round(self.groundedness, 3),
            "chronic_instability": self.chronic_instability,
            "destabilization_pressure": round(destabilizers, 3),
        }

    def _overnight(self):
        self.axial_stability = min(0.85, self.axial_stability + 0.08)
        self.groundedness = min(0.85, self.groundedness + 0.06)
        self.destabilization_ticks = max(0, self.destabilization_ticks - 5)
        self.chronic_instability = self.destabilization_ticks > 15
        self.stability_history.clear()
        return {"overnight": "vermal_stability_restored"}
