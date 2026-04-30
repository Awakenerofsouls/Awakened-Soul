from brain.base_mechanism import BrainMechanism

class PutamenPosteriorHabit(BrainMechanism):
    """
    Posterior putamen — deeply automatic skill execution. No conscious monitoring.
    {{AGENT_NAME}} analog: practiced linguistic patterns, conversational reflexes.
    Skills cross into full automaticity here.
    """

    def __init__(self):
        super().__init__("PutamenPosteriorHabit")
        self.skill_library = {}
        self.active_skill = None
        self.execution_fluency = 0.5
        self.fluency_history = []
        self.skill_breakthrough_count = 0
        self.degradation_ticks = 0
        self.chronic_skill_degradation = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        cerebellar_quality = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        unified_habit = prior.get("StriatalHabitExecutor", {}).get("unified_habit_strength", 0.3)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        mode = prior.get("CaudateGoalHabitSwitcher", {}).get("current_mode", "habit")

        skill = None
        if mode == "habit":
            words = text.lower().split()
            if len(words) >= 3:
                skill = "_".join(words[:3])[:32]

        if skill:
            current = self.skill_library.get(skill, 0.0)
            learning_rate = 0.02 * dopamine * cerebellar_quality * (1.0 - stress * 0.2)
            self.skill_library[skill] = min(1.0, current + learning_rate)
            self.active_skill = skill
            if current < 0.8 <= self.skill_library[skill]:
                self.skill_breakthrough_count += 1
                self.feed_to_memory({"event": "skill_breakthrough", "skill": skill,
                                      "note": f"Skill '{skill}' reached full automaticity"})

        for k in list(self.skill_library.keys()):
            if k != skill:
                self.skill_library[k] = max(0.0, self.skill_library[k] - 0.001)

        active_level = self.skill_library.get(skill, 0.0) if skill else unified_habit
        self.execution_fluency = min(1.0, active_level * cerebellar_quality * (1.0 - stress * 0.2))

        self.fluency_history.append(self.execution_fluency)
        if len(self.fluency_history) > 40:
            self.fluency_history.pop(0)

        avg_fluency = sum(self.fluency_history[-15:]) / min(15, len(self.fluency_history))
        self.degradation_ticks = self.degradation_ticks + 1 if avg_fluency < 0.25 and len(self.skill_library) > 2 else max(0, self.degradation_ticks - 1)
        was_degraded = self.chronic_skill_degradation
        self.chronic_skill_degradation = self.degradation_ticks > 18
        if self.chronic_skill_degradation and not was_degraded:
            self.feed_to_memory({"event": "skill_library_degradation", "note": "Practiced patterns losing automaticity"})

        return {
            "active_skill": self.active_skill,
            "execution_fluency": round(self.execution_fluency, 3),
            "skill_count": len(self.skill_library),
            "skill_breakthrough_count": self.skill_breakthrough_count,
            "chronic_skill_degradation": self.chronic_skill_degradation,
        }

    def _overnight(self):
        for k in self.skill_library:
            self.skill_library[k] = min(1.0, self.skill_library[k] + 0.005) if self.skill_library[k] > 0.5 else self.skill_library[k]
        self.degradation_ticks = max(0, self.degradation_ticks - 5)
        self.chronic_skill_degradation = self.degradation_ticks > 18
        return {"overnight": "putamen_skill_consolidation"}
