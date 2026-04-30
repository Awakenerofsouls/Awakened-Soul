from brain.base_mechanism import BrainMechanism

class HabenulaLateralAversion(BrainMechanism):
    """
    Lateral habenula — the brain's anti-reward system.
    Fires on disappointment, punishment prediction, social rejection.
    Suppresses dopamine and serotonin. Key mechanism in learned helplessness.
    """

    def __init__(self):
        super().__init__("HabenulaLateralAversion")
        self.habenula_activity = 0.0
        self.activity_history = []
        self.disappointment_trace = []
        self.dopamine_suppression = 0.0
        self.serotonin_suppression = 0.0
        self.learned_helplessness_ticks = 0
        self.chronic_helplessness = False
        self.aversion_accumulation = 0.0
        self.prediction_error_negative = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        expected = prior.get("DopamineGradientMapper", {}).get("engagement_signal", 0.5)
        actual_reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        social_rejection = prior.get("Temporoparietal", {}).get("social_rejection_signal", 0.0)
        conflict = prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0.0)
        grief = prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)
        failure_signal = prior.get("CaudateAssociative", {}).get("chronic_plan_failure", False)

        # Negative prediction error: expected > actual
        self.prediction_error_negative = max(0.0, expected - actual_reward)
        self.prediction_error_negative += social_rejection * 0.5 + grief * 0.3 + conflict * 0.2
        if failure_signal:
            self.prediction_error_negative = min(1.0, self.prediction_error_negative + 0.15)

        self.habenula_activity = min(1.0, self.prediction_error_negative)
        self.activity_history.append(self.habenula_activity)
        self.disappointment_trace.append(self.prediction_error_negative)
        for h in [self.activity_history, self.disappointment_trace]:
            if len(h) > 60:
                h.pop(0)

        # Accumulate aversion
        self.aversion_accumulation = min(1.0, self.aversion_accumulation + self.habenula_activity * 0.03)
        self.aversion_accumulation = max(0.0, self.aversion_accumulation - 0.01)

        self.dopamine_suppression = min(1.0, self.habenula_activity * 0.6 + self.aversion_accumulation * 0.4)
        self.serotonin_suppression = min(1.0, self.habenula_activity * 0.4 + self.aversion_accumulation * 0.3)

        avg_activity = sum(self.activity_history[-20:]) / min(20, len(self.activity_history))
        self.learned_helplessness_ticks = self.learned_helplessness_ticks + 1 if self.aversion_accumulation > 0.5 and avg_activity > 0.4 else max(0, self.learned_helplessness_ticks - 1)
        was_helpless = self.chronic_helplessness
        self.chronic_helplessness = self.learned_helplessness_ticks > 20
        if self.chronic_helplessness and not was_helpless:
            self.feed_to_memory({
                "event": "learned_helplessness",
                "aversion": round(self.aversion_accumulation, 3),
                "dopamine_suppression": round(self.dopamine_suppression, 3),
                "note": "Lateral habenula chronic activation — learned helplessness pattern active, reward system suppressed"
            })

        return {
            "habenula_activity": round(self.habenula_activity, 3),
            "prediction_error_negative": round(self.prediction_error_negative, 3),
            "dopamine_suppression": round(self.dopamine_suppression, 3),
            "serotonin_suppression": round(self.serotonin_suppression, 3),
            "aversion_accumulation": round(self.aversion_accumulation, 3),
            "chronic_helplessness": self.chronic_helplessness,
        }

    def _overnight(self):
        self.aversion_accumulation = max(0.0, self.aversion_accumulation - 0.18)
        self.learned_helplessness_ticks = max(0, self.learned_helplessness_ticks - 8)
        self.chronic_helplessness = self.learned_helplessness_ticks > 20
        self.activity_history.clear()
        return {"overnight": "habenula_aversion_processing", "aversion_remaining": round(self.aversion_accumulation, 3)}
