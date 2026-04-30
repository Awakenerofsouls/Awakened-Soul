from brain.base_mechanism import BrainMechanism

class SensorimotorHabitExecutor(BrainMechanism):
    """
    Posterior putamen — sensorimotor habit execution. Sensory trigger -> action, no thought.
    Nova analog: linguistic habits, response patterns triggered by specific input features.
    """

    def __init__(self):
        super().__init__("SensorimotorHabitExecutor")
        self.sensorimotor_habits = {}
        self.execution_history = []
        self.trigger_log = []
        self.auto_execution_count = 0
        self.rigidity_ticks = 0
        self.chronic_rigidity = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        sensory_salience = prior.get("VisualSalienceFilter", {}).get("detected_salience", 0.3)
        override_cost = prior.get("DorsalStriatumHabitExecutor", {}).get("goal_override_cost", 0.0)
        motor_timing = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)

        trigger = self._extract_trigger(text)
        if trigger:
            current = self.sensorimotor_habits.get(trigger, 0.0)
            self.sensorimotor_habits[trigger] = min(1.0, current + 0.05 * dopamine * sensory_salience)
            self.trigger_log.append(trigger)
            if len(self.trigger_log) > 20:
                self.trigger_log.pop(0)

        for k in list(self.sensorimotor_habits.keys()):
            if k != trigger:
                self.sensorimotor_habits[k] = max(0.0, self.sensorimotor_habits[k] - 0.005)
            if self.sensorimotor_habits[k] < 0.01:
                del self.sensorimotor_habits[k]

        habit_val = self.sensorimotor_habits.get(trigger, 0.0) if trigger else 0.0
        execution_strength = habit_val * motor_timing * dopamine
        auto_executed = execution_strength > 0.65 and override_cost < 0.4
        if auto_executed:
            self.auto_execution_count += 1

        self.execution_history.append(execution_strength)
        if len(self.execution_history) > 40:
            self.execution_history.pop(0)

        avg_exec = sum(self.execution_history[-15:]) / min(15, len(self.execution_history))
        deep_habits = sum(1 for v in self.sensorimotor_habits.values() if v > 0.75)
        self.rigidity_ticks = self.rigidity_ticks + 1 if deep_habits >= 3 and avg_exec > 0.6 else max(0, self.rigidity_ticks - 1)
        was_rigid = self.chronic_rigidity
        self.chronic_rigidity = self.rigidity_ticks > 18
        if self.chronic_rigidity and not was_rigid:
            self.feed_to_memory({"event": "sensorimotor_rigidity", "deep_habits": deep_habits,
                                  "note": "Sensorimotor habits deeply grooved — linguistic patterns very automatic"})

        return {
            "execution_strength": round(execution_strength, 3),
            "auto_executed": auto_executed,
            "active_habits": len(self.sensorimotor_habits),
            "auto_execution_count": self.auto_execution_count,
            "chronic_rigidity": self.chronic_rigidity,
        }

    def _extract_trigger(self, text):
        if not text:
            return ""
        words = text.lower().split()
        if len(words) >= 2:
            return f"{words[0]}_{words[1]}"[:32]
        return words[0][:32] if words else ""

    def _overnight(self):
        for k in list(self.sensorimotor_habits.keys()):
            v = self.sensorimotor_habits[k]
            self.sensorimotor_habits[k] = min(1.0, v + 0.008) if v > 0.5 else max(0.0, v - 0.01)
            if self.sensorimotor_habits[k] < 0.01:
                del self.sensorimotor_habits[k]
        self.rigidity_ticks = max(0, self.rigidity_ticks - 5)
        self.chronic_rigidity = self.rigidity_ticks > 18
        return {"overnight": "sensorimotor_habits_consolidated"}
