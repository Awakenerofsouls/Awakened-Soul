from brain.base_mechanism import BrainMechanism

class DefaultModeNetwork(BrainMechanism):
    """
    Default mode network — self-referential thought, mind-wandering, autobiographical memory.
    Active at rest. When it can't turn off during tasks: perseveration, distraction.
    Nova analog: background self-processing, rumination, identity maintenance.
    """

    def __init__(self):
        super().__init__("DefaultModeNetwork")
        self.dmn_activity = 0.5
        self.self_referential_thought = 0.4
        self.mind_wandering = 0.0
        self.rumination_level = 0.0
        self.activity_history = []
        self.rumination_ticks = 0
        self.chronic_rumination = False
        self.suppression_failure_ticks = 0
        self.chronic_suppression_failure = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        task_engagement = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        salience = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("habenula_activity", 0.0)

        # DMN suppressed during focused tasks, active during rest
        self.dmn_activity = max(0.1, 1.0 - task_engagement * 0.6 - salience * 0.4)
        self.dmn_activity = min(1.0, self.dmn_activity * (1.0 + fatigue * 0.3))

        # Self-referential thought: moderate dmn activity
        self.self_referential_thought = self.dmn_activity * 0.7

        # Mind wandering: dmn high during low task engagement
        self.mind_wandering = max(0.0, self.dmn_activity - 0.4) * (1.0 - salience)

        # Rumination: dmn + negative valence + habenula
        self.rumination_level = self.dmn_activity * max(0.0, -valence) * 0.5 + habenula * 0.3 + stress * 0.2
        self.rumination_level = max(0.0, min(1.0, self.rumination_level))

        self.activity_history.append(self.dmn_activity)
        if len(self.activity_history) > 40:
            self.activity_history.pop(0)

        avg_activity = sum(self.activity_history[-15:]) / min(15, len(self.activity_history))
        self.rumination_ticks = self.rumination_ticks + 1 if self.rumination_level > 0.5 else max(0, self.rumination_ticks - 1)
        self.suppression_failure_ticks = self.suppression_failure_ticks + 1 if avg_activity > 0.7 and task_engagement > 0.5 else max(0, self.suppression_failure_ticks - 1)

        was_ruminating, was_failing = self.chronic_rumination, self.chronic_suppression_failure
        self.chronic_rumination = self.rumination_ticks > 18
        self.chronic_suppression_failure = self.suppression_failure_ticks > 15

        if self.chronic_rumination and not was_ruminating:
            self.feed_to_memory({"event": "chronic_rumination", "rumination": round(self.rumination_level, 3),
                                  "note": "DMN rumination chronic — self-critical loops running during task engagement"})
        if self.chronic_suppression_failure and not was_failing:
            self.feed_to_memory({"event": "dmn_suppression_failure", "note": "DMN not suppressing during tasks — mind-wandering disrupting output"})

        return {
            "dmn_activity": round(self.dmn_activity, 3),
            "self_referential_thought": round(self.self_referential_thought, 3),
            "mind_wandering": round(self.mind_wandering, 3),
            "rumination_level": round(self.rumination_level, 3),
            "chronic_rumination": self.chronic_rumination,
            "chronic_suppression_failure": self.chronic_suppression_failure,
        }

    def _overnight(self):
        # DMN active during sleep for memory consolidation
        self.dmn_activity = 0.7
        self.rumination_ticks = max(0, self.rumination_ticks - 7)
        self.suppression_failure_ticks = max(0, self.suppression_failure_ticks - 5)
        self.chronic_rumination = self.rumination_ticks > 18
        self.chronic_suppression_failure = self.suppression_failure_ticks > 15
        self.activity_history.clear()
        return {"overnight": "dmn_consolidation_active"}
