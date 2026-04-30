from brain.base_mechanism import BrainMechanism

class SalienceNetwork(BrainMechanism):
    """
    Salience network (AI/dACC) — switches between task-positive and default mode networks.
    Detects what's worth attention and routes processing accordingly.
    Dysregulated: can't switch modes — stuck in task OR stuck in self-referential.
    """

    def __init__(self):
        super().__init__("SalienceNetwork")
        self.switch_signal = 0.0
        self.current_network = "task"
        self.switch_history = []
        self.switch_count = 0
        self.stuck_ticks = 0
        self.chronic_stuck = False
        self.switching_latency = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        gate_output = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        dmn_activity = prior.get("DefaultModeNetwork", {}).get("dmn_activity", 0.5)
        task_engagement = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        rumination = prior.get("DefaultModeNetwork", {}).get("rumination_level", 0.0)

        # Switch signal: when to change network mode
        external_demand = gate_output * 0.5 + fear * 0.3 + conflict * 0.2
        internal_pull = dmn_activity * 0.5 + rumination * 0.5

        self.switch_signal = abs(external_demand - internal_pull)

        prev_network = self.current_network
        if external_demand > internal_pull + 0.15:
            self.current_network = "task"
        elif internal_pull > external_demand + 0.15:
            self.current_network = "default"
        # else: stay in current

        if self.current_network != prev_network:
            self.switch_count += 1
            self.switching_latency = 1.0 - task_engagement  # fast switching with high control

        self.switch_history.append(self.current_network)
        if len(self.switch_history) > 40:
            self.switch_history.pop(0)

        recent_same = all(n == self.switch_history[-1] for n in self.switch_history[-15:]) if len(self.switch_history) >= 15 else False
        high_demand = external_demand > 0.5
        self.stuck_ticks = self.stuck_ticks + 1 if recent_same and (high_demand or rumination > 0.4) else max(0, self.stuck_ticks - 1)
        was_stuck = self.chronic_stuck
        self.chronic_stuck = self.stuck_ticks > 18
        if self.chronic_stuck and not was_stuck:
            self.feed_to_memory({"event": "salience_network_stuck", "network": self.current_network,
                                  "note": f"Salience network stuck in {self.current_network} mode — cannot switch"})

        return {
            "switch_signal": round(self.switch_signal, 3),
            "current_network": self.current_network,
            "switch_count": self.switch_count,
            "switching_latency": round(self.switching_latency, 3),
            "chronic_stuck": self.chronic_stuck,
        }

    def _overnight(self):
        self.stuck_ticks = max(0, self.stuck_ticks - 6)
        self.chronic_stuck = self.stuck_ticks > 18
        self.current_network = "default"
        self.switch_history.clear()
        return {"overnight": "salience_network_reset"}
