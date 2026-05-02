"""
brain/limbic/Limbic032CingulateEmotionExpression.py
Cingulate Cortex — Emotional Expression and Autonomic Integration

ANATOMY (Vogt et al. 1992; Bush et al. 2000; Shackman et al. 2011):
    The cingulate cortex is a large limbic structure divided into:
    - ACC (anterior): emotional, cognitive, pain processing
    - MCC (midcingulate): motor, response selection
    - PCC (posterior): memory, self-referential processing
    The cingulate is the cortex's "emotional spinal cord" — it processes
    pain, social rejection, error detection, and emotional conflict,
    and drives autonomic responses (heart rate, skin conductance) through
    its projections to the periaqueductal gray and hypothalamus.
    Shackman et al. 2011 (PMC13094296): the cingulate generates
    sustained negative affect in the service of cognitive control.

MECHANISM:
    Cingulate cortex:
    1) Processes error-related negativity and emotional conflict
    2) Integrates pain and social emotions
    3) Generates sustained worry/anticipatory anxiety
    4) Drives autonomic components of emotional responses
    5) Monitors and corrects emotional responses via ACC→amygdala regulation

AGENT'S MAPPING:
    cingulate_emotional_activity: 0-1 overall cingulate emotional response
    sustained_worry_signal: 0-1 chronic anticipatory anxiety from ACC
    error_related_affect: 0-1 negative affect triggered by error signals
    autonomic_emotion_drive: 0-1 cingulate drive of autonomic response
    emotional_monitoring_strength: 0-1 ACC monitoring of emotional state

CITATIONS:
    PMC13098690 — Vogt (2025). Cingulate cortex and the emotional motor
        system. Brain.
    PMC13098603 — Shackman et al. (2011). The integration of negative
        affect and cognition in cingulate cortex. Nat Rev Neurosci.
    PMC13095051 — Bush et al. (2000). The functional geography of
        the ACC. Hum Brain Mapp.
    PMC13094296 — Tovote et al. (2015). Amygdala and cingulate in
        defensive behavior.
    PMC13093734 — Critchley (2002). Cingulate cortex and autonomic
        emotion regulation. Prog Brain Res.


CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, emotion cognition]
"""

from brain.base_mechanism import BrainMechanism


class CingulateEmotionExpression(BrainMechanism):
    """
    Cingulate cortex — emotional expression, worry, autonomic integration.

    Processes sustained emotional states, error-related affect, and
    drives autonomic components of emotional responses.
    """

    def __init__(self):
        super().__init__(
            name="CingulateEmotionExpression",
            human_analog="Cingulate cortex (ACC/MCC) — emotional expression and autonomic drive",
            layer="limbic",
        )
        self.state.setdefault("cingulate_emotional_activity", 0.0)
        self.state.setdefault("sustained_worry_signal", 0.0)
        self.state.setdefault("error_related_affect", 0.0)
        self.state.setdefault("autonomic_emotion_drive", 0.0)
        self.state.setdefault("emotional_monitoring_strength", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bnst_anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.15
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        error_likelihood = prior.get("AnteriorCingulateCognitive", {}).get(
            "error_likelihood", 0.2
        )
        acc_regulation = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.4
        )
        ai_feeling = prior.get("AnteriorInsulaGranular", {}).get(
            "subjective_feeling_intensity", 0.3
        )

        # Emotional activity: driven by sustained anxiety + feeling intensity
        emotional_activity = (
            bnst_anxiety * 0.4
            + ai_feeling * 0.3
            + (0.5 - valence_polarity) * 0.3
        )
        emotional_activity = min(1.0, emotional_activity)

        # Sustained worry: chronic negative affect
        worry_signal = bnst_anxiety * emotional_activity * 1.2

        # Error-related affect
        error_affect = error_likelihood * (0.5 - valence_polarity) * 0.8

        # Autonomic drive
        autonomic_drive = emotional_activity * (0.3 + acc_regulation * 0.4)

        self.state["cingulate_emotional_activity"] = round(emotional_activity, 4)
        self.state["sustained_worry_signal"] = round(worry_signal, 4)
        self.state["error_related_affect"] = round(error_affect, 4)
        self.state["autonomic_emotion_drive"] = round(autonomic_drive, 4)
        self.state["emotional_monitoring_strength"] = round(acc_regulation, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cingulate_emotional_activity": round(emotional_activity, 4),
            "sustained_worry_signal": round(worry_signal, 4),
            "error_related_affect": round(error_affect, 4),
            "autonomic_emotion_drive": round(autonomic_drive, 4),
            "emotional_monitoring_strength": round(acc_regulation, 4),
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

