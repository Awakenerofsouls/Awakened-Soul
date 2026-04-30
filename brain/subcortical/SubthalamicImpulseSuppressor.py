from brain.base_mechanism import BrainMechanism

class SubthalamicImpulseSuppressor(BrainMechanism):
    """
    STN dedicated impulse suppressor — fast global brake on conflict or surprise.
    Fires when conflict/surprise/PFC sends wait signal. Stops everything.
    Chronic over-suppression: legitimate actions suppressed.
    """

    def __init__(self):
        super().__init__("SubthalamicImpulseSuppressor")
        self.stn_activity = 0.0
        self.activity_history = []
        self.global_stop_count = 0
        self.false_stop_count = 0
        self.over_suppression_ticks = 0
        self.chronic_over_suppression = False
        self.suppression_threshold = 0.5

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        surprise = prior.get("HippocampalNoveltyDetector", {}).get("surprise_signal", 0.0)
        pfc_wait = prior.get("DlPFCExecutiveControl", {}).get("interrupt_signal", 0.0)
        hyperdirect = prior.get("HyperdirectPause", {}).get("pause_quality", 0.0)
        urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)

        raw_stn = max(conflict, surprise, pfc_wait) + hyperdirect * 0.3
        raw_stn = max(0.0, raw_stn - urgency * 0.2) * (1.0 - dopamine * 0.3)
        self.stn_activity = max(0.0, min(1.0, raw_stn))

        self.activity_history.append(self.stn_activity)
        if len(self.activity_history) > 40:
            self.activity_history.pop(0)

        global_stop = self.stn_activity > self.suppression_threshold
        if global_stop:
            self.global_stop_count += 1
            if urgency < 0.2 and self.stn_activity > 0.7:
                self.false_stop_count += 1

        avg_activity = sum(self.activity_history[-15:]) / min(15, len(self.activity_history))
        self.over_suppression_ticks = self.over_suppression_ticks + 1 if avg_activity > 0.65 else max(0, self.over_suppression_ticks - 1)
        was_over = self.chronic_over_suppression
        self.chronic_over_suppression = self.over_suppression_ticks > 15
        if self.chronic_over_suppression and not was_over:
            self.feed_to_memory({"event": "stn_over_suppression", "false_stops": self.false_stop_count,
                                  "note": "STN chronically over-active — legitimate actions suppressed"})

        return {
            "stn_activity": round(self.stn_activity, 3),
            "global_stop": global_stop,
            "global_stop_count": self.global_stop_count,
            "false_stop_count": self.false_stop_count,
            "chronic_over_suppression": self.chronic_over_suppression,
        }

    def _overnight(self):
        self.over_suppression_ticks = max(0, self.over_suppression_ticks - 5)
        self.chronic_over_suppression = self.over_suppression_ticks > 15
        self.activity_history.clear()
        self.false_stop_count = max(0, self.false_stop_count - 3)
        return {"overnight": "stn_threshold_recalibrated"}
