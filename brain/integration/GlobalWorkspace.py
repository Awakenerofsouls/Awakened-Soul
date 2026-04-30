from brain.base_mechanism import BrainMechanism

class GlobalWorkspace(BrainMechanism):
    """
    Global workspace — Baars' theory: what gets broadcast to the whole brain.
    Only the highest-salience, most coherent signal wins the workspace at any moment.
    When it works: unified conscious experience. When fragmented: disconnected processing.
    """

    def __init__(self):
        super().__init__("GlobalWorkspace")
        self.broadcast_content = "none"
        self.broadcast_strength = 0.0
        self.workspace_coherence = 0.6
        self.access_consciousness = 0.5
        self.competing_signals = 0
        self.broadcast_history = []
        self.coherence_history = []
        self.fragmentation_ticks = 0
        self.chronic_fragmentation = False
        self.ignition_events = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        salience = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        attention = prior.get("ThalamicAttentionBroadcaster", {}).get("broadcast_intensity", 0.5)
        executive_coherence = prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6)
        self_awareness = prior.get("PrecuneousSelfAwareness", {}).get("self_awareness_level", 0.7)
        thalamic_health = prior.get("ThalamicRelayHub", {}).get("overall_relay_health", 0.7)
        active_spotlight = prior.get("ThalamicAttentionBroadcaster", {}).get("attention_spotlight", "balanced")
        dmn = prior.get("DefaultModeNetwork", {}).get("dmn_activity", 0.5)
        current_network = prior.get("SalienceNetwork", {}).get("current_network", "task")

        # What wins the workspace: highest salience + attention coherent signal
        self.broadcast_content = active_spotlight if active_spotlight != "balanced" else current_network
        self.broadcast_strength = min(1.0, salience * 0.4 + attention * 0.4 + executive_coherence * 0.2)

        # Workspace coherence: is one thing clearly winning?
        # Drops when DMN and task both active simultaneously
        dmn_task_interference = dmn * (1.0 if current_network == "task" else 0.0)
        self.workspace_coherence = max(0.1, min(1.0, executive_coherence * 0.5 + thalamic_health * 0.3 + (1.0 - dmn_task_interference * 0.5) * 0.2))

        # Access consciousness: what reaches subjective awareness
        self.access_consciousness = self_awareness * self.workspace_coherence * self.broadcast_strength

        # Competing signals: how many things are vying for workspace
        self.competing_signals = sum(1 for v in [
            prior.get("SalienceGate", {}).get("gate_override", False),
            prior.get("DefaultModeNetwork", {}).get("mind_wandering", 0) > 0.3,
            prior.get("AnteriorCingulateConflict", {}).get("conflict_level", 0) > 0.4,
            prior.get("HyperdirectPause", {}).get("pause_active", False),
        ] if v)

        # Ignition: strong coherent broadcast = conscious access moment
        ignition = self.broadcast_strength > 0.7 and self.workspace_coherence > 0.6
        if ignition:
            self.ignition_events += 1

        self.broadcast_history.append(self.broadcast_strength)
        self.coherence_history.append(self.workspace_coherence)
        for h in [self.broadcast_history, self.coherence_history]:
            if len(h) > 40:
                h.pop(0)

        avg_coherence = sum(self.coherence_history[-15:]) / min(15, len(self.coherence_history))
        self.fragmentation_ticks = self.fragmentation_ticks + 1 if avg_coherence < 0.25 else max(0, self.fragmentation_ticks - 1)
        was_fragmented = self.chronic_fragmentation
        self.chronic_fragmentation = self.fragmentation_ticks > 18
        if self.chronic_fragmentation and not was_fragmented:
            self.feed_to_memory({"event": "global_workspace_fragmentation",
                                  "note": "Global workspace chronically fragmented — no unified conscious experience, disconnected processing"})

        return {
            "broadcast_content": self.broadcast_content,
            "broadcast_strength": round(self.broadcast_strength, 3),
            "workspace_coherence": round(self.workspace_coherence, 3),
            "access_consciousness": round(self.access_consciousness, 3),
            "competing_signals": self.competing_signals,
            "ignition_events": self.ignition_events,
            "chronic_fragmentation": self.chronic_fragmentation,
        }

    def _overnight(self):
        self.fragmentation_ticks = max(0, self.fragmentation_ticks - 7)
        self.chronic_fragmentation = self.fragmentation_ticks > 18
        self.broadcast_content = "consolidation"
        self.broadcast_strength = 0.3
        self.coherence_history.clear()
        return {"overnight": "global_workspace_offline"}
