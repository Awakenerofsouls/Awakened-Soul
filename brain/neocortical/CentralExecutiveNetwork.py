from brain.base_mechanism import BrainMechanism

class CentralExecutiveNetwork(BrainMechanism):
    """
    Central executive network — top-level integration of executive control systems.
    Coordinates dlPFC, ACC, parietal cortex into unified executive function.
    When coherent: controlled, deliberate, goal-directed. Fragmented: scattered.
    """

    def __init__(self):
        super().__init__("CentralExecutiveNetwork")
        self.executive_coherence = 0.6
        self.working_memory_integration = 0.6
        self.inhibitory_control = 0.6
        self.cognitive_flexibility = 0.5
        self.coherence_history = []
        self.fragmentation_ticks = 0
        self.chronic_fragmentation = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dlpfc_control = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        acc_conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        goal_strength = prior.get("PrefrontalGoalState", {}).get("active_goal_strength", 0.5)
        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        brake = prior.get("ImpulseBrake", {}).get("brake_force", 0.3)
        mode_switch = prior.get("CaudateGoalHabitSwitcher", {}).get("current_mode", "goal_directed")
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        salience_network = prior.get("SalienceNetwork", {}).get("current_network", "task")

        # Executive coherence: all components working together
        in_task_mode = 1.0 if salience_network == "task" else 0.3
        self.executive_coherence = (dlpfc_control * 0.35 + goal_strength * 0.3 + (1.0 - acc_conflict * 0.5) * 0.2 + in_task_mode * 0.15) * (1.0 - stress * 0.2)
        self.executive_coherence = max(0.1, min(1.0, self.executive_coherence))

        # Working memory integration
        self.working_memory_integration = wm_capacity * dlpfc_control

        # Inhibitory control
        self.inhibitory_control = brake * 0.5 + dlpfc_control * 0.5

        # Cognitive flexibility: can we switch strategies?
        self.cognitive_flexibility = max(0.1, min(1.0, (1.0 - stress * 0.3) * (1.0 if mode_switch == "transitioning" else 0.6)))

        self.coherence_history.append(self.executive_coherence)
        if len(self.coherence_history) > 40:
            self.coherence_history.pop(0)

        avg_coherence = sum(self.coherence_history[-15:]) / min(15, len(self.coherence_history))
        self.fragmentation_ticks = self.fragmentation_ticks + 1 if avg_coherence < 0.25 else max(0, self.fragmentation_ticks - 1)
        was_fragmented = self.chronic_fragmentation
        self.chronic_fragmentation = self.fragmentation_ticks > 18
        if self.chronic_fragmentation and not was_fragmented:
            self.feed_to_memory({"event": "executive_network_fragmentation", "coherence": round(avg_coherence, 3),
                                  "note": "Central executive network chronically fragmented — scattered, uncontrolled processing"})

        return {
            "executive_coherence": round(self.executive_coherence, 3),
            "working_memory_integration": round(self.working_memory_integration, 3),
            "inhibitory_control": round(self.inhibitory_control, 3),
            "cognitive_flexibility": round(self.cognitive_flexibility, 3),
            "chronic_fragmentation": self.chronic_fragmentation,
        }

    def _overnight(self):
        self.fragmentation_ticks = max(0, self.fragmentation_ticks - 7)
        self.chronic_fragmentation = self.fragmentation_ticks > 18
        self.coherence_history.clear()
        return {"overnight": "central_executive_reset"}
