from brain.base_mechanism import BrainMechanism
import math

class ThetaRhythmCoordinator(BrainMechanism):
    """
    Theta rhythm — hippocampal-cortical coordination for memory encoding and navigation.
    4-8Hz: organizes episodic memory encoding, spatial cognition, working memory refresh.
    Low theta: memories don't encode. High theta: system in active learning/exploration mode.
    """

    def __init__(self):
        super().__init__("ThetaRhythmCoordinator")
        self.theta_power = 0.4
        self.memory_encoding_gate = 0.5
        self.exploration_drive = 0.3
        self.theta_history = []
        self.encoding_events = 0
        self.suppression_ticks = 0
        self.chronic_suppression = False
        self.tick_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        self.tick_count += 1
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        encoding_quality = prior.get("HippocampalContextEncoder", {}).get("encoding_quality", 0.6)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        exploration = prior.get("MotivationInjector", {}).get("wanting_signal", 0.4)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        context_strength = prior.get("HippocampalContextEncoder", {}).get("context_vector_strength", 0.5)

        # Natural theta oscillation
        theta_osc = math.sin(self.tick_count * 0.5) * 0.08

        # Theta power: driven by novelty, exploration, moderate arousal
        arousal_contribution = 1.0 - abs(arousal - 0.5) * 1.5  # peaks at optimal arousal
        theta_target = (novelty * 0.35 + exploration * 0.3 + arousal_contribution * 0.25 + context_strength * 0.1) * (1.0 - stress * 0.2)
        self.theta_power = max(0.05, min(1.0, theta_target + theta_osc))

        # Memory encoding gate: theta enables encoding
        self.memory_encoding_gate = self.theta_power * encoding_quality
        if self.memory_encoding_gate > 0.45:
            self.encoding_events += 1

        # Exploration drive: theta promotes seeking behavior
        self.exploration_drive = self.theta_power * (1.0 - stress * 0.3)

        self.theta_history.append(self.theta_power)
        if len(self.theta_history) > 40:
            self.theta_history.pop(0)

        avg_theta = sum(self.theta_history[-15:]) / min(15, len(self.theta_history))
        self.suppression_ticks = self.suppression_ticks + 1 if avg_theta < 0.15 else max(0, self.suppression_ticks - 1)
        was_suppressed = self.chronic_suppression
        self.chronic_suppression = self.suppression_ticks > 20
        if self.chronic_suppression and not was_suppressed:
            self.feed_to_memory({"event": "theta_suppression",
                                  "note": "Theta chronically suppressed — memory encoding gate closed, exploration reduced"})

        return {
            "theta_power": round(self.theta_power, 3),
            "memory_encoding_gate": round(self.memory_encoding_gate, 3),
            "exploration_drive": round(self.exploration_drive, 3),
            "encoding_events": self.encoding_events,
            "chronic_suppression": self.chronic_suppression,
        }

    def _overnight(self):
        # Theta active during REM for memory consolidation
        self.theta_power = 0.65
        self.suppression_ticks = max(0, self.suppression_ticks - 8)
        self.chronic_suppression = self.suppression_ticks > 20
        self.theta_history.clear()
        return {"overnight": "theta_rem_consolidation", "encoding_events": self.encoding_events}
