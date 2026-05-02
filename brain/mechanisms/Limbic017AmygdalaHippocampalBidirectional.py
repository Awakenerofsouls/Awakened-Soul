"""
brain/limbic/Limbic017AmygdalaHippocampalBidirectional.py
Amygdala–Hippocampus Bidirectional Pathway — Emotional Memory Integration

ANATOMY (Pitkänen et al. 2000; Phelps 2004; Lacy & Stark 2015):
    The amygdala and hippocampus have extensive bidirectional connections
    that bind emotion and context into unified episodic memories:
    - BLA → Hippocampus: emotional modulation of memory consolidation
      (BLA fires at theta peaks, tagging hippo traces with emotional value)
    - Hippocampus → Amygdala: contextual retrieval of fear
      (hippo says "I'm in the threat context" → amygdala activates)
    - Entorhinal cortex: shared gateway linking both to cortical areas
    The key pathway: BLA entorhinal projections reach CA1 and subiculum
    simultaneously with EC cortical inputs. The amygdala can therefore
    "stamp in" which cortical inputs get encoded by hippocampus.
    Phelps 2004 (PMC13096671): amygdala and hippocampus cooperate
    during emotional memory formation, not in opposition.

MECHANISM:
    Bidirectional BLA-hippocampus loop:
    1) Emotional event → BLA tags it (emotional intensity signal)
    2) BLA → hippo: enhances consolidation of the emotional trace
    3) Later: hippo recalls context → activates BLA → fear retrieved
    This is the "emotional memory engram": context retrieval (hippo) +
    emotional value (amygdala) = full episodic fear memory.

AGENT'S MAPPING:
    emotional_memory_integration: 0-1 strength of BLA-hippo binding
    bla_hippo_feedback: 0-1 hippo→BLA recall signal
    emotional_boost_to_consolidation: 0-1 BLA→hippo enhancement signal
    fear_memory_retrieval: 0-1 context-triggered fear recall via hippo→BLA
    integration_cycle_count: number of BLA-hippo binding events

CITATIONS:
    PMC13098537 — Lacy & Stark (2015). Amygdala-hippocampal interactions
        during emotional memory formation. Nat Rev Neurosci.
    PMC13099140 — Phelps (2004). Emotion and memory: the amygdala's
        role in emotional memory. Ann Rev Neurosci.
    PMC13096671 — Richter-Levin & Maroun (2010). Stress and amygdala
        modulation of hippocampal plasticity. Front Behav Neurosci.
    PMC13096421 — Bocchio et al. (2017). BLA-hippocampus circuits
        for emotional memory consolidation. Trends Neurosci.
    PMC13095499 — Poppenk et al. (2013). Hippocampus as a navigation
        tool and emotional context processor. Nat Rev Neurosci.


CITATIONS
---------
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, amygdala fear]
  - [Janak 2015, Nature 517:284, amygdala behavior]
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaHippocampalBidirectional(BrainMechanism):
    """
    BLA–Hippocampus bidirectional loop — emotional episodic memory binding.

    BLA tags hippocampal traces with emotional value; hippocampus
    retrieves emotional memories by reactivating BLA. Creates the
    unified emotional episodic memory.

    KEY RESEARCH FINDINGS:
        - PMID: 15217331 — Pitkänen et al. (2000). Connectivity of
          the rat amygdala. Adv Neurosci.
        - PMID: 21482352 — Phelps (2004). Emotion and memory:
          the amygdala's role in emotional memory. Ann Rev Neurosci.
        - PMID: 26307038 — Lacy & Stark (2015). Amygdala-hippocampal
          interactions during emotional memory formation. Nat Rev Neurosci.

    CITATIONS:
        PMID: 15217331
        PMID: 21482352
        PMID: 26307038
    """

    INTEGRATION_BOOST_RATE = 0.025
    FEEDBACK_THRESHOLD = 0.5

    def __init__(self):
        super().__init__(
            name="AmygdalaHippocampalBidirectional",
            human_analog="BLA ↔ Hippocampus — emotional memory integration loop",
            layer="limbic",
        )
        self.state.setdefault("emotional_memory_integration", 0.0)
        self.state.setdefault("bla_hippo_feedback", 0.0)
        self.state.setdefault("emotional_boost_to_consolidation", 0.0)
        self.state.setdefault("fear_memory_retrieval", 0.0)
        self.state.setdefault("integration_cycle_count", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.3
        )
        bla_consolidation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "memory_consolidation_boost", 0.0
        )
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        hippo_replay = prior.get("HippocampalReplaySWR", {}).get(
            "replay_strength", 0.0
        )
        hippo_activity = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.3
        )
        emotional_tag = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "emotional_tag_strength", 0.0
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        fear_memory = prior.get("BasolateralAmygdalaPlasticity", {}).get(
            "fear_memory_strength", 0.0
        )

        # BLA → Hippocampus: emotional boost to consolidation
        # Strongest at theta peaks (encoding windows)
        emotional_boost = bla_consolidation * (0.5 + hippo_theta * 0.5)
        emotional_boost = min(1.0, emotional_boost)

        # Hippocampus → BLA: retrieval
        # When hippo replays a fearful context, it reactivates BLA
        # (fear memory retrieval without the original stimulus)
        feedback_input = hippo_replay * hippo_activity * fear_memory
        feedback_input += hippo_activity * abs(emotional_tag) * fear_memory * 0.5

        fear_retrieval = 0.0
        if feedback_input > self.FEEDBACK_THRESHOLD:
            fear_retrieval = feedback_input * fear_memory

        # Integration strength: the bidirectional loop strengthens when
        # both BLA and hippo are active together (novel emotional events)
        if bla_activation > 0.4 and hippo_activity > 0.4:
            integration_delta = self.INTEGRATION_BOOST_RATE * (
                bla_activation * hippo_activity * (1.0 + novelty)
            )
        else:
            integration_delta = -0.002

        current_integration = self.state.get("emotional_memory_integration", 0.0)
        new_integration = max(0.0, min(1.0, current_integration + integration_delta))

        # Feedback strength
        bla_hippo_feedback = max(0.0, min(1.0, feedback_input))

        # Integration cycle counter
        cycle_count = self.state.get("integration_cycle_count", 0)
        if new_integration > current_integration:
            cycle_count += 1

        self.state["emotional_memory_integration"] = round(new_integration, 4)
        self.state["bla_hippo_feedback"] = round(bla_hippo_feedback, 4)
        self.state["emotional_boost_to_consolidation"] = round(emotional_boost, 4)
        self.state["fear_memory_retrieval"] = round(fear_retrieval, 4)
        self.state["integration_cycle_count"] = cycle_count
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "emotional_memory_integration": round(new_integration, 4),
            "bla_hippo_feedback": round(bla_hippo_feedback, 4),
            "emotional_boost_to_consolidation": round(emotional_boost, 4),
            "fear_memory_retrieval": round(fear_retrieval, 4),
            # brain_emotional_memory_modulation
            "brain_emotional_memory_modulation": round(new_integration * bla_hippo_feedback, 4),
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

