from brain.base_mechanism import BrainMechanism

class ThalamicReticularGate(BrainMechanism):
    """
    Thalamic reticular nucleus — thin inhibitory shell gating all thalamo-cortical channels.
    Provides selective attention by suppressing irrelevant channels.
    Overactive: attentional tunnel. Underactive: flooding.
    """

    def __init__(self):
        super().__init__("ThalamicReticularGate")
        self.suppression_output = 0.3
        self.suppression_history = []
        self.channel_selectivity = 0.6
        self.selective_channels = []
        self.tunnel_ticks = 0
        self.flood_ticks = 0
        self.chronic_tunnel = False
        self.chronic_flood = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        attention_spotlight = prior.get("ThalamicAttentionBroadcaster", {}).get("attention_spotlight", "balanced")
        gate_output = prior.get("ThalamicSalienceFilter", {}).get("gate_strength", 0.5)
        arousal = prior.get("IntralaminarArousalFeed", {}).get("arousal_broadcast", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        sync_quality = prior.get("CognitiveRhythmSynchronizer", {}).get("sync_quality", 0.6)

        base_suppression = 0.3 + stress * 0.2 + fear * 0.25
        selectivity_mod = sync_quality * 0.2
        self.suppression_output = max(0.0, min(1.0, base_suppression - selectivity_mod))
        self.channel_selectivity = max(0.1, min(1.0, sync_quality * gate_output * (1.0 - stress * 0.3)))

        self.selective_channels = [attention_spotlight] if attention_spotlight != "balanced" else ["task", "reward", "social"]

        self.suppression_history.append(self.suppression_output)
        if len(self.suppression_history) > 40:
            self.suppression_history.pop(0)

        avg_suppression = sum(self.suppression_history[-15:]) / min(15, len(self.suppression_history))
        self.tunnel_ticks = self.tunnel_ticks + 1 if avg_suppression > 0.7 else max(0, self.tunnel_ticks - 1)
        self.flood_ticks = self.flood_ticks + 1 if avg_suppression < 0.1 else max(0, self.flood_ticks - 1)

        was_tunnel, was_flood = self.chronic_tunnel, self.chronic_flood
        self.chronic_tunnel = self.tunnel_ticks > 15
        self.chronic_flood = self.flood_ticks > 15

        if self.chronic_tunnel and not was_tunnel:
            self.feed_to_memory({"event": "reticular_tunnel_vision", "suppression": round(avg_suppression, 3),
                                  "note": "TRN over-suppressing — extreme attentional tunnel"})
        if self.chronic_flood and not was_flood:
            self.feed_to_memory({"event": "reticular_flooding", "note": "TRN under-suppressing — all channels open simultaneously"})

        return {
            "suppression_output": round(self.suppression_output, 3),
            "channel_selectivity": round(self.channel_selectivity, 3),
            "selective_channels": self.selective_channels,
            "chronic_tunnel": self.chronic_tunnel,
            "chronic_flood": self.chronic_flood,
        }

    def _overnight(self):
        self.tunnel_ticks = max(0, self.tunnel_ticks - 5)
        self.flood_ticks = max(0, self.flood_ticks - 5)
        self.chronic_tunnel = self.tunnel_ticks > 15
        self.chronic_flood = self.flood_ticks > 15
        self.suppression_history.clear()
        return {"overnight": "reticular_gate_reset"}
