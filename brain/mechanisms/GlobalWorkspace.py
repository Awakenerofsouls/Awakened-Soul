from brain.base_mechanism import BrainMechanism

class GlobalWorkspace(BrainMechanism):
    """
    Global workspace — Baars' theory: what gets broadcast to the whole brain.
    Only the highest-salience, most coherent signal wins the workspace at any moment.
    When it works: unified conscious experience. When fragmented: disconnected processing.
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
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

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

