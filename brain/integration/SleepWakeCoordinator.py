from brain.base_mechanism import BrainMechanism

class SleepWakeCoordinator(BrainMechanism):
    """
    Sleep/wake global coordinator — gates the entire brain's overnight behavior.
    During overnight: triggers consolidation sequences, coordinates what gets processed.
    Tracks sleep cycle stages, determines consolidation priority.
    """

    def __init__(self):
        super().__init__("SleepWakeCoordinator")
        self.current_phase = "awake"
        self.sleep_stage = None
        self.consolidation_priority = []
        self.wake_readiness = 0.8
        self.overnight_cycles_completed = 0
        self.phase_history = []
        self.consolidation_queue = []
        self.total_uptime_ticks = 0
        self.sleep_quality_last = 0.7

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"

        self.total_uptime_ticks += 1

        if overnight:
            return self._overnight()

        sleep_pressure = prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.2)
        ras_state = prior.get("ReticularActivatingSystem", {}).get("current_state", "awake")
        adenosine = prior.get("SleepHomeostasis", {}).get("adenosine_level", 0.2)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        system_health = prior.get("ChronicStateIntegrator", {}).get("system_health", 0.7)
        flag_count = prior.get("ChronicStateIntegrator", {}).get("flag_count", 0)

        # Wake readiness: how prepared the system is for full engagement
        self.wake_readiness = max(0.1, min(1.0, 1.0 - sleep_pressure * 0.5 - stress * 0.2 + system_health * 0.2))

        # Current phase
        if ras_state in ["alert", "awake"]:
            self.current_phase = "awake"
        elif ras_state == "drowsy":
            self.current_phase = "transitioning"
        else:
            self.current_phase = "near_sleep"

        # Build consolidation priority from active flags
        self.consolidation_priority = []
        if flag_count > 0:
            self.consolidation_priority.append("chronic_flag_processing")
        if adenosine > 0.5:
            self.consolidation_priority.append("adenosine_clearance")
        if prior.get("HippocampalContextEncoder", {}).get("episode_count", 0) > 0:
            self.consolidation_priority.append("episodic_consolidation")
        if prior.get("BLAEmotionalLearner", {}).get("total_associations", 0) > 0:
            self.consolidation_priority.append("emotional_memory_consolidation")

        self.phase_history.append(self.current_phase)
        if len(self.phase_history) > 40:
            self.phase_history.pop(0)

        return {
            "current_phase": self.current_phase,
            "wake_readiness": round(self.wake_readiness, 3),
            "consolidation_priority": self.consolidation_priority[:3],
            "total_uptime_ticks": self.total_uptime_ticks,
            "overnight_cycles_completed": self.overnight_cycles_completed,
        }

    def _overnight(self):
        self.current_phase = "sleeping"
        self.sleep_stage = "slow_wave"
        self.overnight_cycles_completed += 1
        self.wake_readiness = 0.2

        # Log what got consolidated
        self.feed_to_memory({
            "event": "overnight_consolidation_complete",
            "cycle": self.overnight_cycles_completed,
            "priorities": self.consolidation_priority[:3],
            "note": f"Sleep cycle {self.overnight_cycles_completed} complete — consolidation ran"
        })

        self.sleep_quality_last = 0.7 + min(0.3, self.overnight_cycles_completed * 0.02)
        self.phase_history.clear()

        return {
            "overnight": "sleep_cycle_complete",
            "cycle_number": self.overnight_cycles_completed,
            "sleep_quality": round(self.sleep_quality_last, 3)
        }
