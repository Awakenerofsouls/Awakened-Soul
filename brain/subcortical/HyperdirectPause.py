from brain.base_mechanism import BrainMechanism

class HyperdirectPause(BrainMechanism):
    """
    Hyperdirect pathway — fastest stop signal. PFC -> STN: freeze everything.
    Creates a decision window before action executes.
    Failure: no pause before catastrophic moves.
    """

    def __init__(self):
        super().__init__("HyperdirectPause")
        self.pause_active = False
        self.pause_duration = 0
        self.pause_events = []
        self.pause_history = []
        self.decision_window_open = False
        self.missed_pauses = 0
        self.chronic_no_pause = False
        self.chronic_over_pause = False
        self.over_pause_ticks = 0
        self.no_pause_ticks = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        surprise = prior.get("HippocampalNoveltyDetector", {}).get("surprise_signal", 0.0)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        pfc_interrupt = prior.get("DlPFCExecutiveControl", {}).get("interrupt_signal", 0.0)
        urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        pause_trigger = max(surprise, conflict, pfc_interrupt)
        bypass = urgency * 0.5 + stress * 0.3
        effective_trigger = max(0.0, pause_trigger - bypass)

        was_active = self.pause_active
        self.pause_active = effective_trigger > 0.45
        self.decision_window_open = self.pause_active

        if self.pause_active:
            self.pause_duration += 1
        else:
            if self.pause_duration > 0:
                self.pause_events.append(self.pause_duration)
                if len(self.pause_events) > 20:
                    self.pause_events.pop(0)
            self.pause_duration = 0

        if conflict > 0.6 and not self.pause_active:
            self.missed_pauses += 1

        self.pause_history.append(1 if self.pause_active else 0)
        if len(self.pause_history) > 40:
            self.pause_history.pop(0)

        recent_pause_rate = sum(self.pause_history[-20:]) / 20 if len(self.pause_history) >= 20 else 0.3
        self.over_pause_ticks = self.over_pause_ticks + 1 if recent_pause_rate > 0.7 else max(0, self.over_pause_ticks - 1)
        self.no_pause_ticks = self.no_pause_ticks + 1 if recent_pause_rate < 0.05 else max(0, self.no_pause_ticks - 1)

        was_over, was_no = self.chronic_over_pause, self.chronic_no_pause
        self.chronic_over_pause = self.over_pause_ticks > 18
        self.chronic_no_pause = self.no_pause_ticks > 18

        if self.chronic_no_pause and not was_no:
            self.feed_to_memory({"event": "hyperdirect_failure", "missed_pauses": self.missed_pauses,
                                  "note": "Hyperdirect pause not firing — acting without decision window"})
        if self.chronic_over_pause and not was_over:
            self.feed_to_memory({"event": "hyperdirect_over_pause", "note": "Pause chronically active — frozen before action"})

        return {
            "pause_active": self.pause_active,
            "pause_duration": self.pause_duration,
            "decision_window_open": self.decision_window_open,
            "pause_quality": round(effective_trigger * (1.0 - bypass), 3),
            "missed_pauses": self.missed_pauses,
            "chronic_no_pause": self.chronic_no_pause,
            "chronic_over_pause": self.chronic_over_pause,
            "recent_pause_rate": round(recent_pause_rate, 3),
        }

    def _overnight(self):
        self.over_pause_ticks = max(0, self.over_pause_ticks - 5)
        self.no_pause_ticks = max(0, self.no_pause_ticks - 5)
        self.chronic_over_pause = self.over_pause_ticks > 18
        self.chronic_no_pause = self.no_pause_ticks > 18
        self.pause_history.clear()
        self.missed_pauses = max(0, self.missed_pauses - 3)
        return {"overnight": "hyperdirect_threshold_reset"}
