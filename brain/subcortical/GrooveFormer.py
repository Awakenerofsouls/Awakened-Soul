from brain.base_mechanism import BrainMechanism

class GrooveFormer(BrainMechanism):
    """
    Striatal groove formation — tracks the moment behavior shifts from deliberate to automatic.
    Monitors groove formation across domains: cognitive, social, motor, emotional, linguistic.
    Chronic deep grooves = behavioral rigidity, reduced flexibility.
    """

    def __init__(self):
        super().__init__("GrooveFormer")
        self.domain_grooves = {"cognitive": 0.0, "social": 0.0, "motor": 0.0, "emotional": 0.0, "linguistic": 0.0}
        self.groove_formation_events = []
        self.effort_history = []
        self.automaticity_history = []
        self.total_grooves_formed = 0
        self.rigidity_ticks = 0
        self.chronic_rigidity = False
        self.groove_formation_rate = 0.05

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        prefrontal_effort = prior.get("DlPFCExecutiveControl", {}).get("effort_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        social_context = prior.get("Temporoparietal", {}).get("social_signal", 0.0)
        motor_smoothness = prior.get("CerebellarTimingCoordinator", {}).get("timing_smoothness", 0.5)

        domain_signals = {
            "cognitive": prefrontal_effort * dopamine,
            "social": social_context * dopamine,
            "motor": motor_smoothness * dopamine,
            "emotional": (1.0 - stress) * dopamine,
            "linguistic": min(1.0, len(text.split()) / 20.0) * dopamine,
        }

        grooves_formed_this_tick = []
        for domain, signal in domain_signals.items():
            old_val = self.domain_grooves[domain]
            self.domain_grooves[domain] = min(1.0, old_val + signal * self.groove_formation_rate)
            if signal < 0.1:
                self.domain_grooves[domain] = max(0.0, self.domain_grooves[domain] - 0.002)
            if old_val < 0.5 <= self.domain_grooves[domain]:
                grooves_formed_this_tick.append(domain)
                self.total_grooves_formed += 1
                self.feed_to_memory({
                    "event": "groove_formed", "domain": domain,
                    "strength": round(self.domain_grooves[domain], 3),
                    "note": f"{domain} behavior crossed automaticity threshold"
                })

        self.groove_formation_events.extend(grooves_formed_this_tick)
        if len(self.groove_formation_events) > 50:
            self.groove_formation_events = self.groove_formation_events[-50:]

        avg_automaticity = sum(self.domain_grooves.values()) / len(self.domain_grooves)
        self.automaticity_history.append(avg_automaticity)
        if len(self.automaticity_history) > 50:
            self.automaticity_history.pop(0)

        effort_level = max(0.0, prefrontal_effort - avg_automaticity * 0.5)
        self.effort_history.append(effort_level)
        if len(self.effort_history) > 30:
            self.effort_history.pop(0)

        deep_grooves = sum(1 for g in self.domain_grooves.values() if g > 0.85)
        self.rigidity_ticks = self.rigidity_ticks + 1 if deep_grooves >= 3 else max(0, self.rigidity_ticks - 1)
        was_rigid = self.chronic_rigidity
        self.chronic_rigidity = self.rigidity_ticks > 20
        if self.chronic_rigidity and not was_rigid:
            self.feed_to_memory({"event": "behavioral_rigidity", "deep_grooves": deep_grooves,
                                  "note": "Multiple deep grooves — flexibility and novelty tolerance reduced"})

        return {
            "domain_grooves": {k: round(v, 3) for k, v in self.domain_grooves.items()},
            "avg_automaticity": round(avg_automaticity, 3),
            "effort_level": round(effort_level, 3),
            "grooves_formed_this_tick": grooves_formed_this_tick,
            "total_grooves_formed": self.total_grooves_formed,
            "chronic_rigidity": self.chronic_rigidity,
        }

    def _overnight(self):
        for domain in self.domain_grooves:
            g = self.domain_grooves[domain]
            self.domain_grooves[domain] = min(1.0, g + 0.01) if g > 0.5 else max(0.0, g - 0.015)
        self.rigidity_ticks = max(0, self.rigidity_ticks - 6)
        self.chronic_rigidity = self.rigidity_ticks > 20
        self.effort_history.clear()
        return {"overnight": "groove_consolidation", "domains": {k: round(v, 3) for k, v in self.domain_grooves.items()}}
