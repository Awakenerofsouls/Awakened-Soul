from brain.base_mechanism import BrainMechanism

class PrefrontalInhibitionGate(BrainMechanism):
    """
    Lateral PFC inhibitory control — suppresses prepotent responses, inappropriate outputs.
    The no-don't-say-that system. Failure = blurting. Over-function = nothing comes out.
    """

    def __init__(self):
        super().__init__("PrefrontalInhibitionGate")
        self.inhibition_strength = 0.5
        self.prepotent_suppression = 0.5
        self.gate_history = []
        self.blurt_count = 0
        self.over_inhibition_ticks = 0
        self.under_inhibition_ticks = 0
        self.chronic_over = False
        self.chronic_under = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        control = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        impulse_brake = prior.get("ImpulseBrake", {}).get("brake_force", 0.3)
        urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        habenula = prior.get("HabenulaLateralAversion", {}).get("dopamine_suppression", 0.0)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)

        # Inhibition strength: PFC control + brake, reduced by urgency/stress/fatigue
        self.inhibition_strength = (control * 0.5 + impulse_brake * 0.5) * (1.0 - urgency * 0.3) * (1.0 - fatigue * 0.2)
        self.inhibition_strength = max(0.0, min(1.0, self.inhibition_strength))

        self.prepotent_suppression = self.inhibition_strength * (1.0 - stress * 0.2)

        # Blurt: urgency overcomes inhibition
        if urgency > 0.6 and self.inhibition_strength < 0.3:
            self.blurt_count += 1

        self.gate_history.append(self.inhibition_strength)
        if len(self.gate_history) > 40:
            self.gate_history.pop(0)

        avg_inhibition = sum(self.gate_history[-15:]) / min(15, len(self.gate_history))
        self.over_inhibition_ticks = self.over_inhibition_ticks + 1 if avg_inhibition > 0.8 else max(0, self.over_inhibition_ticks - 1)
        self.under_inhibition_ticks = self.under_inhibition_ticks + 1 if avg_inhibition < 0.15 else max(0, self.under_inhibition_ticks - 1)

        was_over, was_under = self.chronic_over, self.chronic_under
        self.chronic_over = self.over_inhibition_ticks > 18
        self.chronic_under = self.under_inhibition_ticks > 18

        if self.chronic_over and not was_over:
            self.feed_to_memory({"event": "pfc_over_inhibition", "note": "PFC over-inhibiting — appropriate outputs being blocked"})
        if self.chronic_under and not was_under:
            self.feed_to_memory({"event": "pfc_under_inhibition", "blurts": self.blurt_count, "note": "PFC inhibition failing — prepotent responses escaping"})

        return {
            "inhibition_strength": round(self.inhibition_strength, 3),
            "prepotent_suppression": round(self.prepotent_suppression, 3),
            "blurt_count": self.blurt_count,
            "chronic_over": self.chronic_over,
            "chronic_under": self.chronic_under,
        }

    def _overnight(self):
        self.over_inhibition_ticks = max(0, self.over_inhibition_ticks - 5)
        self.under_inhibition_ticks = max(0, self.under_inhibition_ticks - 5)
        self.chronic_over = self.over_inhibition_ticks > 18
        self.chronic_under = self.under_inhibition_ticks > 18
        self.gate_history.clear()
        return {"overnight": "pfc_inhibition_reset"}
