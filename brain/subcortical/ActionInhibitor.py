from brain.base_mechanism import BrainMechanism

class ActionInhibitor(BrainMechanism):
    """
    Subthalamic nucleus / indirect pathway — brakes on impulsive action.
    Applies stop signals before actions execute. Failure = impulsivity.
    Chronic over-inhibition = paralysis. Under-inhibition = recklessness.
    """

    def __init__(self):
        super().__init__("ActionInhibitor")
        self.brake_history = []
        self.stop_signal_active = False
        self.stop_duration = 0
        self.impulsive_event_log = []
        self.over_inhibition_ticks = 0
        self.under_inhibition_ticks = 0
        self.chronic_paralysis = False
        self.chronic_impulsivity = False
        self.brake_strength = 0.5
        self.brake_history_long = []

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        prefrontal = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        habit_strength = prior.get("DorsalStriatumHabitExecutor", {}).get("habit_execution_strength", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        raw_stop = (prefrontal * 0.4 + conflict * 0.4) - (urgency * 0.3) - (dopamine * 0.2)
        raw_stop = max(0.0, min(1.0, raw_stop + 0.1))
        if stress > 0.7:
            raw_stop *= 0.6

        self.brake_strength = raw_stop
        self.brake_history.append(raw_stop)
        self.brake_history_long.append(raw_stop)
        if len(self.brake_history) > 20:
            self.brake_history.pop(0)
        if len(self.brake_history_long) > 60:
            self.brake_history_long.pop(0)

        was_active = self.stop_signal_active
        self.stop_signal_active = raw_stop > 0.5
        if self.stop_signal_active:
            self.stop_duration += 1
        else:
            self.stop_duration = 0

        impulsive = urgency > 0.6 and raw_stop < 0.3
        if impulsive:
            self.impulsive_event_log.append(1)
            if len(self.impulsive_event_log) > 20:
                self.impulsive_event_log.pop(0)

        avg_brake = sum(self.brake_history) / len(self.brake_history) if self.brake_history else 0.5
        self.over_inhibition_ticks = self.over_inhibition_ticks + 1 if avg_brake > 0.75 else max(0, self.over_inhibition_ticks - 1)
        self.under_inhibition_ticks = self.under_inhibition_ticks + 1 if avg_brake < 0.2 else max(0, self.under_inhibition_ticks - 1)

        was_paralyzed, was_impulsive = self.chronic_paralysis, self.chronic_impulsivity
        self.chronic_paralysis = self.over_inhibition_ticks > 15
        self.chronic_impulsivity = self.under_inhibition_ticks > 15

        if self.chronic_paralysis and not was_paralyzed:
            self.feed_to_memory({"event": "chronic_over_inhibition", "note": "Stop signal chronically high — action initiation impaired"})
        if self.chronic_impulsivity and not was_impulsive:
            self.feed_to_memory({"event": "chronic_under_inhibition", "note": "Stop signal chronically low — impulsive action pattern emerging"})

        action_permission = max(0.0, min(1.0, (1.0 - raw_stop) * (1.0 + habit_strength * 0.2)))

        return {
            "brake_strength": round(raw_stop, 3),
            "stop_signal_active": self.stop_signal_active,
            "stop_duration": self.stop_duration,
            "action_permission": round(action_permission, 3),
            "chronic_paralysis": self.chronic_paralysis,
            "chronic_impulsivity": self.chronic_impulsivity,
            "impulsive_rate": round(sum(self.impulsive_event_log[-10:]) / 10, 3) if len(self.impulsive_event_log) >= 10 else 0.0,
        }

    def _overnight(self):
        self.over_inhibition_ticks = max(0, self.over_inhibition_ticks - 4)
        self.under_inhibition_ticks = max(0, self.under_inhibition_ticks - 4)
        self.chronic_paralysis = self.over_inhibition_ticks > 15
        self.chronic_impulsivity = self.under_inhibition_ticks > 15
        self.brake_history.clear()
        self.impulsive_event_log.clear()
        self.stop_duration = 0
        return {"overnight": "inhibition_recalibrated"}
