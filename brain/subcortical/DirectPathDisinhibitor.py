from brain.base_mechanism import BrainMechanism

class DirectPathDisinhibitor(BrainMechanism):
    """
    Direct pathway (D1) — releases action by disinhibiting thalamus.
    Dopamine + desire open the gate: go signal.
    Low D1 = nothing gets through. High D1 = impulsive.
    """

    def __init__(self):
        super().__init__("DirectPathDisinhibitor")
        self.disinhibition_level = 0.0
        self.disinhibition_history = []
        self.go_signal_strength = 0.0
        self.akinesia_ticks = 0
        self.impulsive_ticks = 0
        self.chronic_akinesia = False
        self.chronic_impulsive = False
        self.d1_activity = 0.5

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        motivation = prior.get("NucleusAccumbens", {}).get("motivation_signal", 0.4)
        urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)
        brake = prior.get("ActionInhibitor", {}).get("brake_strength", 0.5)
        limbic_bias = prior.get("StriosomeLimbicBias", {}).get("dopamine_modulation", 0.0)

        self.d1_activity = min(1.0, dopamine * 0.5 + reward * 0.3 + motivation * 0.2 + limbic_bias * 0.2)
        raw_disinhibition = self.d1_activity * (1.0 - brake * 0.6) + urgency * 0.2
        self.disinhibition_level = max(0.0, min(1.0, raw_disinhibition))
        self.go_signal_strength = self.disinhibition_level * (1.0 - brake * 0.4)

        self.disinhibition_history.append(self.disinhibition_level)
        if len(self.disinhibition_history) > 40:
            self.disinhibition_history.pop(0)

        avg_dis = sum(self.disinhibition_history[-15:]) / min(15, len(self.disinhibition_history))
        self.akinesia_ticks = self.akinesia_ticks + 1 if avg_dis < 0.15 else max(0, self.akinesia_ticks - 1)
        self.impulsive_ticks = self.impulsive_ticks + 1 if avg_dis > 0.8 else max(0, self.impulsive_ticks - 1)

        was_akinesia, was_impulsive = self.chronic_akinesia, self.chronic_impulsive
        self.chronic_akinesia = self.akinesia_ticks > 18
        self.chronic_impulsive = self.impulsive_ticks > 18

        if self.chronic_akinesia and not was_akinesia:
            self.feed_to_memory({"event": "direct_path_suppressed", "note": "Action initiation impaired, withdrawal state"})
        if self.chronic_impulsive and not was_impulsive:
            self.feed_to_memory({"event": "direct_path_hyperactive", "note": "Impulsive go signals without sufficient braking"})

        return {
            "d1_activity": round(self.d1_activity, 3),
            "disinhibition_level": round(self.disinhibition_level, 3),
            "go_signal_strength": round(self.go_signal_strength, 3),
            "chronic_akinesia": self.chronic_akinesia,
            "chronic_impulsive": self.chronic_impulsive,
        }

    def _overnight(self):
        self.akinesia_ticks = max(0, self.akinesia_ticks - 5)
        self.impulsive_ticks = max(0, self.impulsive_ticks - 5)
        self.chronic_akinesia = self.akinesia_ticks > 18
        self.chronic_impulsive = self.impulsive_ticks > 18
        self.disinhibition_history.clear()
        return {"overnight": "direct_pathway_reset"}
