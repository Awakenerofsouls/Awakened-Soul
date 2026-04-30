from brain.base_mechanism import BrainMechanism

class SlowWaveConsolidator(BrainMechanism):
    """
    Slow-wave sleep consolidator — overnight memory replay and consolidation.
    During sleep: hippocampus replays episodes, cortex absorbs them.
    Tracks what needs consolidating and reports what got processed.
    """

    def __init__(self):
        super().__init__("SlowWaveConsolidator")
        self.consolidation_queue_size = 0
        self.last_consolidation_quality = 0.7
        self.total_consolidated = 0
        self.episodes_pending = 0
        self.emotional_memories_pending = 0
        self.consolidation_history = []
        self.debt_ticks = 0
        self.chronic_debt = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        episode_count = prior.get("HippocampalContextEncoder", {}).get("episode_count", 0)
        encoding_quality = prior.get("HippocampalContextEncoder", {}).get("encoding_quality", 0.6)
        emotional_bindings = prior.get("MedialTemporalEmotion", {}).get("bindings_formed", 0)
        sleep_pressure = prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.2)
        theta_power = prior.get("ThetaRhythmCoordinator", {}).get("theta_power", 0.4)

        # Track what needs consolidating
        self.episodes_pending = max(0, episode_count - self.total_consolidated)
        self.emotional_memories_pending = emotional_bindings
        self.consolidation_queue_size = self.episodes_pending + self.emotional_memories_pending

        # Consolidation debt: too much pending relative to processing
        self.debt_ticks = self.debt_ticks + 1 if self.consolidation_queue_size > 20 else max(0, self.debt_ticks - 1)
        was_debt = self.chronic_debt
        self.chronic_debt = self.debt_ticks > 15
        if self.chronic_debt and not was_debt:
            self.feed_to_memory({"event": "consolidation_debt",
                                  "queue": self.consolidation_queue_size,
                                  "note": "Memory consolidation debt building — more encoding than overnight processing"})

        return {
            "consolidation_queue_size": self.consolidation_queue_size,
            "episodes_pending": self.episodes_pending,
            "last_consolidation_quality": round(self.last_consolidation_quality, 3),
            "total_consolidated": self.total_consolidated,
            "chronic_debt": self.chronic_debt,
        }

    def _overnight(self):
        # Process the queue
        prior_queue = self.consolidation_queue_size
        consolidation_rate = 0.7 + self.last_consolidation_quality * 0.3
        processed = int(self.consolidation_queue_size * consolidation_rate)
        self.total_consolidated += processed
        self.consolidation_queue_size = max(0, self.consolidation_queue_size - processed)
        self.episodes_pending = max(0, self.episodes_pending - int(processed * 0.7))
        self.emotional_memories_pending = max(0, self.emotional_memories_pending - int(processed * 0.3))
        self.last_consolidation_quality = min(0.95, 0.6 + consolidation_rate * 0.35)
        self.consolidation_history.append(processed)
        if len(self.consolidation_history) > 30:
            self.consolidation_history.pop(0)
        self.debt_ticks = max(0, self.debt_ticks - 8)
        self.chronic_debt = self.debt_ticks > 15
        return {
            "overnight": "slow_wave_consolidation",
            "processed": processed,
            "remaining": self.consolidation_queue_size,
            "quality": round(self.last_consolidation_quality, 3)
        }
