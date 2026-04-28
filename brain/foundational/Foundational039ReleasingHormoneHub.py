"""
Build 39: Foundational039ReleasingHormoneHub — Hypothalamic Releasing Hormones Hub
=============================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — mediobasal hypothalamus, median eminence)
  Filename: brain/foundational/Foundational039ReleasingHormoneHub.py
  Instance name: ReleasingHormoneHub

NEURAL SUBSTRATE:
  Hypothalamic releasing/inhibiting hormones — the hypothalamic command
  signals to the anterior pituitary. All are released from the median
  eminence into the hypothalamic-hypophyseal portal system:

  - CRH (corticotropin-releasing hormone): PVN → ACTH
  - TRH (thyrotropin-releasing hormone): PVN → TSH
  - GnRH (gonadotropin-releasing hormone): ARC/POA → LH/FSH
  - GHRH (growth hormone-releasing hormone): ARC → GH
  - Somatostatin (somatotropin release-inhibiting factor, SRIF): ARC → inhibits GH
  - Dopamine (prolactin-inhibiting factor, PIF): ARC/TIDA → inhibits prolactin
  - Oxytocin (paraventricular nucleus): posterior pituitary → uterus/mammary

  The "master switch" for all endocrine axes — these signals set the
  overall endocrine state of the organism.

  Human analog: endocrine command, hormonal axes.

Output keys:
  releasing_hormone_composite: float [0.0–1.0] — total RH output
  crh_equivalent: float [0.0–1.0] — normalized CRH drive
  trh_equivalent: float [0.0–1.0] — normalized TRH drive
  gnrh_equivalent: float [0.0–1.0] — normalized GnRH drive
  ghrh_equivalent: float [0.0–1.0] — normalized GHRH drive
  endocrine_axis_balance: float [0.0–1.0] — HPA-HPT-HPG axis coordination

CITATIONS:
    PMC9574777 — Núñez L, Bird GS, Hernando-Pérez E et al. (2019). Store-Operated
        Ca2+ Entry and Ca2+ Responses to Hypothalamic Releasing Hormones in Anterior
        Pituitary Cells. Cell Calcium.
    PMC11011867 — Santiago-Andres Y, Aquiles A, Taniguchi-Ponciano K et al. (2024).
        Association Between Intracellular Calcium Signaling and Tumor Recurrence in
        Human Non-Functioning Pituitary Adenomas. Cancers.
"""

from brain.base_mechanism import BrainMechanism


class ReleasingHormoneHub(BrainMechanism):
    """
    Hypothalamic releasing hormone hub: all hypothalamic-pituitary axes.

    Combines all hypothalamic releasing hormones into a composite
    endocrine command output.
    """

    STATE_FIELDS = [
        "releasing_hormone_composite", "crh_equivalent", "trh_equivalent",
        "gnrh_equivalent", "ghrh_equivalent", "endocrine_axis_balance", "tick_count",
    ]

    CRH_GAIN = 0.60
    TRH_GAIN = 0.55
    GNRH_GAIN = 0.50
    GHRH_GAIN = 0.50

    def __init__(self, name: str = "ReleasingHormoneHub",
                 human_analog: str = "Hypothalamus — releasing hormone hub",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["releasing_hormone_composite"] = 0.40
        self.state["crh_equivalent"] = 0.30
        self.state["trh_equivalent"] = 0.40
        self.state["gnrh_equivalent"] = 0.30
        self.state["ghrh_equivalent"] = 0.40
        self.state["endocrine_axis_balance"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        crh = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        trh = prior.get("ThyroidAxisController", {}).get("trh_level", 0.40)
        gnrh = prior.get("GnRHReintegration", {}).get("gnrh_pulse_frequency", 0.30)
        ghrh = prior.get("GrowthHormoneReleasingHormone", {}).get("ghrh_level", 0.30)
        somatostatin = prior.get("SomatostatinInhibitor", {}).get("somatostatin_level", 0.20)
        dopamine = prior.get("DopamineTIDA", {}).get("dopamine_tone", 0.30)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)

        # Normalize each releasing hormone
        crh_equiv = min(1.0, crh * self.CRH_GAIN)
        trh_equiv = min(1.0, trh * self.TRH_GAIN)
        gnrh_equiv = min(1.0, gnrh * self.GNRH_GAIN)
        ghrh_raw = max(0.0, ghrh * self.GHRH_GAIN - somatostatin * 0.30)
        ghrh_equiv = min(1.0, ghrh_raw)

        # Composite releasing hormone output
        composite = (crh_equiv + trh_equiv + gnrh_equiv + ghrh_equiv) / 4.0

        # Endocrine axis balance: stress suppresses HPG/HPT but drives HPA
        stress_suppression = stress * 0.40
        axis_balance = (1.0 - stress_suppression) * 0.50 + (crh_equiv * 0.50)

        # --- Persist ---
        self.state["releasing_hormone_composite"] = round(composite, 4)
        self.state["crh_equivalent"] = round(crh_equiv, 4)
        self.state["trh_equivalent"] = round(trh_equiv, 4)
        self.state["gnrh_equivalent"] = round(gnrh_equiv, 4)
        self.state["ghrh_equivalent"] = round(ghrh_equiv, 4)
        self.state["endocrine_axis_balance"] = round(axis_balance, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "releasing_hormone_composite": round(composite, 4),
            "crh_equivalent": round(crh_equiv, 4),
            "trh_equivalent": round(trh_equiv, 4),
            "gnrh_equivalent": round(gnrh_equiv, 4),
            "ghrh_equivalent": round(ghrh_equiv, 4),
            "endocrine_axis_balance": round(axis_balance, 4),
        }
