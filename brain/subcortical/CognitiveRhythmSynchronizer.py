from brain.base_mechanism import BrainMechanism
import math

class CognitiveRhythmSynchronizer(BrainMechanism):
    """
    Thalamo-cortical rhythms — synchronizes cognitive oscillations across regions.
    Alpha suppresses noise. Beta holds current state. Gamma binds features.
    Desync = fragmented thinking. Over-sync = rigid, stuck in loops.
    """

    def __init__(self):
        super().__init__("CognitiveRhythmSynchronizer")
        self.alpha_power = 0.5
        self.beta_power = 0.5
        self.gamma_power = 0.3
        self.alpha_history = []
        self.beta_history = []
        self.gamma_history = []
        self.sync_quality = 0.6
        self.desync_ticks = 0
        self.over_sync_ticks = 0
        self.chronic_desync = False
        self.chronic_over_sync = False
        self.tick_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        self.tick_count += 1
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        cortical_excitability = prior.get("IntralaminarArousalFeed", {}).get("cortical_excitability", 0.5)
        cognitive_load = prior.get("DlPFCExecutiveControl", {}).get("cognitive_load", 0.4)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        salience = prior.get("ThalamicSalienceFilter", {}).get("raw_salience", 0.3)
        timing_quality = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)

        alpha_target = max(0.1, 0.8 - arousal * 0.6 - salience * 0.4)
        self.alpha_power += (alpha_target - self.alpha_power) * 0.12
        self.alpha_power = max(0.0, min(1.0, self.alpha_power))

        beta_target = 0.2 + cognitive_load * 0.5 + stress * 0.2
        self.beta_power += (beta_target - self.beta_power) * 0.1
        self.beta_power = max(0.0, min(1.0, self.beta_power))

        gamma_target = salience * 0.5 + cortical_excitability * 0.3 + timing_quality * 0.2
        gamma_osc = math.sin(self.tick_count * 0.3) * 0.05
        self.gamma_power += (gamma_target - self.gamma_power) * 0.15 + gamma_osc
        self.gamma_power = max(0.0, min(1.0, self.gamma_power))

        for band, power in [("alpha", self.alpha_power), ("beta", self.beta_power), ("gamma", self.gamma_power)]:
            hist = getattr(self, f"{band}_history")
            hist.append(power)
            if len(hist) > 40:
                hist.pop(0)

        balance = 1.0 - abs(self.alpha_power - 0.3) - abs(self.beta_power - 0.4) - abs(self.gamma_power - 0.3)
        self.sync_quality = max(0.0, min(1.0, balance * timing_quality))

        self.desync_ticks = self.desync_ticks + 1 if self.sync_quality < 0.2 else max(0, self.desync_ticks - 1)
        self.over_sync_ticks = self.over_sync_ticks + 1 if self.beta_power > 0.85 else max(0, self.over_sync_ticks - 1)

        was_desync, was_over = self.chronic_desync, self.chronic_over_sync
        self.chronic_desync = self.desync_ticks > 15
        self.chronic_over_sync = self.over_sync_ticks > 15

        if self.chronic_desync and not was_desync:
            self.feed_to_memory({"event": "thalamo_cortical_desync", "sync_quality": round(self.sync_quality, 3),
                                  "note": "Cognitive rhythms desynchronized — fragmented thinking"})
        if self.chronic_over_sync and not was_over:
            self.feed_to_memory({"event": "beta_over_sync", "beta": round(self.beta_power, 3),
                                  "note": "Beta locked high — rigid cognition, stuck in loops"})

        return {
            "alpha_power": round(self.alpha_power, 3),
            "beta_power": round(self.beta_power, 3),
            "gamma_power": round(self.gamma_power, 3),
            "sync_quality": round(self.sync_quality, 3),
            "chronic_desync": self.chronic_desync,
            "chronic_over_sync": self.chronic_over_sync,
        }

    def _overnight(self):
        self.alpha_power = 0.7
        self.beta_power = 0.2
        self.gamma_power = 0.1
        self.desync_ticks = max(0, self.desync_ticks - 8)
        self.over_sync_ticks = max(0, self.over_sync_ticks - 6)
        self.chronic_desync = self.desync_ticks > 15
        self.chronic_over_sync = self.over_sync_ticks > 15
        return {"overnight": "rhythm_reset_sleep_state"}
