"""
Build 46: Foundational046VocalAutonomicLink — Periaqueductal Gray Vocalization Control
================================================================================

PLACEMENT:
  Layer:    foundational (midbrain — periaqueductal gray, PAG)
  Filename: brain/foundational/Foundational046VocalAutonomicLink.py
  Instance name: VocalAutonomicLink

NEURAL SUBSTRATE:
  Periaqueductal gray (PAG) in midbrain — the emotional motor control
  center. The PAG coordinates vocalization, autonomic responses, and
  defensive behaviors. Contains columnar organization:
  - Lateral/ventrolateral PAG: defensive responses (flight, fight, freeze)
  - Dorsomedial PAG: active coping (vocalization, aggression)
  - The PAG receives input from amygdala, hypothalamus, and cortex,
    and projects to the parabrachial nucleus, nucleus ambiguus, and
    reticular formation.

  VOCALIZATION CIRCUIT:
  PAG (laryngeal CPG) → nucleus ambiguus → laryngeal motor neurons
  (in nucleus ambiguus) → vagus nerve (CN X) → laryngeal muscles

  The PAG coordinates laryngeal tension (vocal pitch), respiratory
  patterning (phonation timing), and autonomic accompaniment (heart
  rate changes during vocalization).

  Human analog: crying, laughing, screaming, vocal autonomic responses.

Output keys:
  laryngeal_tension: float [0.0–1.0] — vocal fold tension
  vocal_autonomic_accompany: float [0.0–1.0] — autonomic accompaniment
  emotional_vocal_drive: float [0.0–1.0] — amygdala-PAG emotional drive
  respiratory_vocal_pattern: float [0.0–1.0] — respiratory patterning for vocalization
  vocal_defensive_response: float [0.0–1.0] — defensive vocal (alarm calls)

CITATIONS:
    PMC2376830 — Ambalavanar R, Tanaka Y, Selbie WS et al. (2004). Neuronal
        Activation in the Medulla Oblongata During Selective Elicitation of the
        Laryngeal Adductor Response. J Appl Physiol.
    PMC3162241 — Pascual-Font A, Hernández-Morato I, McHanwell S et al. (2011).
        The Central Projections of the Laryngeal Nerves in the Rat. J Anat.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class VocalAutonomicLink(BrainMechanism):
    """
    PAG: vocalization, emotional motor control, laryngeal autonomic.

    Coordinates vocal output with autonomic state, driven by limbic input.
    """

    STATE_FIELDS = [
        "laryngeal_tension", "vocal_autonomic_accompany", "emotional_vocal_drive",
        "respiratory_vocal_pattern", "vocal_defensive_response", "tick_count",
    ]

    LARYNGEAL_GAIN = 0.55
    AUTONOMIC_GAIN = 0.50
    EMOTIONAL_GAIN = 0.60
    DEFENSIVE_GAIN = 0.55

    def __init__(self, name: str = "VocalAutonomicLink",
                 human_analog: str = "PAG — periaqueductal gray vocalization control",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["laryngeal_tension"] = 0.10
        self.state["vocal_autonomic_accompany"] = 0.20
        self.state["emotional_vocal_drive"] = 0.10
        self.state["respiratory_vocal_pattern"] = 0.0
        self.state["vocal_defensive_response"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        amygdala = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)
        vocal_motor = prior.get("VocalMotorCortex", {}).get("vocal_command", 0.0)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        vagal_tone = prior.get("VagalRestPromoter", {}).get("cardiac_vagal_tone", 0.40)

        # Emotional vocal drive: amygdala input to PAG → crying/laughing
        emotional_drive = amygdala * self.EMOTIONAL_GAIN
        emotional_drive += stress * 0.30

        # Laryngeal tension: rises with emotional arousal; suppressed by vagal tone
        laryngeal = emotional_drive * self.LARYNGEAL_GAIN
        laryngeal += vocal_motor * 0.30
        vagal_suppression = (1.0 - vagal_tone) * 0.15
        laryngeal = max(0.0, min(1.0, laryngeal + vagal_suppression))

        # Vocal autonomic accompaniment: heart rate, blood pressure changes with vocalization
        autonomic_accompany = emotional_drive * self.AUTONOMIC_GAIN
        autonomic_accompany += stress * 0.25
        autonomic_accompany = min(1.0, autonomic_accompany)

        # Respiratory vocal pattern: vocalization requires respiratory coordination
        respiratory_pattern = (laryngeal * 0.40) + (emotional_drive * 0.30)
        respiratory_pattern = min(1.0, max(0.0, respiratory_pattern))

        # Defensive vocal: alarm call / scream driven by fear + stress
        fear_vocal = amygdala * self.DEFENSIVE_GAIN + stress * 0.30
        # Sympathetic arousal elevates laryngeal tension for alarm
        fear_vocal += (1.0 - vagal_tone) * 0.20
        vocal_defensive = min(1.0, fear_vocal)

        # --- Persist ---
        self.state["laryngeal_tension"] = round(laryngeal, 4)
        self.state["vocal_autonomic_accompany"] = round(autonomic_accompany, 4)
        self.state["emotional_vocal_drive"] = round(emotional_drive, 4)
        self.state["respiratory_vocal_pattern"] = round(respiratory_pattern, 4)
        self.state["vocal_defensive_response"] = round(vocal_defensive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "laryngeal_tension": round(laryngeal, 4),
            "vocal_autonomic_accompany": round(autonomic_accompany, 4),
            "emotional_vocal_drive": round(emotional_drive, 4),
            "respiratory_vocal_pattern": round(respiratory_pattern, 4),
            "vocal_defensive_response": round(vocal_defensive, 4),
        }

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

