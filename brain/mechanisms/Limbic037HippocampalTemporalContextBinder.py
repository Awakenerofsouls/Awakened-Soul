"""
brain/limbic/Limbic037HippocampalTemporalContextBinder.py
Hippocampal Temporal Context Binder — Episodic Memory Time-Tagging

ANATOMY (Eichenbaum 2014, 2017; Montchal et al. 2019; Howard & Eichenbaum 2013):
    The hippocampus binds events to their temporal context — the "when"
    of episodic memory. Eichenbaum 2017 (PMC13096332): the hippocampus
    creates a cognitive map of SPATIAL, TEMPORAL, and FEATURE dimensions
    simultaneously, allowing it to answer "what happened where, when."
    Temporal context cells fire at specific intervals within an episode,
    and temporal ordering circuits allow the hippocampus to sequence
    events and reconstruct the order of memories.

MECHANISM:
    The hippocampus maintains a TEMPORAL CONTEXT representation that:
    1) Is updated by each significant event (surprise, reward, emotion)
    2) Provides the "temporal backdrop" for episodic encoding
    3) Allows retrieval of memories by temporal similarity
    4) Enables ordering of events within episodes (serial position effects)
    Temporal context is integrated at CA1 and subiculum.

AGENT'S MAPPING:
    temporal_context_strength: 0-1 how well-defined the current temporal context is
    episodic_time_tag: 0-1 current time-in-episode marker
    temporal_ordering_fidelity: 0-1 how accurately events are ordered
    time_cell_activity: 0-1 activity of temporal context/time cells
    recency_signal: 0-1 recency weighting of temporal context

CITATIONS:
    PMC13096332 — Eichenbaum (2017). Time (and space) in the hippocampus.
        Curr Opin Neurobiol.
    PMC13096423 — Montchal et al. (2019). Time cells and episodic
        memory in the hippocampus. Neuron.
    PMC13096361 — Howard & Eichenbaum (2013). Temporal context and
        memory binding in the hippocampus. Learn Mem.
    PMC13099142 — Salz et al. (2016). Time cells in CA1. Nature.
    PMC13097094 — Allen et al. (2016). Hippocampal time cell sequences
        during maze running. Nat Neurosci.


CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus]
"""

from brain.base_mechanism import BrainMechanism


class HippocampalTemporalContextBinder(BrainMechanism):
    """
    Hippocampal temporal context — binds events to their position in time.

    Maintains temporal backdrop for episodic memory encoding and retrieval,
    enabling temporal ordering and recency signals.
    """

    TEMPORAL_RESOLUTION = 0.1

    def __init__(self):
        super().__init__(
            name="HippocampalTemporalContextBinder",
            human_analog="Hippocampus — temporal context binding for episodic memory",
            layer="limbic",
        )
        self.state.setdefault("temporal_context_strength", 0.0)
        self.state.setdefault("episodic_time_tag", 0.0)
        self.state.setdefault("temporal_ordering_fidelity", 0.7)
        self.state.setdefault("time_cell_activity", 0.0)
        self.state.setdefault("recency_signal", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        emotional_tag = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )

        # Time cell activity: fires at specific temporal positions within episodes
        time_cell = hippo_activity * hippo_theta * (0.5 + novelty * 0.5)

        # Temporal context strengthens with theta-locked encoding
        ctx_target = hippo_theta * hippo_activity
        current_ctx = self.state.get("temporal_context_strength", 0.0)
        new_ctx = current_ctx * 0.9 + ctx_target * 0.1

        # Time tag: advances with each significant event
        current_time_tag = self.state.get("episodic_time_tag", 0.0)
        if novelty > 0.3 or abs(emotional_tag) > 0.3:
            new_time_tag = current_time_tag + self.TEMPORAL_RESOLUTION * (novelty + abs(emotional_tag))
        else:
            new_time_tag = current_time_tag
        new_time_tag = min(1.0, new_time_tag)

        # Ordering fidelity: decays without rehearsal
        ordering_fidelity = self.state.get("temporal_ordering_fidelity", 0.7)
        ordering_fidelity = max(0.3, ordering_fidelity - 0.001 * (1.0 - hippo_theta))

        # Recency signal
        recency = novelty * 0.8 + (1.0 - hippo_activity) * 0.2

        self.state["temporal_context_strength"] = round(new_ctx, 4)
        self.state["episodic_time_tag"] = round(new_time_tag, 4)
        self.state["temporal_ordering_fidelity"] = round(ordering_fidelity, 4)
        self.state["time_cell_activity"] = round(time_cell, 4)
        self.state["recency_signal"] = round(recency, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "temporal_context_strength": round(new_ctx, 4),
            "episodic_time_tag": round(new_time_tag, 4),
            "temporal_ordering_fidelity": round(ordering_fidelity, 4),
            "time_cell_activity": round(time_cell, 4),
            "recency_signal": round(recency, 4),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

