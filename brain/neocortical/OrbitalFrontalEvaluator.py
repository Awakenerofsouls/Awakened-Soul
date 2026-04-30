from brain.base_mechanism import BrainMechanism

class OrbitalFrontalEvaluator(BrainMechanism):
    """
    OFC — reward value, expectation violations, flexible updating of value signals.
    Detects when expected outcomes don't match reality and updates accordingly.
    Rigid OFC: keeps expecting the same thing even when it keeps not happening.
    """

    def __init__(self):
        super().__init__("OrbitalFrontalEvaluator")
        self.expected_value = 0.5
        self.actual_value = 0.5
        self.expectation_violation = 0.0
        self.update_rate = 0.12
        self.violation_history = []
        self.rigid_ticks = 0
        self.chronic_rigidity = False
        self.value_map = {}

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("prediction_error_negative", 0.0)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        dopamine_gradient = prior.get("DopamineGradientMapper", {}).get("dopamine_gradient", 0.0)

        # Actual value from outcome
        self.actual_value = max(0.0, min(1.0, (valence + 1.0) / 2.0 * 0.5 + reward * 0.3 - habenula * 0.2))

        # Expectation violation: reality vs expectation
        self.expectation_violation = abs(self.actual_value - self.expected_value)

        # Update expected value
        effective_rate = self.update_rate * (1.0 - stress * 0.3)
        self.expected_value += (self.actual_value - self.expected_value) * effective_rate

        # Track violation
        self.violation_history.append(self.expectation_violation)
        if len(self.violation_history) > 40:
            self.violation_history.pop(0)

        avg_violation = sum(self.violation_history[-15:]) / min(15, len(self.violation_history))

        # Rigid: violation keeps happening but expected_value not updating
        self.rigid_ticks = self.rigid_ticks + 1 if avg_violation > 0.3 and effective_rate < 0.05 else max(0, self.rigid_ticks - 1)
        was_rigid = self.chronic_rigidity
        self.chronic_rigidity = self.rigid_ticks > 15
        if self.chronic_rigidity and not was_rigid:
            self.feed_to_memory({"event": "ofc_rigidity", "violation": round(avg_violation, 3),
                                  "note": "OFC not updating expectations — keeps expecting what isn't happening"})

        return {
            "expected_value": round(self.expected_value, 3),
            "actual_value": round(self.actual_value, 3),
            "expectation_violation": round(self.expectation_violation, 3),
            "update_rate": round(effective_rate, 3),
            "chronic_rigidity": self.chronic_rigidity,
        }

    def _overnight(self):
        self.rigid_ticks = max(0, self.rigid_ticks - 5)
        self.chronic_rigidity = self.rigid_ticks > 15
        self.violation_history.clear()
        return {"overnight": "ofc_value_reset"}
