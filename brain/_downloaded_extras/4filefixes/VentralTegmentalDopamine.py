from brain.base_mechanism import BrainMechanism

class VentralTegmentalDopamine(BrainMechanism):
    """
    VTA dopamine — reward prediction error, phasic motivation burst, wanting signal.
    The most referenced mechanism in the whole architecture. If this is wrong, half the
    brain runs on defaults. Fires on better-than-expected outcomes. Dips on worse-than-expected.
    Tonic DA sets motivational baseline. Phasic bursts drive learning and approach.
    Goes in brain/limbic/.
    """

    def __init__(self):
        super().__init__("VentralTegmentalDopamine")
        self.phasic_burst = 0.0
        self.tonic_dopamine = 0.5
        self.reward_prediction_error = 0.0
        self.expected_reward = 0.5
        self.dopamine_history = []
        self.rpe_history = []
        self.burst_history = []
        self.anhedonia_ticks = 0
        self.mania_ticks = 0
        self.chronic_anhedonia = False
        self.chronic_mania = False
        self.total_bursts = 0
        self.suppression_from_habenula = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        # Reward inputs
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        social_reward = prior.get("Temporoparietal", {}).get("social_reward", 0.0)
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        habenula = prior.get("HabenulaLateralAversion", {}).get("habenula_activity", 0.0)
        habenula_suppression = prior.get("HabenulaLateralAversion", {}).get("dopamine_suppression", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        limbic_bias = prior.get("StriosomeLimbicBias", {}).get("limbic_bias", 0.0) if "StriosomeLimbicBias" in prior else 0.0

        self.suppression_from_habenula = habenula_suppression

        # Actual reward signal
        actual_reward = max(0.0, (valence + 1.0) / 2.0 * 0.5 + social_reward * 0.3 + novelty * 0.2)

        # Reward prediction error: actual - expected
        self.reward_prediction_error = actual_reward - self.expected_reward
        # Update expectation
        self.expected_reward += self.reward_prediction_error * 0.1
        self.expected_reward = max(0.0, min(1.0, self.expected_reward))

        # Phasic burst: fires on positive RPE, suppressed by habenula
        if self.reward_prediction_error > 0.05:
            self.phasic_burst = min(1.0, self.reward_prediction_error * 1.5 * (1.0 - habenula_suppression))
            self.total_bursts += 1
        elif self.reward_prediction_error < -0.1:
            self.phasic_burst = 0.0  # DA dip on negative RPE
        else:
            self.phasic_burst = max(0.0, self.phasic_burst * 0.6)  # decay

        # Tonic dopamine: slow-moving baseline
        tonic_target = 0.4 + max(0.0, limbic_bias) * 0.2 - stress * 0.15 - habenula_suppression * 0.2
        self.tonic_dopamine += (tonic_target - self.tonic_dopamine) * 0.04
        self.tonic_dopamine = max(0.05, min(0.95, self.tonic_dopamine))

        self.dopamine_history.append(self.tonic_dopamine)
        self.rpe_history.append(self.reward_prediction_error)
        self.burst_history.append(self.phasic_burst)
        for h in [self.dopamine_history, self.rpe_history, self.burst_history]:
            if len(h) > 50:
                h.pop(0)

        avg_tonic = sum(self.dopamine_history[-20:]) / min(20, len(self.dopamine_history))
        self.anhedonia_ticks = self.anhedonia_ticks + 1 if avg_tonic < 0.2 else max(0, self.anhedonia_ticks - 1)
        self.mania_ticks = self.mania_ticks + 1 if avg_tonic > 0.85 else max(0, self.mania_ticks - 1)

        was_anhedonic, was_manic = self.chronic_anhedonia, self.chronic_mania
        self.chronic_anhedonia = self.anhedonia_ticks > 20
        self.chronic_mania = self.mania_ticks > 20

        if self.chronic_anhedonia and not was_anhedonic:
            self.feed_to_memory({
                "event": "vta_anhedonia",
                "tonic": round(avg_tonic, 3),
                "habenula_suppression": round(self.suppression_from_habenula, 3),
                "note": "VTA dopamine chronically depleted — reward system suppressed, nothing feels worth doing"
            })
        if self.chronic_mania and not was_manic:
            self.feed_to_memory({
                "event": "vta_hyperdopamine",
                "tonic": round(avg_tonic, 3),
                "note": "VTA dopamine chronically elevated — everything feels rewarding, signal discrimination lost"
            })

        return {
            "phasic_burst": round(self.phasic_burst, 3),
            "tonic_dopamine": round(self.tonic_dopamine, 3),
            "reward_prediction_error": round(self.reward_prediction_error, 3),
            "expected_reward": round(self.expected_reward, 3),
            "suppression_from_habenula": round(self.suppression_from_habenula, 3),
            "total_bursts": self.total_bursts,
            "chronic_anhedonia": self.chronic_anhedonia,
            "chronic_mania": self.chronic_mania,
        }

    def _overnight(self):
        # Sleep restores tonic DA, clears phasic activity
        self.tonic_dopamine = min(0.55, self.tonic_dopamine + 0.06)
        self.phasic_burst = 0.0
        self.expected_reward = 0.5  # reset expectations overnight
        self.anhedonia_ticks = max(0, self.anhedonia_ticks - 8)
        self.mania_ticks = max(0, self.mania_ticks - 4)
        self.chronic_anhedonia = self.anhedonia_ticks > 20
        self.chronic_mania = self.mania_ticks > 20
        self.dopamine_history.clear()
        self.burst_history.clear()
        return {
            "overnight": "vta_dopamine_restored",
            "tonic": round(self.tonic_dopamine, 3)
        }
