"""
Build 60: Foundational060LateralTuberalNucleusOutput — Lateral Tuberal Nucleus Integration
================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — lateral tuberal nucleus)
  Filename: brain/foundational/Foundational060LateralTuberalNucleusOutput.py
  Instance name: LateralTuberalNucleusOutput

NEURAL SUBSTRATE:
  Lateral tuberal nucleus (LTN) — a hypothalamic nucleus adjacent to
  the lateral hypothalamus, poorly understood but implicated in:
  - Integration of metabolic and autonomic signals
  - Projects to the bed nucleus of the stria terminalis (BNST)
  - Connected to lateral hypothalamus and zona incerta
  - Contains neurotensin and NPY neurons

  The LTN is part of the extended lateral hypothalamic area and
  integrates multiple drives: hunger, thirst, sexual motivation,
  and defensive behaviors.

  Human analog: general drive integration, hypothalamic motivation.

Output keys:
  ltn_integrator: float [0.0–1.0] — composite drive integrator output
  motivational_weight: float [0.0–1.0] — motivational salience weighting
  drive_coordination: float [0.0–1.0] — coordination of multiple drives
  ltn_threat_response: float [0.0–1.0] — threat-driven activation
  lateral_tuberal_composite: float [0.0–1.0] — total LTN output

CITATIONS:
    PMC10135972 — Vraka K, Mytilinaios D, Katsenos AP et al. (2023). Cellular
        Localization of Orexin 1 Receptor in Human Hypothalamus. Neuropeptides.
    PMC12293592 — Chen X, Wang Y, Fu S et al. (2025). The Integrated Function of
        the Lateral Hypothalamus in Energy Homeostasis. Nat Commun.
"""

from brain.base_mechanism import BrainMechanism


class LateralTuberalNucleusOutput(BrainMechanism):
    """
    Lateral tuberal nucleus: general drive integration.

    Models the LTN as a general-purpose drive integrator.
    """

    STATE_FIELDS = [
        "ltn_integrator", "motivational_weight", "drive_coordination",
        "ltn_threat_response", "lateral_tuberal_composite", "tick_count",
    ]

    INTEGRATOR_GAIN = 0.50
    THREAT_GAIN = 0.45

    def __init__(self, name: str = "LateralTuberalNucleusOutput",
                 human_analog: str = "Lateral tuberal nucleus — drive integrator",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["ltn_integrator"] = 0.40
        self.state["motivational_weight"] = 0.30
        self.state["drive_coordination"] = 0.40
        self.state["ltn_threat_response"] = 0.0
        self.state["lateral_tuberal_composite"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        feeding = prior.get("FeedingStressIntegrator", {}).get("feeding_drive", 0.30)
        thirst = prior.get("FacialGradientSensor", {}).get("thirst_drive", 0.20)
        sexual = prior.get("ThermoSexualBalancer", {}).get("sexual_motivation", 0.30)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        amygdala = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)

        # LTN integrator: sums all drives
        drive_sum = feeding + thirst + sexual + arousal
        ltn_integrator = min(1.0, drive_sum * self.INTEGRATOR_GAIN * 0.25)

        # Motivational weight: highest drive dominates
        drives = [feeding, thirst, sexual, arousal]
        max_drive = max(drives)
        motivational_weight = max_drive

        # Drive coordination: how well competing drives are coordinated
        # Low variance = well-coordinated; high variance = conflict
        drive_mean = sum(drives) / len(drives)
        drive_variance = sum((d - drive_mean) ** 2 for d in drives) / len(drives)
        drive_coordination = max(0.0, 1.0 - drive_variance * 2.0)

        # LTN threat response: stress and amygdala activate LTN
        ltn_threat = stress * self.THREAT_GAIN + amygdala * 0.30
        ltn_threat_response = min(1.0, ltn_threat)

        # Lateral tuberal composite
        lateral_tuberal_composite = (ltn_integrator + motivational_weight + ltn_threat_response) / 3.0

        # --- Persist ---
        self.state["ltn_integrator"] = round(ltn_integrator, 4)
        self.state["motivational_weight"] = round(motivational_weight, 4)
        self.state["drive_coordination"] = round(drive_coordination, 4)
        self.state["ltn_threat_response"] = round(ltn_threat_response, 4)
        self.state["lateral_tuberal_composite"] = round(lateral_tuberal_composite, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ltn_integrator": round(ltn_integrator, 4),
            "motivational_weight": round(motivational_weight, 4),
            "drive_coordination": round(drive_coordination, 4),
            "ltn_threat_response": round(ltn_threat_response, 4),
            "lateral_tuberal_composite": round(lateral_tuberal_composite, 4),
        }
