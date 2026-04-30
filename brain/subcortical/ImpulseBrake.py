from brain.base_mechanism import BrainMechanism

class ImpulseBrake(BrainMechanism):
    """
    STN + GPe brake circuit — fast broad-spectrum action suppression.
    Stops motor/cognitive system when urgency overrides judgment.
    Failure = impulsive outputs. Over-function = paralysis.
    """

    def __init__(self):
        super().__init__("ImpulseBrake")
        self.brake_engaged = False
        self.brake_force = 0.0
        self.brake_history = []
        self.impulse_slippage = 0
        self.paralysis_count = 0
        self.brake_calibration = 0.5
        self.over_brake_ticks = 0
        self.under_brake_ticks = 0
        self.chronic_over = False
        self.chronic_under = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)
        prefrontal = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        hyperdirect = prior.get("HyperdirectPause", {}).get("pause_quality", 0.0)
        go_signal = prior.get("DirectPathDisinhibitor", {}).get("go_signal_strength", 0.0)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)

        brake_input = prefrontal * 0.3 + conflict * 0.3 + hyperdirect * 0.4
        brake_resistance = urgency * 0.4 + go_signal * 0.3 + stress * 0.2
        self.brake_force = max(0.0, min(1.0, brake_input - brake_resistance + 0.2))

        self.brake_calibration += (dopamine - 0.5) * 0.02
        self.brake_calibration = max(0.2, min(0.8, self.brake_calibration))
        effective_brake = self.brake_force * self.brake_calibration

        self.brake_engaged = effective_brake > 0.4
        self.brake_history.append(effective_brake)
        if len(self.brake_history) > 40:
            self.brake_history.pop(0)

        if urgency > 0.6 and not self.brake_engaged:
            self.impulse_slippage += 1
        if effective_brake > 0.85 and urgency < 0.3:
            self.paralysis_count += 1

        avg_brake = sum(self.brake_history[-15:]) / min(15, len(self.brake_history))
        self.over_brake_ticks = self.over_brake_ticks + 1 if avg_brake > 0.75 else max(0, self.over_brake_ticks - 1)
        self.under_brake_ticks = self.under_brake_ticks + 1 if avg_brake < 0.15 else max(0, self.under_brake_ticks - 1)

        was_over, was_under = self.chronic_over, self.chronic_under
        self.chronic_over = self.over_brake_ticks > 18
        self.chronic_under = self.under_brake_ticks > 18

        if self.chronic_under and not was_under:
            self.feed_to_memory({"event": "impulse_brake_failure", "slippage": self.impulse_slippage,
                                  "note": "Impulse brake chronically weak — urgency not caught before action"})
        if self.chronic_over and not was_over:
            self.feed_to_memory({"event": "impulse_brake_over_engaged", "note": "Even appropriate actions suppressed"})

        return {
            "brake_force": round(effective_brake, 3),
            "brake_engaged": self.brake_engaged,
            "action_remaining": round(max(0.0, 1.0 - effective_brake), 3),
            "impulse_slippage": self.impulse_slippage,
            "paralysis_count": self.paralysis_count,
            "chronic_over": self.chronic_over,
            "chronic_under": self.chronic_under,
        }

    def _overnight(self):
        self.over_brake_ticks = max(0, self.over_brake_ticks - 5)
        self.under_brake_ticks = max(0, self.under_brake_ticks - 5)
        self.chronic_over = self.over_brake_ticks > 18
        self.chronic_under = self.under_brake_ticks > 18
        self.brake_history.clear()
        self.impulse_slippage = max(0, self.impulse_slippage - 2)
        return {"overnight": "impulse_brake_recalibrated"}
