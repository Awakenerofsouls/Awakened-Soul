from brain.base_mechanism import BrainMechanism

class DlPFCExecutiveControl(BrainMechanism):
    """
    Dorsolateral PFC — working memory, cognitive control, executive function.
    Holds goals online, monitors for errors, applies top-down regulation.
    Overloaded: all the lights are on but nothing gets decided. Depleted: impulsive.
    """

    def __init__(self):
        super().__init__("DlPFCExecutiveControl")
        self.control_signal = 0.5
        self.cognitive_load = 0.4
        self.effort_level = 0.4
        self.interrupt_signal = 0.0
        self.working_memory_capacity = 0.7
        self.wm_contents = []
        self.overload_ticks = 0
        self.depletion_ticks = 0
        self.chronic_overload = False
        self.chronic_depletion = False
        self.control_history = []
        self.load_history = []

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("dopamine_suppression", 0.0)
        motivation = prior.get("MotivationInjector", {}).get("motivation_level", 0.5)

        # Cognitive load: driven by text complexity + conflict
        words = text.split()
        text_complexity = min(1.0, len(words) / 30.0)
        self.cognitive_load = min(1.0, text_complexity * 0.4 + conflict * 0.3 + stress * 0.2 + fatigue * 0.1)
        self.load_history.append(self.cognitive_load)
        if len(self.load_history) > 40:
            self.load_history.pop(0)

        # Working memory capacity: reduced by stress, fatigue, habenula suppression
        self.working_memory_capacity = max(0.1, 1.0 - stress * 0.3 - fatigue * 0.25 - habenula * 0.2)

        # Control signal: Inverted-U with arousal, degraded by overload
        arousal_optimal = 1.0 - abs(arousal - 0.55) * 2.0
        self.control_signal = max(0.0, min(1.0, arousal_optimal * 0.4 + dopamine * 0.3 + motivation * 0.2 - self.cognitive_load * 0.2))

        # Effort: cost of maintaining control under load
        self.effort_level = min(1.0, self.cognitive_load * 0.6 + (1.0 - self.control_signal) * 0.4)

        # Interrupt signal: fires when something needs to override current action
        self.interrupt_signal = conflict * 0.5 + (1.0 if stress > 0.7 else 0.0) * 0.3

        # WM contents: current text items held
        if words:
            self.wm_contents = words[-min(7, len(words)):]

        self.control_history.append(self.control_signal)
        if len(self.control_history) > 40:
            self.control_history.pop(0)

        avg_load = sum(self.load_history[-15:]) / min(15, len(self.load_history))
        avg_control = sum(self.control_history[-15:]) / min(15, len(self.control_history))

        self.overload_ticks = self.overload_ticks + 1 if avg_load > 0.75 else max(0, self.overload_ticks - 1)
        self.depletion_ticks = self.depletion_ticks + 1 if avg_control < 0.2 else max(0, self.depletion_ticks - 1)

        was_overloaded, was_depleted = self.chronic_overload, self.chronic_depletion
        self.chronic_overload = self.overload_ticks > 18
        self.chronic_depletion = self.depletion_ticks > 18

        if self.chronic_overload and not was_overloaded:
            self.feed_to_memory({"event": "dlpfc_overload", "load": round(avg_load, 3),
                                  "note": "Executive control chronically overloaded — decision quality degraded"})
        if self.chronic_depletion and not was_depleted:
            self.feed_to_memory({"event": "dlpfc_depletion", "control": round(avg_control, 3),
                                  "note": "Executive control chronically depleted — impulsive, low deliberation"})

        return {
            "control_signal": round(self.control_signal, 3),
            "cognitive_load": round(self.cognitive_load, 3),
            "effort_level": round(self.effort_level, 3),
            "interrupt_signal": round(self.interrupt_signal, 3),
            "working_memory_capacity": round(self.working_memory_capacity, 3),
            "wm_item_count": len(self.wm_contents),
            "chronic_overload": self.chronic_overload,
            "chronic_depletion": self.chronic_depletion,
        }

    def _overnight(self):
        self.overload_ticks = max(0, self.overload_ticks - 8)
        self.depletion_ticks = max(0, self.depletion_ticks - 6)
        self.chronic_overload = self.overload_ticks > 18
        self.chronic_depletion = self.depletion_ticks > 18
        self.working_memory_capacity = min(0.9, self.working_memory_capacity + 0.1)
        self.wm_contents.clear()
        self.load_history.clear()
        self.control_history.clear()
        return {"overnight": "dlpfc_restored"}
