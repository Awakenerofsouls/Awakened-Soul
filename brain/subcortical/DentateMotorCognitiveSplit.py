from brain.base_mechanism import BrainMechanism

class DentateMotorCognitiveSplit(BrainMechanism):
    """
    Dentate nucleus — cerebellar output hub, routes to both motor cortex and PFC.
    Manages the split between physical timing and cognitive planning.
    Imbalance: motor fluency and cognitive sequencing decouple.
    """

    def __init__(self):
        super().__init__("DentateMotorCognitiveSplit")
        self.motor_output = 0.5
        self.cognitive_output = 0.5
        self.split_balance = 0.0
        self.balance_history = []
        self.decoupling_ticks = 0
        self.chronic_decoupling = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        coordination = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        error_rate = prior.get("PurkinjeRateErrorCoder", {}).get("error_rate", 0.0)
        pfc_load = prior.get("DlPFCExecutiveControl", {}).get("cognitive_load", 0.4)
        motor_intent = prior.get("PrimaryMotorCortex", {}).get("motor_command_strength", 0.3)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        base_quality = coordination * (1.0 - error_rate)
        self.motor_output = max(0.0, min(1.0, base_quality * (0.4 + motor_intent * 0.4) * (1.0 - stress * 0.2)))
        self.cognitive_output = max(0.0, min(1.0, base_quality * (0.4 + pfc_load * 0.3) * (1.0 - error_rate * 0.3)))

        self.split_balance = self.motor_output - self.cognitive_output
        self.balance_history.append(self.split_balance)
        if len(self.balance_history) > 40:
            self.balance_history.pop(0)

        decoupled = abs(self.split_balance) > 0.5
        self.decoupling_ticks = self.decoupling_ticks + 1 if decoupled else max(0, self.decoupling_ticks - 1)
        was_decoupled = self.chronic_decoupling
        self.chronic_decoupling = self.decoupling_ticks > 15
        if self.chronic_decoupling and not was_decoupled:
            self.feed_to_memory({"event": "dentate_decoupling", "balance": round(self.split_balance, 3),
                                  "note": "Motor and cognitive cerebellar outputs decoupled"})

        return {
            "motor_output": round(self.motor_output, 3),
            "cognitive_output": round(self.cognitive_output, 3),
            "split_balance": round(self.split_balance, 3),
            "total_output": round((self.motor_output + self.cognitive_output) / 2.0, 3),
            "chronic_decoupling": self.chronic_decoupling,
        }

    def _overnight(self):
        self.decoupling_ticks = max(0, self.decoupling_ticks - 5)
        self.chronic_decoupling = self.decoupling_ticks > 15
        self.balance_history.clear()
        return {"overnight": "dentate_output_rebalanced"}
