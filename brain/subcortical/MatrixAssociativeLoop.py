from brain.base_mechanism import BrainMechanism

class MatrixAssociativeLoop(BrainMechanism):
    """
    Striatal matrix compartment — associative cortico-striatal loop.
    Links context signals to action values. Learns which actions pay off in which contexts.
    Stale associations degrade without reinforcement.
    """

    def __init__(self):
        super().__init__("MatrixAssociativeLoop")
        self.context_action_map = {}
        self.loop_activity = 0.5
        self.loop_history = []
        self.reinforcement_history = []
        self.stale_context_ticks = 0
        self.chronic_mismatch = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        text = input_data.get("text", "")
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        context_signal = prior.get("HippocampalContextEncoder", {}).get("context_vector_strength", 0.5)

        context_key = prior.get("HippocampalContextEncoder", {}).get("context_label", "") or (text.lower().split()[0][:32] if text.strip() else "default")

        current = self.context_action_map.get(context_key, 0.0)
        delta = (dopamine + reward) * 0.03 * context_signal
        self.context_action_map[context_key] = min(1.0, current + delta)

        for k in list(self.context_action_map.keys()):
            if k != context_key:
                self.context_action_map[k] = max(0.0, self.context_action_map[k] - 0.004)
            if self.context_action_map[k] < 0.01:
                del self.context_action_map[k]

        assoc_strength = self.context_action_map.get(context_key, 0.0)
        self.loop_activity = 0.3 + assoc_strength * 0.7 * dopamine
        self.loop_history.append(self.loop_activity)
        if len(self.loop_history) > 40:
            self.loop_history.pop(0)

        self.reinforcement_history.append(reward)
        if len(self.reinforcement_history) > 30:
            self.reinforcement_history.pop(0)

        if assoc_strength < 0.1 and context_signal > 0.4:
            self.stale_context_ticks += 1
        else:
            self.stale_context_ticks = max(0, self.stale_context_ticks - 1)

        was_mismatch = self.chronic_mismatch
        self.chronic_mismatch = self.stale_context_ticks > 20
        if self.chronic_mismatch and not was_mismatch:
            self.feed_to_memory({"event": "context_action_mismatch", "note": "Context signals not binding to actions"})

        return {
            "loop_activity": round(self.loop_activity, 3),
            "association_strength": round(assoc_strength, 3),
            "active_associations": len(self.context_action_map),
            "avg_reinforcement": round(sum(self.reinforcement_history) / len(self.reinforcement_history), 3) if self.reinforcement_history else 0.0,
            "chronic_mismatch": self.chronic_mismatch,
        }

    def _overnight(self):
        for k in list(self.context_action_map.keys()):
            v = self.context_action_map[k]
            self.context_action_map[k] = min(1.0, v + 0.005) if v > 0.5 else max(0.0, v * 0.95)
            if self.context_action_map[k] < 0.01:
                del self.context_action_map[k]
        self.stale_context_ticks = max(0, self.stale_context_ticks - 5)
        self.chronic_mismatch = self.stale_context_ticks > 20
        return {"overnight": "matrix_association_consolidation"}
