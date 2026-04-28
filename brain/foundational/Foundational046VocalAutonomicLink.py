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
