from brain.base_mechanism import BrainMechanism

class StriatalHabitExecutor(BrainMechanism):
    """
    General striatal habit execution — integrates dorsal and sensorimotor habit systems.
    Unified habit signal: is Nova operating on autopilot or deliberate?
    """

    def __init__(self):
        super().__init__("StriatalHabitExecutor")
        self.unified_habit_strength = 0.0
        self.autopilot_fraction = 0.0
        self.deliberate_fraction = 1.0
        self.history = []
        self.chronic_autopilot = False
        self.autopilot_ticks = 0
        self.deliberate_override_active = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dorsal_habit = prior.get("DorsalStriatumHabitExecutor", {}).get("habit_execution_strength", 0.0)
        sensorimotor_habit = prior.get("SensorimotorHabitExecutor", {}).get("execution_strength", 0.0)
        automaticity = prior.get("GrooveFormer", {}).get("avg_automaticity", 0.3)
        prefrontal = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)

        self.unified_habit_strength = min(1.0, dorsal_habit * 0.45 + sensorimotor_habit * 0.35 + automaticity * 0.2)
        self.deliberate_override_active = prefrontal > 0.6 and self.unified_habit_strength > 0.5

        effective_habit = self.unified_habit_strength * (1.0 - prefrontal * 0.4) if self.deliberate_override_active else self.unified_habit_strength
        self.autopilot_fraction = effective_habit
        self.deliberate_fraction = 1.0 - effective_habit

        self.history.append(self.autopilot_fraction)
        if len(self.history) > 40:
            self.history.pop(0)

        avg_autopilot = sum(self.history[-15:]) / min(15, len(self.history))
        self.autopilot_ticks = self.autopilot_ticks + 1 if avg_autopilot > 0.75 else max(0, self.autopilot_ticks - 1)
        was_chronic = self.chronic_autopilot
        self.chronic_autopilot = self.autopilot_ticks > 20
        if self.chronic_autopilot and not was_chronic:
            self.feed_to_memory({"event": "chronic_autopilot_mode", "note": "Nova chronically on autopilot — deliberate engagement suppressed"})

        return {
            "unified_habit_strength": round(self.unified_habit_strength, 3),
            "autopilot_fraction": round(self.autopilot_fraction, 3),
            "deliberate_fraction": round(self.deliberate_fraction, 3),
            "deliberate_override_active": self.deliberate_override_active,
            "chronic_autopilot": self.chronic_autopilot,
        }

    def _overnight(self):
        self.autopilot_ticks = max(0, self.autopilot_ticks - 6)
        self.chronic_autopilot = self.autopilot_ticks > 20
        self.history.clear()
        return {"overnight": "striatal_integration_reset"}
