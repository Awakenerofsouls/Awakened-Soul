from brain.base_mechanism import BrainMechanism

class MatrixStriatalLoop(BrainMechanism):
    """
    Matrix striatal cortico-striato-thalamo-cortical loop — tracks full loop completion.
    Loop gain determines whether habits reinforce or fade.
    """

    def __init__(self):
        super().__init__("MatrixStriatalLoop")
        self.loop_gain = 0.6
        self.gain_history = []
        self.loop_completions = 0
        self.loop_breaks = 0
        self.chronic_loop_break = False
        self.break_ticks = 0
        self.loop_integrity = 0.7

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        matrix_output = prior.get("StriatumMatrixCompartment", {}).get("matrix_output", 0.5)
        gpi_gate = prior.get("GlobusPallidusInternal", {}).get("action_gate_open", False)
        thalamic_health = prior.get("ThalamicRelayHub", {}).get("overall_relay_health", 0.7)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        relay_throughput = prior.get("ExecutiveRelayHub", {}).get("relay_throughput", 0.7)

        if gpi_gate:
            self.loop_gain = matrix_output * thalamic_health * relay_throughput * dopamine
            self.loop_completions += 1
        else:
            self.loop_gain = 0.0
            self.loop_breaks += 1

        total = self.loop_completions + self.loop_breaks
        self.loop_integrity = self.loop_completions / total if total > 0 else 0.5

        self.gain_history.append(self.loop_gain)
        if len(self.gain_history) > 40:
            self.gain_history.pop(0)

        avg_gain = sum(self.gain_history[-15:]) / min(15, len(self.gain_history))
        self.break_ticks = self.break_ticks + 1 if avg_gain < 0.1 else max(0, self.break_ticks - 1)
        was_broken = self.chronic_loop_break
        self.chronic_loop_break = self.break_ticks > 15
        if self.chronic_loop_break and not was_broken:
            self.feed_to_memory({"event": "striatal_loop_break", "integrity": round(self.loop_integrity, 3),
                                  "note": "Cortico-striatal loop chronically broken — habit reinforcement failing"})

        return {
            "loop_gain": round(self.loop_gain, 3),
            "loop_integrity": round(self.loop_integrity, 3),
            "loop_completions": self.loop_completions,
            "loop_breaks": self.loop_breaks,
            "chronic_loop_break": self.chronic_loop_break,
        }

    def _overnight(self):
        self.break_ticks = max(0, self.break_ticks - 5)
        self.chronic_loop_break = self.break_ticks > 15
        self.gain_history.clear()
        return {"overnight": "matrix_loop_reset"}
