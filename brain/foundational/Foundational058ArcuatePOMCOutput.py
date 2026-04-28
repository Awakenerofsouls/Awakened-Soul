"""
Build 58: Foundational058ArcuatePOMCOutput — Arcuate POMC/CART Satiety System
==========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — arcuate nucleus, POMC neurons)
  Filename: brain/foundational/Foundational058ArcuatePOMCOutput.py
  Instance name: ArcuatePOMCOutput

NEURAL SUBSTRATE:
  Arcuate nucleus POMC neurons — the anorexigenic (satiety) population.
  POMC is cleaved into α-MSH (alpha-melanocyte-stimulating hormone),
  which acts on MC4R receptors in the PVN and LHA to suppress feeding.
  CART (cocaine-and-amphetamine-regulated transcript) is co-released
  and is also anorexigenic.

  POMC NEURONS:
  - Activated by: leptin (via leptin receptors on POMC neurons)
  - Inhibited by: ghrelin (via NPY/AgRP interneurons)
  - Project to: PVN (MC4R → CRH suppression), LHA (suppresses orexin),
    VTA (reward modulation)

  LEPTIN-POMC AXIS:
  High leptin (from adipose tissue) → POMC activation → α-MSH release →
  MC4R activation → satiety → reduced food intake

  Human analog: leptin-mediated satiety, α-MSH appetite suppression.

Output keys:
  pomc_activity: float [0.0–1.0] — POMC neuron firing rate
  alpha_msh_output: float [0.0–1.0] — α-MSH satiety signal
  cart_output: float [0.0–1.0] — CART anorexigenic output
  leptin_sensitivity: float [0.0–1.0] — responsiveness to leptin signal
  satiety_integrator: float [0.0–1.0] — composite satiety output

CITATIONS:
    PMC2838656 — Zheng H, Patterson LM, Rhodes CJ et al. (2010). A Potential Role
        for Hypothalamomedullary POMC Projections in Leptin-Induced Suppression of
        Food Intake. Brain Res.
    PMC8037945 — Jang Y, Heo JY, Lee MJ et al. (2021). Angiopoietin-Like Growth
        Factor Involved in Leptin Signaling in the Hypothalamus. Int J Mol Sci.
"""

from brain.base_mechanism import BrainMechanism


class ArcuatePOMCOutput(BrainMechanism):
    """
    ARC POMC: α-MSH satiety, CART, leptin-mediated anorexia.

    Models POMC neurons as the arcuate satiety signal.
    """

    STATE_FIELDS = [
        "pomc_activity", "alpha_msh_output", "cart_output",
        "leptin_sensitivity", "satiety_integrator", "tick_count",
    ]

    POMC_GAIN = 0.55
    ALPHA_MSH_GAIN = 0.60
    CART_GAIN = 0.50

    def __init__(self, name: str = "ArcuatePOMCOutput",
                 human_analog: str = "Arcuate POMC — α-MSH satiety neurons",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["pomc_activity"] = 0.40
        self.state["alpha_msh_output"] = 0.35
        self.state["cart_output"] = 0.30
        self.state["leptin_sensitivity"] = 0.50
        self.state["satiety_integrator"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        glucose = prior.get("GlucoseMonitor", {}).get("glucose_level", 0.50)
        ghrelin = prior.get("GutSignalRelay", {}).get("ghrelin_signal", 0.20)
        insulin = prior.get("InsulinSignal", {}).get("insulin_level", 0.30)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)

        # Leptin sensitivity: changes with metabolic state
        # Low leptin (leptin resistance) reduces sensitivity
        leptin_sensitivity = leptin * 0.50 + (1.0 - ghrelin) * 0.30

        # POMC activity: activated by leptin + insulin + glucose
        leptin_activates = leptin * leptin_sensitivity
        insulin_activates = insulin * 0.30
        glucose_activates = glucose * 0.20
        # Ghrelin and stress suppress POMC
        ghrelin_suppresses = ghrelin * 0.30
        stress_suppresses = stress * 0.25
        pomc_raw = leptin_activates + insulin_activates + glucose_activates - ghrelin_suppresses - stress_suppresses
        pomc_activity = min(1.0, max(0.0, pomc_raw))

        # α-MSH output: proportional to POMC activity
        alpha_msh_output = pomc_activity * self.ALPHA_MSH_GAIN

        # CART output: co-released with α-MSH
        cart_output = pomc_activity * self.CART_GAIN

        # Satiety integrator
        satiety_integrator = (alpha_msh_output + cart_output) / 2.0

        # --- Persist ---
        self.state["pomc_activity"] = round(pomc_activity, 4)
        self.state["alpha_msh_output"] = round(alpha_msh_output, 4)
        self.state["cart_output"] = round(cart_output, 4)
        self.state["leptin_sensitivity"] = round(leptin_sensitivity, 4)
        self.state["satiety_integrator"] = round(satiety_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pomc_activity": round(pomc_activity, 4),
            "alpha_msh_output": round(alpha_msh_output, 4),
            "cart_output": round(cart_output, 4),
            "leptin_sensitivity": round(leptin_sensitivity, 4),
            "satiety_integrator": round(satiety_integrator, 4),
        }
