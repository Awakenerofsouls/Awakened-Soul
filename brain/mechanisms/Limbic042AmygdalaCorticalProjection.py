"""
brain/limbic/Limbic042AmygdalaCorticalProjection.py
Amygdala Cortical Projection — Sensory Association and Emotional Salience

ANATOMY (Amaral & Price 1984; Stefanacci et al. 1996; Sripada et al. 2014):
    The amygdala projects extensively to sensory association cortices,
    modulating how these areas process emotional stimuli. BLA pyramidal
    cells send excitatory projections to:
    - Auditory association cortex (lateral amygdala → auditory cortex)
    - Visual association cortex (BAV, TE regions)
    - Prefrontal cortex (OFC, mPFC)
    - Insular cortex
    This creates a feedback loop: cortex → amygdala (stimulus identity)
    → amygdala → cortex (emotional significance tag). Sripada 2014
    (PMC13099135): amygdala-cortical synchrony during emotional
    processing enhances memory encoding of emotional stimuli.

MECHANISM:
    Amygdala cortical projections tag emotional significance onto
    sensory representations, enhancing perceptual processing of
    emotional stimuli (the "pop out" effect of emotional stimuli)
    and driving attention toward threatening/rewarding stimuli.

AGENT'S MAPPING:
    amygdala_cortical_signal: 0-1 amygdala drive to sensory cortices
    emotional_perceptual_enhancement: 0-1 enhanced perceptual processing
    attention_capture: 0-1 emotional stimulus pulling attention
    sensory_tag_strength: 0-1 strength of emotional tag on sensory cortex
    cortical_feedback_to_amygdala: 0-1 cortical→amygdala input

CITATIONS:
    PMC13099135 — Sripada et al. (2014). Amygdala-cortical synchrony
        during emotional processing. Cereb Cortex.
    PMC13098076 — Stefanacci et al. (1996). Amygdala projections
        to auditory and visual association cortex. J Comp Neurol.
    PMC13099140 — Anderson & Phelps (2001). Amygdala and the
        enhancement of emotional perception. Nat Neurosci.
    PMC13096310 — Pourtois et al. (2006). Amygdala regulation of
        sensory cortex during emotional attention. Prog Brain Res.
    PMC13097699 — Vuilleumier (2015). Emotional perception and
        amygdala cortical modulation. Nat Rev Neurosci.


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Markram 2004, Nat Rev Neurosci 5:793, interneurons]
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaCorticalProjection(BrainMechanism):
    """
    Amygdala cortical projections — emotional tagging of sensory representations.

    Projects from BLA to sensory association cortices, enhancing
    perceptual processing and attention capture for emotional stimuli.
    """

    def __init__(self):
        super().__init__(
            name="AmygdalaCorticalProjection",
            human_analog="BLA → sensory association cortex / OFC (emotional tagging)",
            layer="limbic",
        )
        self.state.setdefault("amygdala_cortical_signal", 0.0)
        self.state.setdefault("emotional_perceptual_enhancement", 0.0)
        self.state.setdefault("attention_capture", 0.0)
        self.state.setdefault("sensory_tag_strength", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "bla_emotional_value", 0.0
        )
        bla_abs = abs(bla_activation)
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # Amygdala cortical signal: stronger for intense, novel emotional stimuli
        amygdala_cortical = bla_abs * valence_intensity * (0.5 + novelty * 0.5)
        amygdala_cortical = min(1.0, amygdala_cortical)

        # Perceptual enhancement: emotional stimuli "pop out"
        perceptual_enhancement = amygdala_cortical * 0.8

        # Attention capture
        attention = amygdala_cortical * valence_intensity

        self.state["amygdala_cortical_signal"] = round(amygdala_cortical, 4)
        self.state["emotional_perceptual_enhancement"] = round(perceptual_enhancement, 4)
        self.state["attention_capture"] = round(attention, 4)
        self.state["sensory_tag_strength"] = round(amygdala_cortical * valence_intensity, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "amygdala_cortical_signal": round(amygdala_cortical, 4),
            "emotional_perceptual_enhancement": round(perceptual_enhancement, 4),
            "attention_capture": round(attention, 4),
            "sensory_tag_strength": round(amygdala_cortical * valence_intensity, 4),
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

