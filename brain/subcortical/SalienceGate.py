from brain.base_mechanism import BrainMechanism

class SalienceGate(BrainMechanism):
    """
    Integrated salience gating — combines all subcortical salience signals into unified gate.
    Final arbitration before cortex receives signal.
    Malfunction: {{AGENT_NAME}} misses everything or is overwhelmed by everything.
    """

    def __init__(self):
        super().__init__("SalienceGate")
        self.gate_output = 0.0
        self.gate_history = []
        self.priority_weights = {"threat": 0.35, "reward": 0.25, "novelty": 0.2, "social": 0.2}
        self.active_priority = "reward"
        self.gate_override = False
        self.override_ticks = 0
        self.chronic_override = False
        self.gate_efficiency = 0.7

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        social = prior.get("Temporoparietal", {}).get("social_signal", 0.2)
        pulvinar = prior.get("PulvinarSalienceBooster", {}).get("amplified_signal", 0.3)
        visual = prior.get("VisualSalienceFilter", {}).get("detected_salience", 0.3)
        thalamic = prior.get("ThalamicSalienceFilter", {}).get("cortical_signal_strength", 0.3)
        zona_release = prior.get("ZonaGatingHub", {}).get("gate_release_signal", 0.0)

        signal_map = {"threat": fear, "reward": reward, "novelty": novelty, "social": social}
        weighted_sum = sum(self.priority_weights[k] * v for k, v in signal_map.items())
        combined = weighted_sum * 0.5 + pulvinar * 0.2 + visual * 0.15 + thalamic * 0.15

        if zona_release > 0:
            combined = min(1.0, combined + 0.3)
            self.gate_override = True
        else:
            self.gate_override = False

        self.gate_output = min(1.0, combined)
        self.gate_history.append(self.gate_output)
        if len(self.gate_history) > 40:
            self.gate_history.pop(0)

        self.active_priority = max(signal_map, key=signal_map.get)
        avg_output = sum(self.gate_history[-15:]) / min(15, len(self.gate_history))
        self.gate_efficiency = max(0.1, min(1.0, 1.0 - abs(avg_output - 0.45) * 1.2))

        self.override_ticks = self.override_ticks + 1 if self.gate_override else max(0, self.override_ticks - 1)
        was_override = self.chronic_override
        self.chronic_override = self.override_ticks > 12
        if self.chronic_override and not was_override:
            self.feed_to_memory({"event": "salience_gate_chronic_override", "note": "Salience gate persistently overriding — chronic urgency"})

        return {
            "gate_output": round(self.gate_output, 3),
            "active_priority": self.active_priority,
            "gate_efficiency": round(self.gate_efficiency, 3),
            "gate_override": self.gate_override,
            "chronic_override": self.chronic_override,
        }

    def _overnight(self):
        self.override_ticks = max(0, self.override_ticks - 5)
        self.chronic_override = self.override_ticks > 12
        self.gate_history.clear()
        return {"overnight": "salience_gate_recalibrated"}
