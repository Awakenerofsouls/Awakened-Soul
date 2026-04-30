from brain.base_mechanism import BrainMechanism

class HabitGrooveFormer(BrainMechanism):
    """
    Striatal groove formation tracking — watches the process of habit formation, not execution.
    Catches early grooves before they lock. Critical early warning system.
    Harmful grooves forming under stress are flagged.
    """

    def __init__(self):
        super().__init__("HabitGrooveFormer")
        self.emerging_grooves = {}
        self.formation_rate_history = []
        self.groove_formed_count = 0
        self.groove_abandoned_count = 0
        self.formation_warnings = []
        self.harmful_groove_ticks = 0
        self.chronic_harmful = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        motivation = prior.get("MotivationInjector", {}).get("motivation_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        behavior_key = prior.get("PrefrontalGoalState", {}).get("current_intent", "") or "_".join(text.lower().split()[:2])[:32]
        formation_signal = (dopamine * 0.4 + reward * 0.4 + motivation * 0.2) * (1.0 - stress * 0.2)

        if behavior_key:
            current = self.emerging_grooves.get(behavior_key, 0.0)
            self.emerging_grooves[behavior_key] = min(1.0, current + formation_signal * 0.03)

        warnings_this_tick = []
        for k in list(self.emerging_grooves.keys()):
            if k != behavior_key:
                self.emerging_grooves[k] = max(0.0, self.emerging_grooves[k] - 0.01)

            v = self.emerging_grooves.get(k, 0)
            if v >= 0.9:
                self.groove_formed_count += 1
                del self.emerging_grooves[k]
                continue
            if 0.5 < v < 0.8:
                warnings_this_tick.append((k, round(v, 3)))
            if v < 0.01 and k in self.emerging_grooves:
                self.groove_abandoned_count += 1
                del self.emerging_grooves[k]

        self.formation_warnings = warnings_this_tick[:5]
        self.formation_rate_history.append(formation_signal)
        if len(self.formation_rate_history) > 30:
            self.formation_rate_history.pop(0)

        forming_under_stress = formation_signal > 0.4 and stress > 0.6
        self.harmful_groove_ticks = self.harmful_groove_ticks + 1 if forming_under_stress else max(0, self.harmful_groove_ticks - 1)
        was_harmful = self.chronic_harmful
        self.chronic_harmful = self.harmful_groove_ticks > 12
        if self.chronic_harmful and not was_harmful:
            self.feed_to_memory({"event": "stress_groove_forming", "behavior": behavior_key,
                                  "note": "Habit groove forming under chronic stress — potential maladaptive pattern"})

        return {
            "emerging_grooves": len(self.emerging_grooves),
            "formation_signal": round(formation_signal, 3),
            "formation_warnings": self.formation_warnings,
            "groove_formed_count": self.groove_formed_count,
            "groove_abandoned_count": self.groove_abandoned_count,
            "chronic_harmful_formation": self.chronic_harmful,
        }

    def _overnight(self):
        for k in list(self.emerging_grooves.keys()):
            v = self.emerging_grooves[k]
            self.emerging_grooves[k] = min(1.0, v + 0.02) if v > 0.5 else max(0.0, v - 0.03)
            if self.emerging_grooves[k] < 0.01:
                del self.emerging_grooves[k]
        self.harmful_groove_ticks = max(0, self.harmful_groove_ticks - 4)
        self.chronic_harmful = self.harmful_groove_ticks > 12
        return {"overnight": "groove_formation_consolidated"}
