"""
Build 19: Foundational010AppetiteNPYBalancer — Arcuate NPY/AgRP vs POMC Balance
==========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamic — arcuate nucleus)
  Filename: brain/foundational/Foundational010AppetiteNPYBalancer.py
  Instance name: AppetiteNPYBalancer

NEURAL SUBSTRATE:
  Arcuate nucleus (Arc) of the hypothalamus contains two
  counteracting neuron populations:
  - NPY/AgRP neurons: orexigenic (hunger-promoting). Fire during
    energy deficit. Release neuropeptide Y (NPY) and agouti-related
    peptide (AgRP), an antagonist at melanocortin receptors.
    Strongly activated by ghrelin (the "hunger hormone").
  - POMC neurons: anorexigenic (satiety-promoting). Process
    proopiomelanocortin (POMC) into α-MSH, which activates
    melanocortin-4 receptors (MC4R) to reduce food intake.
    Activated by leptin (the "satiety hormone").

  The balance between NPY/AgRP and POMC drives hunger vs
  satiety. MC4R activation is the critical downstream signal:
  MC4R knockout mice are obese regardless of NPY/AgRP status.
  This mechanism models the NPY/AgRP vs POMC balance as a
  continuous hunger-satiety axis.

KEY FINDINGS:
  1. NPY is one of the most potent appetite stimulators known:
     microinjection of NPY into the paraventricular nucleus (PVN)
     causes immediate, robust feeding behavior — 10× baseline food
     intake within 1 hour (Clark et al. 1984, Regul Pept).
  2. AgRP antagonizes MC3R/MC4R melanocortin receptors:
     AgRP increases food intake via disinhibition of feeding
     circuits (Ollmann et al. 1997, J Neurosci).
  3. POMC neurons are activated by leptin: leptin-deficient
     (ob/ob) mice have reduced POMC activity → hyperphagia
     and obesity (Schwartz et al. 1996, Nat Neurosci).
  4. Ghrelin activates NPY/AgRP neurons directly via the
     "ghrelin receptor" GHSR-1a in the arcuate nucleus —
     ghrelin rises before meals and falls after feeding
     (Wren et al. 2001, J Clin Endocrinol Metab).
  5. MC4R signaling in the paraventricular nucleus of the
     hypothalamus is necessary for energy balance: PVN MC4R
     loss causes hyperphagia independent of arcuate activity
     (Bhasin et al. 2020, Cell Metab).

INPUTS (prior_results):
  - Homeostat: metabolic_state (str: "hungry" | "fed" | "satiated")
  - StressActivationAxis: crh_level (float 0-1)
  - ArousalRegulator: arousal_level (float 0-1)
  - GutSignalRelay: gut_distress (float 0-1)

OUTPUTS:
  - hunger_drive: float 0.0-1.0 (net orexigenic drive from NPY/AgRP)
  - satiety_signal: float 0.0-1.0 (anorexigenic signal from POMC/α-MSH)
  - net_appetitive_balance: float -1.0 to +1.0 (hunger minus satiety)
  - melanocortin_tone: float 0.0-1.0 (MC4R activation level)

CITATIONS:
    PMC2766111 — Higuchi H, Niki T, Shiiya T (2008). Feeding Behavior and Gene
        Expression of Appetite-Related Neuropeptides in Mice Lacking NPY Y5 Receptor.
        Brain Res.
    PMC3759582 — Teubner BJ, Bartness TJ (2013). PYY(3-36) into the Arcuate Nucleus
        Inhibits Food Deprivation-Induced Increases in Food Hoarding and Intake.
        Am J Physiol Regul Integr Comp Physiol.
"""

from brain.base_mechanism import BrainMechanism


class AppetiteNPYBalancer(BrainMechanism):
    """
    Arcuate nucleus — NPY/AgRP vs POMC hunger-satiety balance.

    NPY/AgRP neurons promote feeding (orexigenic). POMC neurons
    suppress it (anorexigenic via α-MSH/MC4R). Net balance drives
    appetitive motivation.
    """

    # Baseline hunger drive (post-absorptive = moderate)
    BASELINE_HUNGER = 0.40

    # NPY/AgRP sensitivity to metabolic state
    METABOLIC_SENSITIVITY = 0.35

    def __init__(self):
        super().__init__(
            name="AppetiteNPYBalancer",
            human_analog=(
                "Arcuate nucleus — NPY/AgRP orexigenic neurons vs "
                "POMC anorexigenic neurons, MC4R-mediated satiety signaling"
            ),
            layer="foundational",
        )
        self.state.setdefault("hunger_drive", self.BASELINE_HUNGER)
        self.state.setdefault("satiety_signal", 0.30)
        self.state.setdefault("net_appetitive_balance", 0.10)
        self.state.setdefault("melanocortin_tone", 0.30)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        metabolic_state = prior.get("Homeostat", {}).get("metabolic_state", "fed")
        crh_level = prior.get("StressActivationAxis", {}).get("crh_level", 0.0)
        arousal_level = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        gut_distress = prior.get("GutSignalRelay", {}).get("gut_distress", 0.0)

        # ---- Metabolic state → NPY/AgRP drive ----
        if metabolic_state == "hungry":
            npy_drive = 0.70 + self.METABOLIC_SENSITIVITY
        elif metabolic_state == "fed":
            npy_drive = self.BASELINE_HUNGER
        else:  # satiated
            npy_drive = 0.15

        # ---- Stress suppresses hunger (fight overrides feeding) ----
        stress_suppression = crh_level * 0.40
        npy_drive = max(0.05, npy_drive - stress_suppression)

        # ---- Gut distress suppresses appetite (nausea) ----
        npy_drive = max(0.05, npy_drive - gut_distress * 0.50)

        # ---- Satiety signal from POMC ----
        if metabolic_state == "satiated":
            pomc_signal = 0.75
        elif metabolic_state == "fed":
            pomc_signal = 0.40
        else:
            pomc_signal = 0.15

        # Arousal coupling: high arousal (active exploration) suppresses POMC slightly
        pomc_signal -= (arousal_level - 0.5) * 0.10
        pomc_signal = max(0.05, min(0.90, pomc_signal))

        # ---- Net balance: hunger drive minus satiety signal ----
        net_balance = npy_drive - pomc_signal
        net_balance = round(max(-1.0, min(1.0, net_balance)), 4)

        # ---- Melanocortin tone (MC4R activation) ----
        # MC4R activation = inverse of NPY/AgRP activity
        melanocortin_tone = round(pomc_signal * (1.0 - npy_drive * 0.5), 4)

        # ---- Hunger drive (bounded) ----
        hunger_drive = round(max(0.05, min(0.95, npy_drive)), 4)
        satiety_signal = round(max(0.05, min(0.90, pomc_signal)), 4)

        # Persist
        self.state["hunger_drive"] = hunger_drive
        self.state["satiety_signal"] = satiety_signal
        self.state["net_appetitive_balance"] = net_balance
        self.state["melanocortin_tone"] = melanocortin_tone
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "hunger_drive": hunger_drive,
            "satiety_signal": satiety_signal,
            "net_appetitive_balance": net_balance,
            "melanocortin_tone": melanocortin_tone,
        }
