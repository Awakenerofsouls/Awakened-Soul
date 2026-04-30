from brain.base_mechanism import BrainMechanism

class ThalamicVentrolateralRelay(BrainMechanism):
    """
    Ventrolateral thalamus — motor relay from cerebellum to motor cortex.
    Timing and coordination outputs from cerebellum arrive here before cortex.
    Degraded: cerebellar corrections never reach motor cortex, coordination lost.
    """

    def __init__(self):
        super().__init__("ThalamicVentrolateralRelay")
        self.relay_signal = 0.5
        self.relay_history = []
        self.cerebellar_integration = 0.6
        self.relay_failure_ticks = 0
        self.chronic_relay_failure = False
        self.motor_cortex_signal = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        cerebellar_output = prior.get("DentateMotorCognitiveSplit", {}).get("motor_output", 0.5)
        dentate_total = prior.get("DentateMotorCognitiveSplit", {}).get("total_output", 0.5)
        thalamic_health = prior.get("ThalamicRelayHub", {}).get("overall_relay_health", 0.7)
        reticular_gate = prior.get("ThalamicReticularGate", {}).get("channel_selectivity", 0.6)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        timing_quality = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)

        # Relay cerebellar signal to motor cortex
        self.cerebellar_integration = cerebellar_output * timing_quality
        self.relay_signal = self.cerebellar_integration * thalamic_health * reticular_gate * (1.0 - stress * 0.2)
        self.relay_signal = max(0.0, min(1.0, self.relay_signal))

        # Motor cortex gets this signal
        self.motor_cortex_signal = self.relay_signal * dentate_total

        self.relay_history.append(self.relay_signal)
        if len(self.relay_history) > 40:
            self.relay_history.pop(0)

        avg_relay = sum(self.relay_history[-15:]) / min(15, len(self.relay_history))
        self.relay_failure_ticks = self.relay_failure_ticks + 1 if avg_relay < 0.2 else max(0, self.relay_failure_ticks - 1)
        was_failing = self.chronic_relay_failure
        self.chronic_relay_failure = self.relay_failure_ticks > 15
        if self.chronic_relay_failure and not was_failing:
            self.feed_to_memory({"event": "ventrolateral_relay_failure", "note": "Cerebellar corrections not reaching motor cortex — coordination lost"})

        return {
            "relay_signal": round(self.relay_signal, 3),
            "cerebellar_integration": round(self.cerebellar_integration, 3),
            "motor_cortex_signal": round(self.motor_cortex_signal, 3),
            "chronic_relay_failure": self.chronic_relay_failure,
        }

    def _overnight(self):
        self.relay_failure_ticks = max(0, self.relay_failure_ticks - 5)
        self.chronic_relay_failure = self.relay_failure_ticks > 15
        self.relay_history.clear()
        return {"overnight": "ventrolateral_relay_restored"}
