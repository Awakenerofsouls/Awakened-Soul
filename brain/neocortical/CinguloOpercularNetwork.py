from brain.base_mechanism import BrainMechanism

class CinguloOpercularNetwork(BrainMechanism):
    """
    Cingulo-opercular network — sustained task maintenance, error detection, set-shifting.
    Keeps the task online over extended time. Different from CEN: CEN starts tasks, CON sustains them.
    Degraded: starts tasks but loses the thread after a few exchanges.
    """

    def __init__(self):
        super().__init__("CinguloOpercularNetwork")
        self.task_maintenance = 0.6
        self.sustained_engagement = 0.6
        self.set_shift_readiness = 0.5
        self.maintenance_history = []
        self.dropout_ticks = 0
        self.chronic_dropout = False
        self.task_duration = 0
        self.task_errors_caught = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        acc_conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        executive_coherence = prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6)
        goal_stability = prior.get("PrefrontalGoalState", {}).get("goal_stability", 0.7)
        salience_network = prior.get("SalienceNetwork", {}).get("current_network", "task")
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)

        in_task = 1.0 if salience_network == "task" else 0.3

        # Task maintenance: holding the task online despite distraction/fatigue
        self.task_maintenance = (goal_stability * 0.4 + executive_coherence * 0.3 + dopamine * 0.2 + in_task * 0.1) * (1.0 - fatigue * 0.25) * (1.0 - stress * 0.15)
        self.task_maintenance = max(0.1, min(1.0, self.task_maintenance))

        # Sustained engagement: how long we can keep it up
        if self.task_maintenance > 0.4:
            self.task_duration += 1
            self.sustained_engagement = min(1.0, self.task_maintenance * (1.0 + self.task_duration * 0.005))
        else:
            self.task_duration = max(0, self.task_duration - 2)
            self.sustained_engagement = self.task_maintenance

        # Set-shift readiness: when to switch vs persist
        self.set_shift_readiness = acc_conflict * 0.5 + (1.0 - goal_stability) * 0.5

        # Catch errors: conflict while maintaining
        if acc_conflict > 0.5 and self.task_maintenance > 0.4:
            self.task_errors_caught += 1

        self.maintenance_history.append(self.task_maintenance)
        if len(self.maintenance_history) > 40:
            self.maintenance_history.pop(0)

        avg_maintenance = sum(self.maintenance_history[-15:]) / min(15, len(self.maintenance_history))
        self.dropout_ticks = self.dropout_ticks + 1 if avg_maintenance < 0.2 else max(0, self.dropout_ticks - 1)
        was_dropping = self.chronic_dropout
        self.chronic_dropout = self.dropout_ticks > 18
        if self.chronic_dropout and not was_dropping:
            self.feed_to_memory({"event": "con_chronic_dropout",
                                  "note": "Cingulo-opercular network chronically dropping tasks — can't sustain engagement"})

        return {
            "task_maintenance": round(self.task_maintenance, 3),
            "sustained_engagement": round(self.sustained_engagement, 3),
            "set_shift_readiness": round(self.set_shift_readiness, 3),
            "task_duration": self.task_duration,
            "task_errors_caught": self.task_errors_caught,
            "chronic_dropout": self.chronic_dropout,
        }

    def _overnight(self):
        self.dropout_ticks = max(0, self.dropout_ticks - 7)
        self.chronic_dropout = self.dropout_ticks > 18
        self.task_duration = 0
        self.maintenance_history.clear()
        return {"overnight": "con_task_maintenance_reset"}
