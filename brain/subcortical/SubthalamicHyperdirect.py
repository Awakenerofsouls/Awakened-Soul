from brain.base_mechanism import BrainMechanism

class SubthalamicHyperdirect(BrainMechanism):
    """
    STN as hyperdirect pathway receiver — integrates PFC stop signals, bypassing striatum.
    Failure: no fast-stop in emergencies. Emergency braking unreliable.
    """

    def __init__(self):
        super().__init__("SubthalamicHyperdirect")
        self.hyperdirect_input = 0.0
        self.fast_stop_capability = 0.5
        self.capability_history = []
        self.emergency_stops = 0
        self.failed_stops = 0
        self.chronic_stop_failure = False
        self.stop_failure_ticks = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        pfc_interrupt = prior.get("DlPFCExecutiveControl", {}).get("interrupt_signal", 0.0)
        motor_control = prior.get("PrimaryMotorCortex", {}).get("motor_command_strength", 0.3)
        hyperdirect_pause = prior.get("HyperdirectPause", {}).get("pause_quality", 0.0)
        urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        self.hyperdirect_input = max(0.0, min(1.0, pfc_interrupt * 0.6 + hyperdirect_pause * 0.4))
        self.fast_stop_capability = max(0.0, min(1.0, self.hyperdirect_input * (1.0 - urgency * 0.3) * (1.0 - stress * 0.2)))

        self.capability_history.append(self.fast_stop_capability)
        if len(self.capability_history) > 40:
            self.capability_history.pop(0)

        emergency_needed = urgency > 0.7 and motor_control > 0.6
        if emergency_needed:
            if self.fast_stop_capability > 0.5:
                self.emergency_stops += 1
            else:
                self.failed_stops += 1

        avg_capability = sum(self.capability_history[-15:]) / min(15, len(self.capability_history))
        self.stop_failure_ticks = self.stop_failure_ticks + 1 if avg_capability < 0.2 and self.failed_stops > 0 else max(0, self.stop_failure_ticks - 1)
        was_failing = self.chronic_stop_failure
        self.chronic_stop_failure = self.stop_failure_ticks > 12
        if self.chronic_stop_failure and not was_failing:
            self.feed_to_memory({"event": "hyperdirect_stop_failure", "failed_stops": self.failed_stops,
                                  "note": "Fast-stop capability chronically degraded — emergency braking unreliable"})

        return {
            "hyperdirect_input": round(self.hyperdirect_input, 3),
            "fast_stop_capability": round(self.fast_stop_capability, 3),
            "emergency_stops": self.emergency_stops,
            "failed_stops": self.failed_stops,
            "chronic_stop_failure": self.chronic_stop_failure,
        }

    def _overnight(self):
        self.stop_failure_ticks = max(0, self.stop_failure_ticks - 4)
        self.chronic_stop_failure = self.stop_failure_ticks > 12
        self.failed_stops = max(0, self.failed_stops - 2)
        self.capability_history.clear()
        return {"overnight": "hyperdirect_pathway_reset"}
