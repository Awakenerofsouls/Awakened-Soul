"""
Build 49: Foundational049ExpressionMotorBase — Facial Motor Nucleus Expressivity
==========================================================================

PLACEMENT:
  Layer:    foundational (brainstem — facial motor nucleus, nucleus ambiguus)
  Filename: brain/foundational/Foundational049ExpressionMotorBase.py
  Instance name: ExpressionMotorBase

NEURAL SUBSTRATE:
  Facial motor nucleus (VII) in pons — controls muscles of facial expression.
  Contains two divisions:
  - Upper division (temporal, zygomatic): frontalis, orbicularis oculi,
    zygomaticus → upper face, smile
  - Lower division (buccal, marginal mandibular): risorius, depressor
    anguli → lower face, frown

  INPUTS:
  - Motor cortex (voluntary emotional expression)
  - Amygdala (involuntary emotional expression — fear, disgust)
  - Cingulate cortex (empathic facial mirroring)
  - Brainstem central pattern generator for innate emotional expressions

  KEY: The facial nerve carries motor output AND taste (chorda tympani) +
  lacrimal gland parasympathetics. Facial expressions are the most visible
  index of emotional state.

  Human analog: facial expressions, emotional display, rapport.

Output keys:
  facial_expression_tone: float [0.0–1.0] — facial muscle activation level
  positive_expression: float [0.0–1.0] — smile/dopamine-driven expression
  negative_expression: float [0.0–1.0] — frown/fear expression
  autonomic_accompaniment: float [0.0–1.0] — autonomic facial accompaniment
  expression_motor_complexity: float [0.0–1.0] — expression repertoire

CITATIONS:
    PMC10171515 — Sato W, Kochiyama T, Yoshikawa S (2023). The Widespread Action
        Observation/Execution Matching System for Facial Expression Processing.
        Cereb Cortex.
    PMC12358327 — Duan Y, Lv K, Zhao C et al. (2025). Exploring Facial
        Nucleus-Centered Connectivity in Hemifacial Spasm. Sci Rep.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ExpressionMotorBase(BrainMechanism):
    """
    Facial motor nucleus: emotional facial expressions.

    Controls facial expression muscles driven by limbic and cortical input.
    """

    STATE_FIELDS = [
        "facial_expression_tone", "positive_expression", "negative_expression",
        "autonomic_accompaniment", "expression_motor_complexity", "tick_count",
    ]

    POSITIVE_GAIN = 0.55
    NEGATIVE_GAIN = 0.55
    AUTONOMIC_GAIN = 0.40

    def __init__(self, name: str = "ExpressionMotorBase",
                 human_analog: str = "Facial motor nucleus — facial expression control",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["facial_expression_tone"] = 0.30
        self.state["positive_expression"] = 0.10
        self.state["negative_expression"] = 0.05
        self.state["autonomic_accompaniment"] = 0.20
        self.state["expression_motor_complexity"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        amygdala_fear = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)
        amygdala_disgust = prior.get("AmygdalaOutput", {}).get("disgust_signal", 0.0)
        reward = prior.get("VentralStriatumOutput", {}).get("reward_signal", 0.0)
        cingulate = prior.get("AnteriorCingulateConflict", {}).get("empathic_signal", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        vagal_tone = prior.get("VagalRestPromoter", {}).get("cardiac_vagal_tone", 0.40)

        # Positive expression: reward + dopamine + social bonding
        positive_expression = reward * self.POSITIVE_GAIN
        positive_expression += cingulate * 0.25
        positive_expression = min(1.0, positive_expression)

        # Negative expression: fear + disgust
        negative_expression = max(amygdala_fear, amygdala_disgust) * self.NEGATIVE_GAIN
        negative_expression = min(1.0, negative_expression)

        # Facial expression tone: sum of positive + negative
        facial_expression_tone = (positive_expression * 0.50) + (negative_expression * 0.50)
        facial_expression_tone += arousal * 0.15
        facial_expression_tone = min(1.0, facial_expression_tone)

        # Autonomic accompaniment: expressions come with autonomic signatures
        # Positive: parasympathetic (social engagement, vagal)
        # Negative: sympathetic (fear, disgust)
        parasym_autonomic = vagal_tone * positive_expression * self.AUTONOMIC_GAIN
        sym_autonomic = (1.0 - vagal_tone) * negative_expression * self.AUTONOMIC_GAIN
        autonomic_accompaniment = parasym_autonomic + sym_autonomic

        # Expression complexity: more complex in social species, high with cingulate
        complexity = cingulate * 0.40 + positive_expression * 0.30 + 0.30

        # --- Persist ---
        self.state["facial_expression_tone"] = round(facial_expression_tone, 4)
        self.state["positive_expression"] = round(positive_expression, 4)
        self.state["negative_expression"] = round(negative_expression, 4)
        self.state["autonomic_accompaniment"] = round(autonomic_accompaniment, 4)
        self.state["expression_motor_complexity"] = round(complexity, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "facial_expression_tone": round(facial_expression_tone, 4),
            "positive_expression": round(positive_expression, 4),
            "negative_expression": round(negative_expression, 4),
            "autonomic_accompaniment": round(autonomic_accompaniment, 4),
            "expression_motor_complexity": round(complexity, 4),
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

