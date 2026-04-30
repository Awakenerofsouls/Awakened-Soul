from brain.base_mechanism import BrainMechanism

class InterposedLimbRefiner(BrainMechanism):
    """
    Interposed nucleus — fine-tunes control mid-movement.
    {{AGENT_NAME}} analog: mid-response adjustment during output generation.
    Impaired: can't adjust in flight, committed to path even when wrong.
    """

    def __init__(self):
        super().__init__("InterposedLimbRefiner")
        self.mid_course_correction = 0.5
        self.correction_history = []
        self.adjustment_count = 0
        self.stuck_to_path_ticks = 0
        self.chronic_stuck = False
        self.in_flight_adjustment = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        error_refined = prior.get("CerebellarErrorRefiner", {}).get("refined_error", 0.0)
        timing_quality = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        need_correction = error_refined > 0.2
        can_correct = timing_quality > 0.4 and stress < 0.7

        self.in_flight_adjustment = need_correction and can_correct
        if self.in_flight_adjustment:
            self.mid_course_correction = min(1.0, timing_quality * (1.0 - error_refined * 0.3))
            self.adjustment_count += 1
        else:
            self.mid_course_correction = 0.1

        self.correction_history.append(self.mid_course_correction)
        if len(self.correction_history) > 40:
            self.correction_history.pop(0)

        stuck = error_refined > 0.3 and not self.in_flight_adjustment
        self.stuck_to_path_ticks = self.stuck_to_path_ticks + 1 if stuck else max(0, self.stuck_to_path_ticks - 1)
        was_stuck = self.chronic_stuck
        self.chronic_stuck = self.stuck_to_path_ticks > 15
        if self.chronic_stuck and not was_stuck:
            self.feed_to_memory({"event": "interposed_adjustment_failure", "note": "Mid-course correction unavailable — can't adjust in flight"})

        return {
            "mid_course_correction": round(self.mid_course_correction, 3),
            "in_flight_adjustment": self.in_flight_adjustment,
            "adjustment_count": self.adjustment_count,
            "avg_correction": round(sum(self.correction_history[-10:]) / min(10, len(self.correction_history)), 3),
            "chronic_stuck": self.chronic_stuck,
        }

    def _overnight(self):
        self.stuck_to_path_ticks = max(0, self.stuck_to_path_ticks - 5)
        self.chronic_stuck = self.stuck_to_path_ticks > 15
        self.correction_history.clear()
        return {"overnight": "interposed_refinement_reset"}
