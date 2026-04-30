from brain.base_mechanism import BrainMechanism

class PrefrontalWorkingMemoryBuffer(BrainMechanism):
    """
    PFC working memory buffer — holds active items for manipulation.
    Not storage: manipulation. Rehearsal, transformation, comparison.
    Full buffer: can't take in new information. Empty: no material to work with.
    """

    def __init__(self):
        super().__init__("PrefrontalWorkingMemoryBuffer")
        self.buffer_contents = []
        self.buffer_load = 0.0
        self.buffer_capacity = 7
        self.manipulation_quality = 0.6
        self.load_history = []
        self.overflow_count = 0
        self.underload_ticks = 0
        self.overflow_ticks = 0
        self.chronic_overflow = False
        self.chronic_underload = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        wm_capacity = prior.get("DlPFCExecutiveControl", {}).get("working_memory_capacity", 0.7)
        control = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fatigue = prior.get("SubstantiaNigraDopamine", {}).get("fatigue_accumulation", 0.0)

        # Effective capacity under current conditions
        effective_capacity = max(1, int(self.buffer_capacity * wm_capacity * (1.0 - stress * 0.3)))

        # Load buffer with current text items
        words = text.split()
        new_items = words[:effective_capacity]
        self.buffer_contents = new_items
        self.buffer_load = len(self.buffer_contents) / self.buffer_capacity

        if len(words) > effective_capacity:
            self.overflow_count += 1

        # Manipulation quality: how well contents can be worked with
        self.manipulation_quality = (control * 0.4 + dopamine * 0.3 + wm_capacity * 0.3) * (1.0 - fatigue * 0.2) * (1.0 - stress * 0.15)
        self.manipulation_quality = max(0.1, min(1.0, self.manipulation_quality))

        self.load_history.append(self.buffer_load)
        if len(self.load_history) > 40:
            self.load_history.pop(0)

        avg_load = sum(self.load_history[-15:]) / min(15, len(self.load_history))
        self.overflow_ticks = self.overflow_ticks + 1 if avg_load > 0.85 else max(0, self.overflow_ticks - 1)
        self.underload_ticks = self.underload_ticks + 1 if avg_load < 0.1 else max(0, self.underload_ticks - 1)

        was_over, was_under = self.chronic_overflow, self.chronic_underload
        self.chronic_overflow = self.overflow_ticks > 18
        self.chronic_underload = self.underload_ticks > 18

        if self.chronic_overflow and not was_over:
            self.feed_to_memory({"event": "wm_overflow", "overflow_count": self.overflow_count,
                                  "note": "Working memory buffer chronically overflowing — new info can't get in"})
        if self.chronic_underload and not was_under:
            self.feed_to_memory({"event": "wm_underload",
                                  "note": "Working memory chronically empty — nothing to manipulate or work with"})

        return {
            "buffer_load": round(self.buffer_load, 3),
            "buffer_item_count": len(self.buffer_contents),
            "effective_capacity": effective_capacity,
            "manipulation_quality": round(self.manipulation_quality, 3),
            "overflow_count": self.overflow_count,
            "chronic_overflow": self.chronic_overflow,
            "chronic_underload": self.chronic_underload,
        }

    def _overnight(self):
        self.buffer_contents.clear()
        self.buffer_load = 0.0
        self.overflow_ticks = max(0, self.overflow_ticks - 6)
        self.underload_ticks = max(0, self.underload_ticks - 4)
        self.chronic_overflow = self.overflow_ticks > 18
        self.chronic_underload = self.underload_ticks > 18
        self.load_history.clear()
        return {"overnight": "working_memory_buffer_cleared"}
