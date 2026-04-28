"""
Build 35: Foundational035PosturalReticularStabilizer — Medial RF Posture/Stability Control
=====================================================================================

PLACEMENT:
  Layer:    foundational (brainstem — medial reticular formation, gigantocellular nucleus)
  Filename: brain/foundational/Foundational035PosturalReticularStabilizer.py
  Instance name: PosturalReticularStabilizer

NEURAL SUBSTRATE:
  Medial reticular formation (gigantocellular nucleus, Gi) in pons/medulla —
  descendingsupports posture, tone, and righting reflexes. The Gi receives:
  - Cortical input (voluntary posture commands from motor cortex)
  - Vestibular input (head position from vestibular nuclei)
  - Cerebellar input (corrective signals via fastigial nucleus)
  - Basal ganglia (via SNr, via thalamus → Gi)

  The Gi projects to spinal cord (ventral horn, medial zone) to control
  axial and proximal limb muscles for posture. The Gi also mediates
  atonia of postural muscles during REM sleep (via SubC input).

  Human analog: posture, balance, righting reflexes.

Output keys:
  postural_tone: float [0.0–1.0] — axial muscle tone
  righting_reflex: float [0.0–1.0] — righting response strength
  vestibular_compensation: float [0.0–1.0] — vestibular correction signal
  postural_atonia: float [0.0–1.0] — REM sleep postural suppression
  antigravity_drive: float [0.0–1.0] — anti-gravity extensor bias

CITATIONS:
    PMC2829753 — Reed WR, Shum-Siu A, Magnuson DS (2008). Reticulospinal Pathways in
        the Ventrolateral Funiculus With Terminations in the Cervical and Lumbar
        Enlargements of the Adult Rat Spinal Cord. Exp Neurol.
    PMC2565459 — Vinay L, Ben-Mabrouk F, Brocard F et al. (2005). Perinatal
        Development of the Motor Systems Involved in Postural Control. Exp Brain Res.
"""

from brain.base_mechanism import BrainMechanism


class PosturalReticularStabilizer(BrainMechanism):
    """
    Medial RF: postural tone, righting reflexes, vestibular compensation.

    Maintains anti-gravity posture and controls postural atonia during REM.
    """

    STATE_FIELDS = [
        "postural_tone", "righting_reflex", "vestibular_compensation",
        "postural_atonia", "antigravity_drive", "tick_count",
    ]

    TONE_GAIN = 0.55
    RIGHTING_GAIN = 0.50
    VESTIBULAR_GAIN = 0.45
    GRAVITY_GAIN = 0.60

    def __init__(self, name: str = "PosturalReticularStabilizer",
                 human_analog: str = "Medial RF — postural tone and righting reflexes",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["postural_tone"] = 0.50
        self.state["righting_reflex"] = 0.30
        self.state["vestibular_compensation"] = 0.20
        self.state["postural_atonia"] = 0.0
        self.state["antigravity_drive"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        vestibular = prior.get("VestibularIntegrator", {}).get("head_tilt_signal", 0.0)
        cerebellar = prior.get("CerebellarDeepNuclei", {}).get("corrective_signal", 0.0)
        rem_atonia = prior.get("REMAtoniaController", {}).get("atonia_level", 0.0)
        motor_command = prior.get("MotorThalamus", {}).get("motor_command_strength", 0.0)

        # Postural tone: baseline from arousal; cortical input modulates
        postural_tone = arousal * self.TONE_GAIN
        # Motor cortex adds voluntary posture command
        postural_tone += motor_command * 0.20
        postural_tone = min(1.0, max(0.0, postural_tone))

        # Righting reflex: vestibular tilt triggers corrective response
        righting_reflex = abs(vestibular - 0.5) * self.RIGHTING_GAIN
        # Cerebellar correction strengthens righting
        righting_reflex += cerebellar * 0.30

        # Vestibular compensation: correction for head tilt
        vestibular_compensation = abs(vestibular - 0.5) * self.VESTIBULAR_GAIN

        # Postural atonia: REM atonia suppresses postural muscles
        postural_atonia = rem_atonia * 0.80

        # Antigravity drive: extensor bias (anti-gravity muscle activation)
        antigravity_drive = (postural_tone * 0.50) + (1.0 - rem_atonia) * 0.30

        # --- Persist ---
        self.state["postural_tone"] = round(postural_tone, 4)
        self.state["righting_reflex"] = round(righting_reflex, 4)
        self.state["vestibular_compensation"] = round(vestibular_compensation, 4)
        self.state["postural_atonia"] = round(postural_atonia, 4)
        self.state["antigravity_drive"] = round(antigravity_drive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "postural_tone": round(postural_tone, 4),
            "righting_reflex": round(righting_reflex, 4),
            "vestibular_compensation": round(vestibular_compensation, 4),
            "postural_atonia": round(postural_atonia, 4),
            "antigravity_drive": round(antigravity_drive, 4),
        }
