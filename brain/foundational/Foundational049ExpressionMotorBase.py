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
