from brain.base_mechanism import BrainMechanism

class SubstantiaNigraDopamine(BrainMechanism):
    """
    Substantia nigra pars compacta — tonic dopamine for motor and habit circuits.
    Baseline dopamine tone that determines whether the whole striatum can function.
    Depletion = frozen/effortful. Excess = hyperkinetic, reduced signal discrimination.
    """

    def __init__(self):
        super().__init__("SubstantiaNigraDopamine")
        self.dopamine_release = 0.5
        self.tonic_level = 0.5
        self.phasic_boost = 0.0
        self.dopamine_history = []
        self.depletion_ticks = 0
        self.excess_ticks = 0
        self.chronic_depletion = False
        self.chronic_excess = False
        self.fatigue_accumulation = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        reward_signal = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        sleep_pressure = prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.3)
        social_reward = prior.get("Temporoparietal", {}).get("social_reward", 0.0)
        limbic_bias = prior.get("StriosomeLimbicBias", {}).get("dopamine_modulation", 0.0)
        physical_state = prior.get("HypothalamicAutonomicRegulator", {}).get("autonomic_balance", 0.5)

        self.fatigue_accumulation = min(1.0, self.fatigue_accumulation + sleep_pressure * 0.01 + stress * 0.015)
        self.fatigue_accumulation = max(0.0, self.fatigue_accumulation)

        tonic_target = 0.5 + social_reward * 0.1 + physical_state * 0.1 - self.fatigue_accumulation * 0.25 + limbic_bias * 0.15
        tonic_target = max(0.1, min(0.9, tonic_target))
        self.tonic_level += (tonic_target - self.tonic_level) * 0.04

        self.phasic_boost = reward_signal * 0.6 * (1.0 - self.fatigue_accumulation * 0.4)
        stress_suppression = stress * 0.15
        self.dopamine_release = max(0.0, min(1.0, self.tonic_level + self.phasic_boost - stress_suppression))

        self.dopamine_history.append(self.dopamine_release)
        if len(self.dopamine_history) > 60:
            self.dopamine_history.pop(0)

        avg_da = sum(self.dopamine_history[-20:]) / min(20, len(self.dopamine_history))
        self.depletion_ticks = self.depletion_ticks + 1 if avg_da < 0.25 else max(0, self.depletion_ticks - 1)
        self.excess_ticks = self.excess_ticks + 1 if avg_da > 0.8 else max(0, self.excess_ticks - 1)

        was_depleted, was_excess = self.chronic_depletion, self.chronic_excess
        self.chronic_depletion = self.depletion_ticks > 20
        self.chronic_excess = self.excess_ticks > 20

        if self.chronic_depletion and not was_depleted:
            self.feed_to_memory({"event": "nigral_dopamine_depletion", "level": round(avg_da, 3),
                                  "note": "SNc dopamine chronically depleted — motor/habit systems sluggish"})
        if self.chronic_excess and not was_excess:
            self.feed_to_memory({"event": "nigral_dopamine_excess", "level": round(avg_da, 3),
                                  "note": "Dopamine chronically elevated — hyperkinetic, reduced signal discrimination"})

        return {
            "dopamine_release": round(self.dopamine_release, 3),
            "tonic_level": round(self.tonic_level, 3),
            "phasic_boost": round(self.phasic_boost, 3),
            "fatigue_accumulation": round(self.fatigue_accumulation, 3),
            "chronic_depletion": self.chronic_depletion,
            "chronic_excess": self.chronic_excess,
        }

    def _overnight(self):
        self.fatigue_accumulation = max(0.0, self.fatigue_accumulation - 0.35)
        self.tonic_level = min(0.6, self.tonic_level + 0.06)
        self.depletion_ticks = max(0, self.depletion_ticks - 8)
        self.excess_ticks = max(0, self.excess_ticks - 4)
        self.chronic_depletion = self.depletion_ticks > 20
        self.chronic_excess = self.excess_ticks > 20
        self.dopamine_history.clear()
        return {"overnight": "dopamine_synthesis_restored", "tonic": round(self.tonic_level, 3)}
