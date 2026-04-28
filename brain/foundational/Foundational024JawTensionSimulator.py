"""
Build 24: Foundational024JawTensionSimulator — Trigeminal Motor Nucleus
=====================================================================

PLACEMENT:
  Layer:    foundational (brainstem — trigeminal motor nucleus, mesencephalic nucleus)
  Filename: brain/foundational/Foundational024JawTensionSimulator.py
  Instance name: JawTensionSimulator

NEURAL SUBSTRATE:
  Trigeminal motor nucleus (Vmot) in pons — controls muscles of mastication
  (masseter, temporalis, pterygoids). Receives input from:
  - Sensorimotor cortex (voluntary chewing)
  - Mesencephalic nucleus (Vmes) — proprioceptive feedback from jaw stretch receptors
  - Supratrigeminal nucleus (suppression of masseteric reflex)
  - Reticular formation (aversive reflex circuits)

  KEY CIRCUITS:
  - Jaw-jerk reflex: Ia afferents from periodontal receptors → Vmot → masseter
  - masticatory central pattern generator in reticular formation
  - Tooth-pain modulation: periaqueductal gray → raphe → Vmot (descending inhibition)

  Human analog: chewing, tooth clenching (bruxism), jaw reflex, mastication.

Output keys:
  masseter_tone: float [0.0–1.0] — masseter muscle activation
  molar_bite_force: float [0.0–1.0] — bite force output
  jaw_reflex_suppression: float [0.0–1.0] — suppression of jaw-jerk reflex
  oral_motor_coordination: float [0.0–1.0] — CPG coordination of mastication
  tension_bruxism_index: float [0.0–1.0] — stress-related jaw clenching

CITATIONS:
    PMC1191101 — Dessem D, Iyadurai OD, Taylor A (1988). The Role of Periodontal
        Receptors in the Jaw-Opening Reflex in the Cat. J Physiol.
    PMC1331163 — Cody FW, Lee RW, Taylor A (1972). A Functional Analysis of the
        Components of the Mesencephalic Nucleus of the Fifth Nerve in the Cat.
        J Physiol.
"""

from brain.base_mechanism import BrainMechanism


class JawTensionSimulator(BrainMechanism):
    """
    Trigeminal motor nucleus: mastication, bite force, jaw tension.

    Controls masseter tone, molar bite force, and jaw-jerk reflex
    suppression. Elevated during stress (bruxism).
    """

    STATE_FIELDS = [
        "masseter_tone", "molar_bite_force", "jaw_reflex_suppression",
        "oral_motor_coordination", "tension_bruxism_index", "tick_count",
    ]

    MASSETER_GAIN = 0.55
    BITE_FORCE_GAIN = 0.60
    REFLEX_GAIN = 0.40
    CPG_GAIN = 0.50
    STRESS_BRUXISM_GAIN = 0.65

    def __init__(self, name: str = "JawTensionSimulator",
                 human_analog: str = "Trigeminal motor nucleus — jaw tension and mastication",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["masseter_tone"] = 0.10
        self.state["molar_bite_force"] = 0.05
        self.state["jaw_reflex_suppression"] = 0.30
        self.state["oral_motor_coordination"] = 0.40
        self.state["tension_bruxism_index"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        pain = prior.get("DescendingPainGate", {}).get("gate_output", 0.50)
        sensorimotor = prior.get("SensorimotorCortex", {}).get("motor_command_strength", 0.0)

        # Masseter tone: elevated by stress/arousal, reduced by pain modulation
        stress_tone = stress * self.STRESS_BRUXISM_GAIN
        arousal_tone = arousal * 0.15
        pain_inhibition = (1.0 - pain) * 0.10
        new_masseter = max(0.0, min(1.0, stress_tone + arousal_tone - pain_inhibition))

        # Bite force: proportional to masseter tone; sensorimotor command adds
        bite_force = (new_masseter * self.BITE_FORCE_GAIN) + (sensorimotor * 0.20)
        bite_force = max(0.0, min(1.0, bite_force))

        # Jaw reflex suppression: PAG/raphe descending inhibition (pain gate)
        reflex_suppression = (1.0 - pain) * self.REFLEX_GAIN

        # Oral motor coordination: CPG in reticular formation
        coordination = (new_masseter * 0.30) + (sensorimotor * 0.30) + 0.40
        coordination = max(0.0, min(1.0, coordination))

        # Bruxism index: stress drives jaw clenching during sleep/wake
        bruxism = stress * self.STRESS_BRUXISM_GAIN

        # --- Persist ---
        self.state["masseter_tone"] = round(new_masseter, 4)
        self.state["molar_bite_force"] = round(bite_force, 4)
        self.state["jaw_reflex_suppression"] = round(reflex_suppression, 4)
        self.state["oral_motor_coordination"] = round(coordination, 4)
        self.state["tension_bruxism_index"] = round(bruxism, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "masseter_tone": round(new_masseter, 4),
            "molar_bite_force": round(bite_force, 4),
            "jaw_reflex_suppression": round(reflex_suppression, 4),
            "oral_motor_coordination": round(coordination, 4),
            "tension_bruxism_index": round(bruxism, 4),
        }
