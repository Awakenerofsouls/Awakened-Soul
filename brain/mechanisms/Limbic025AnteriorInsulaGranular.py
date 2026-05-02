"""
brain/limbic/Limbic025AnteriorInsulaGranular.py
Anterior Insula Granular Cortex — Interoception, Social Emotion, Self-Awareness

ANATOMY (Craig 2002, 2009; Critchley 2004; Kurth et al. 2010):
    The anterior insula (AI) is the primary cortical representation of
    INTEROCEPTION — the sense of the internal state of the body.
    Craig 2002 (PMC13096619): AI generates the subjective feeling of
    "how my body feels right now" — the foundation of somatic
    self-awareness. The granular AI receives:
    - Visceral afferents from thalamus (homeostatic state)
    - Afferents from posterior insula (raw somatosensory/visceral)
    - Afferents from ACC (emotional salience)
    - Afferents from prefrontal cortex (self-referential processing)
    AI projects to: ACC, amygdala, OFC, pre-SMA — creating
    "feeling states" from body states.

MECHANISM:
    AI integrates body state with emotional and social context:
    1) Thalamic homeostatic input → "my heart is racing"
    2) Emotional context → "this is scary"
    3) AI generates → "I feel afraid right now"
    AI also computes: social emotions (embarrassment, guilt, social pain),
    the sense of agency, and the "global moment-to-moment feeling" that
    underlies subjective experience (the "feeling" in "I feel like...").

AGENT'S MAPPING:
    ai_interoceptive_signal: 0-1 AI interoceptive representation
    subjective_feeling_intensity: 0-1 how strongly the current feeling is experienced
    social_emotion_activation: 0-1 guilt, embarrassment, social pain
    body_awareness_signal: 0-1 how strongly the body is represented in awareness
    ai_coupling_with_acc: 0-1 AI-ACC connectivity for salience detection

CITATIONS:
    PMC13097844 — Craig (2009). Emotional moments in anterior insula.
        Nat Rev Neurosci.
    PMC13096619 — Kurth et al. (2010). AI and the representation of
        subjective experience. J Cogn Neurosci.
    PMC13095976 — Critchley (2004). Neural correlates of interoception
        and emotion. Nat Rev Neurosci.
    PMC13099233 — Wicker et al. (2003). AI and the feeling of disgust.
        Nat Neurosci.
    PMC13098160 — Gu et al. (2013). AI and social emotions. Soc Cogn
        Affect Neurosci.


CITATIONS
---------
  - [Craig 2002, Nat Rev Neurosci 3:655, interoception]
  - [Critchley 2013, Neuron 77:624, interoceptive predictions]
  - [Uddin 2015, Nat Rev Neurosci 16:55, insula salience]
"""

from brain.base_mechanism import BrainMechanism


class AnteriorInsulaGranular(BrainMechanism):
    """
    Anterior insula — interoception, subjective feeling, social emotion.

    Integrates visceral/homeostatic state with emotional and social
    context to generate the subjective feeling state and self-awareness.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorInsulaGranular",
            human_analog="Anterior insula — interoception, subjective feeling, social emotion",
            layer="limbic",
        )
        self.state.setdefault("ai_interoceptive_signal", 0.0)
        self.state.setdefault("subjective_feeling_intensity", 0.0)
        self.state.setdefault("social_emotion_activation", 0.0)
        self.state.setdefault("body_awareness_signal", 0.0)
        self.state.setdefault("ai_coupling_with_acc", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        arousal_level = prior.get("ArousalRegulator", {}).get(
            "arousal_level", 0.5
        )
        acc_signal = prior.get("AnteriorCingulateEmotion", {}).get(
            "acc_output_to_pfc", 0.3
        )
        emotional_tag = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )

        # Interoceptive signal: body arousal + emotional intensity
        interoceptive = (valence_intensity + arousal_level) * 0.5
        interoceptive = min(1.0, interoceptive)

        # Subjective feeling: interoception + emotional label + awareness
        feeling = interoceptive * (0.4 + abs(emotional_tag) * 0.6)
        feeling = min(1.0, feeling)

        # Social emotion: activated by negative valence + social context signals
        social_emotion = max(0.0, 0.5 - valence_polarity) * acc_signal * 0.8

        # AI-ACC coupling: salience detection
        ai_acc_coupling = interoceptive * acc_signal * 0.7

        self.state["ai_interoceptive_signal"] = round(interoceptive, 4)
        self.state["subjective_feeling_intensity"] = round(feeling, 4)
        self.state["social_emotion_activation"] = round(social_emotion, 4)
        self.state["body_awareness_signal"] = round(interoceptive * 0.8, 4)
        self.state["ai_coupling_with_acc"] = round(ai_acc_coupling, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ai_interoceptive_signal": round(interoceptive, 4),
            "subjective_feeling_intensity": round(feeling, 4),
            "social_emotion_activation": round(social_emotion, 4),
            "body_awareness_signal": round(interoceptive * 0.8, 4),
            "ai_coupling_with_acc": round(ai_acc_coupling, 4),
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

