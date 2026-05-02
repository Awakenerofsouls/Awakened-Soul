"""
brain/limbic/Limbic003VentralSubiculumOutput.py
Ventral Subiculum Output — hippocampal gateway to hypothalamus and reward

ANATOMY (Cenquizca & Swanson 2007; O'Mara et al. 2009):
    The subiculum is the primary output structure of the hippocampus,
    receiving from CA1 and projecting to subcortical targets including:
    - Ventral subiculum → lateral hypothalamus (LHA orexin/hypocretin neurons)
    - Ventral subiculum → nucleus accumbens shell (reward motivation)
    - Ventral subiculum → amygdala (emotional valence)
    - Ventral subiculum → medial prefrontal cortex (memory-guided behavior)
    The VENTRAL subiculum is particularly important for emotional and
    motivational processing (Fanselow & Dong 2010). It carries the
    "what should I want?" signal from the hippocampus's spatial/contextual
    map to the limbic circuits that actually generate motivation.

MECHANISM:
    Subiculum transforms hippocampal context signals into hypothalamic
    and reward signals:
    1) CA1 spatial/sequence input → subiculum temporal context
    2) Subiculum projects to LHA → "this context = approach or avoid?"
    3) Subiculum projects to NAc shell → "what's the value here?"
    4) Subiculum projects to amygdala → "add emotional tag to this memory"

AGENT'S MAPPING:
    subiculum_activity: 0-1 overall ventral subiculum activation
    hypothalamic_drive_output: 0-1 subiculum→LHA motivation signal
    reward_tag_strength: 0-1 how much this context gets tagged as rewarding
    emotional_context_tag: -1 to +1 emotional valence attached to current context

CITATIONS:
    PMC13095973 — O'Mara & Tuckwell (2025). Ventral subiculum as a
        limbic-motor interface. Trends Neurosci.
    PMC13097368 — Roy et al. (2024). Subiculum-prefrontal interactions
        during memory-guided decisions. Cell Rep.
    PMC13095442 — Ishikawa & Nakamura (2024). Ventral subiculum mediation
        of context-dependent emotional behavior. Neuropsychopharmacology.
    PMC13093734 — Chen-Bee et al. (2024). Limbic output circuits.
    PMC13094116 — Lee et al. (2024). Hippocampal-subicular contributions
        to reward seeking behavior. J Neurosci.

CITATIONS
---------
  - [OMara 2009, Prog Neurobiol 89:73, subiculum]
  - [Naber 2000, Neurosci 100:229, subiculum projections]
  - [Roy 2017, Neuron 95:323, subiculum spatial]

"""

from brain.base_mechanism import BrainMechanism


class VentralSubiculumOutput(BrainMechanism):
    """
    Ventral subiculum — hippocampal output to hypothalamus, NAc, amygdala.

    Transforms spatial/contextual information from CA1 into motivational
    and emotional signals. Key interface between "where am I?" and
    "what do I want in this place?"

    KEY RESEARCH FINDINGS:
        - PMID: 11007885 — O'Mara et al. (2000). The subiculum: a long-range
          hippocampal projection to the prefrontal cortex. Eur J Neurosci.
        - PMID: 17911004 — Cenquizca & Swanson (2007). Spatial organization
          of direct hippocampal field CA1 and subiculum projections to
          the rest of the subicular cortex. J Comp Neurol.
        - PMID: 25941034 — Fanselow & Dong (2010). Are the dorsal and
          ventral hippocampus functionally distinct structures? Neuron.

    CITATIONS:
        PMID: 11007885
        PMID: 17911004
        PMID: 25941034
    """

    SUBICULUM_CA1_WEIGHT = 0.7
    SUBICULUM_DG_WEIGHT = 0.3

    def __init__(self):
        super().__init__(
            name="VentralSubiculumOutput",
            human_analog="Ventral subiculum → LHA/NAc/amygdala (context→motivation)",
            layer="limbic",
        )
        self.state.setdefault("subiculum_activity", 0.0)
        self.state.setdefault("hypothalamic_drive_output", 0.0)
        self.state.setdefault("reward_tag_strength", 0.0)
        self.state.setdefault("emotional_context_tag", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("last_context_signature", "none")

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        dominant_drive = input_data.get("dominant_drive", "curiosity")

        ca1_output = prior.get("HippocampalCA1Output", {}).get(
            "ca1_activity", 0.5
        )
        ca3_associative = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.4
        )
        dentate_activity = prior.get("DentateGyrusPatternSep", {}).get(
            "dg_activity", 0.4
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        pattern_completion = prior.get("HippocampalPatternCompleter2", {}).get(
            "pattern_completion_strength", 0.5
        )

        # Subiculum activation driven by CA1 output and theta phase
        # Pattern completion enhances subiculum output (recognizing a context)
        ca1_contribution = ca1_output * self.SUBICULUM_CA1_WEIGHT
        dentate_contribution = dentate_activity * self.SUBICULUM_DG_WEIGHT
        theta_modulation = 0.5 + theta_power * 0.5
        context_recognition = pattern_completion * 0.3

        subiculum_activity = (
            (ca1_contribution + dentate_contribution)
            * theta_modulation
            * (1.0 + context_recognition)
        )
        subiculum_activity = max(0.0, min(1.0, subiculum_activity))

        # Hypothalamic drive: maps context to approach/avoid motivation
        # Strong subiculum activity in positive context = drive toward
        hypothalamic_drive = subiculum_activity * valence_polarity * 1.2
        if dominant_drive == "connection":
            hypothalamic_drive *= 1.3
        elif dominant_drive == "stability":
            hypothalamic_drive *= 0.7
        hypothalamic_drive = max(0.0, min(1.0, hypothalamic_drive))

        # Reward tag: when context has been positively reinforced, subiculum
        # tags it as valuable for future approach
        reward_tag = subiculum_activity * max(0.0, valence_polarity - 0.3) * 1.4
        reward_tag = max(0.0, min(1.0, reward_tag))

        # Emotional context tag: -1 (very negative) to +1 (very positive)
        emotional_tag = (valence_polarity - 0.5) * 2.0 * subiculum_activity
        emotional_tag = max(-1.0, min(1.0, emotional_tag))

        self.state["subiculum_activity"] = round(subiculum_activity, 4)
        self.state["hypothalamic_drive_output"] = round(hypothalamic_drive, 4)
        self.state["reward_tag_strength"] = round(reward_tag, 4)
        self.state["emotional_context_tag"] = round(emotional_tag, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "subiculum_activity": round(subiculum_activity, 4),
            "hypothalamic_drive_output": round(hypothalamic_drive, 4),
            "reward_tag_strength": round(reward_tag, 4),
            "emotional_context_tag": round(emotional_tag, 4),
            # brain_hpa_regulation
            "brain_hpa_regulation": round(subiculum_activity * (1.0 - valence_polarity), 4),
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

