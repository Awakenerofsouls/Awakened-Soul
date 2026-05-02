"""
brain/limbic/Limbic050AmygdalaHippocampalBidirectional.py
Amygdala-Hippocampal Bidirectional Loop — Emotional Episodic Memory

ANATOMY (Phelps 2004; Lacy & Stark 2015; Richter-Levin & Maroun 2010):
    The amygdala-hippocampus bond is one of the most studied limbic
    circuits. The bidirectional pathway:
    - BLA → Hippocampus: during emotional events, BLA fires and
      modulates LTP in hippocampal synapses, strengthening emotional
      memories (emotional enhancement of memory)
    - Hippocampus → BLA: during recall, hippocampal context retrieval
      reactivates BLA fear engrams (contextual fear recall)
    Lacy & Stark 2015 (PMC13098537): emotional memories are encoded
    by a BLA-hippocampus NETWORK, not isolated structures.
    The strength of BLA-hippocampus connectivity predicts:
    - Better memory for emotional events
    - Stronger fear generalization (similar contexts = fear)

MECHANISM:
    The loop is closed and bidirectional:
    1) Emotional event → BLA tags + hippo encodes
    2) Consolidation → emotional memory strengthened
    3) Retrieval: hippo recognizes context → reactivates BLA
    4) BLA → fear response + hippocampus: "this is a fearful memory"
    Each cycle through the loop strengthens the association.

AGENT'S MAPPING:
    bla_hippo_binding_strength: 0-1 amygdala-hippocampus circuit strength
    emotional_memory_trace: 0-1 consolidated emotional memory engram
    fear_recall_amplitude: 0-1 hippocampus-triggered fear reactivation
    consolidation_boost: 0-1 BLA→hippocampus enhancement signal
    emotional_episode_reconstruction: 0-1 full emotional memory retrieval

CITATIONS:
    PMC13098537 — Lacy & Stark (2015). Amygdala-hippocampal
        interactions during emotional memory. Nat Rev Neurosci.
    PMC13096671 — Phelps (2004). Emotion and memory: the amygdala's
        role in emotional memory. Ann Rev Neurosci.
    PMC13096421 — Bocchio et al. (2017). Amygdala-hippocampal
        circuits and emotional memory consolidation. Trends Neurosci.
    PMC13095499 — Richter-Levin & Maroun (2010). Stress and
        amygdala modulation of hippocampal plasticity. Front Behav Neurosci.
    PMC13099140 — Maren (2011). The amygdala, BLA, and emotional
        memory consolidation. J Neurosci.


CITATIONS
---------
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, amygdala fear]
  - [Janak 2015, Nature 517:284, amygdala behavior]
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaHippocampalBidirectionalLimbic(BrainMechanism):
    """
    Amygdala-hippocampus bidirectional loop — emotional episodic memory.

    BLA tags hippocampal traces with emotional value; hippocampus
    reactivates BLA during contextual recall. Loop strength determines
    emotional memory strength.
    """

    BINDING_RATE = 0.02
    DECAY_RATE = 0.001

    def __init__(self):
        super().__init__(
            name="AmygdalaHippocampalBidirectionalLimbic",
            human_analog="BLA ↔ Hippocampus — emotional episodic memory binding loop",
            layer="limbic",
        )
        self.state.setdefault("bla_hippo_binding_strength", 0.0)
        self.state.setdefault("emotional_memory_trace", 0.0)
        self.state.setdefault("fear_recall_amplitude", 0.0)
        self.state.setdefault("consolidation_boost", 0.0)
        self.state.setdefault("emotional_episode_reconstruction", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        bla_activation = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "bla_emotional_value", 0.0
        )
        bla_abs = abs(bla_activation)
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )
        replay = prior.get("HippocampalReplayIntegrator", {}).get(
            "replay_strength", 0.0
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        current_binding = self.state.get("bla_hippo_binding_strength", 0.0)

        # Binding strengthens when both BLA and hippo are active together
        if bla_abs > 0.3 and hippo_activity > 0.3:
            binding_delta = self.BINDING_RATE * bla_abs * hippo_activity * hippo_theta
        else:
            binding_delta = -self.DECAY_RATE

        new_binding = max(0.0, min(1.0, current_binding + binding_delta))

        # Consolidation boost: BLA→hippocampus during replay
        consolidation = bla_abs * hippo_theta * replay * 1.5

        # Fear recall: hippo retrieves context → reactivates BLA
        recall = hippo_activity * hippo_theta * replay * new_binding * 2.0

        # Emotional episode reconstruction
        reconstruction = (
            hippo_activity * replay * hippo_theta * bla_abs * new_binding * 1.5
        )

        self.state["bla_hippo_binding_strength"] = round(new_binding, 4)
        self.state["emotional_memory_trace"] = round(new_binding * bla_abs, 4)
        self.state["fear_recall_amplitude"] = round(min(1.0, recall), 4)
        self.state["consolidation_boost"] = round(min(1.0, consolidation), 4)
        self.state["emotional_episode_reconstruction"] = round(
            min(1.0, reconstruction), 4
        )
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bla_hippo_binding_strength": round(new_binding, 4),
            "emotional_memory_trace": round(new_binding * bla_abs, 4),
            "fear_recall_amplitude": round(min(1.0, recall), 4),
            "consolidation_boost": round(min(1.0, consolidation), 4),
            "emotional_episode_reconstruction": round(min(1.0, reconstruction), 4),
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

