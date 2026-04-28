"""
Build 59: Foundational059ArcuateNPYAGRPOutput — Arcuate NPY/AgRP Hunger System
=========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — arcuate nucleus, NPY/AgRP neurons)
  Filename: brain/foundational/Foundational059ArcuateNPYAGRPOutput.py
  Instance name: ArcuateNPYAGRPOutput

NEURAL SUBSTRATE:
  Arcuate nucleus NPY/AgRP neurons — the orexigenic (hunger) population.
  These neurons are the most potent appetite-stimulators known:
  - NPY (neuropeptide Y): injection into hypothalamus → voracious eating
  - AgRP (agouti-related peptide): antagonist of MC3/4R → blocks α-MSH

  NPY/AgRP NEURONS:
  - Activated by: ghrelin (from stomach), leptin deficiency, fasting
  - Inhibited by: leptin, insulin, α-MSH (negative feedback)
  - Project to: LHA (orexin), PVN (suppress CRH), parabrachial nucleus

  NEURAL CIRCUIT FOR FEEDING:
  Leptin deficiency → ARC NPY/AgRP activated → LHA orexin activated → feeding

  KEY: NPY acts via Y1 and Y5 receptors. AgRP blocks MC4R (melanocortin
  receptor). The MC4R pathway is the final common pathway for energy
  balance — both α-MSH (anorexigenic) and AgRP (orexigenic) compete
  for the same receptor.

  Human analog: ghrelin hunger, NPY-driven hyperphagia, leptin deficiency.

Output keys:
  npy_level: float [0.0–1.0] — NPY output level
  agrp_output: float [0.0–1.0] — AgRP output
  hunger_drive: float [0.0–1.0] — net orexigenic drive
  mc4r_competition: float [-1.0 to 1.0] — AgRP vs α-MSH competition at MC4R
  arcuate_hunger_integrator: float [0.0–1.0] — composite NPY/AgRP output

CITATIONS:
    PMC3467268 — Martins L, Fernández-Mallo D, Novelle MG et al. (2012). Hypothalamic
        mTOR Signaling Mediates the Orexigenic Action of Ghrelin. PLoS ONE.
    PMC4808343 — Cabral A, Portiansky E, Sánchez-Jaramillo E et al. (2016). Ghrelin
        Activates Hypophysiotropic Corticotropin-Releasing Factor Neurons Independently
        of the Arcuate Nucleus. J Neuroendocrinol.
"""

from brain.base_mechanism import BrainMechanism


class ArcuateNPYAGRPOutput(BrainMechanism):
    """
    ARC NPY/AgRP: ghrelin hunger, orexigenic drive, MC4R competition.

    Models NPY/AgRP neurons as the arcuate hunger signal.
    """

    STATE_FIELDS = [
        "npy_level", "agrp_output", "hunger_drive",
        "mc4r_competition", "arcuate_hunger_integrator", "tick_count",
    ]

    NPY_GAIN = 0.60
    AGROP_GAIN = 0.55

    def __init__(self, name: str = "ArcuateNPYAGRPOutput",
                 human_analog: str = "Arcuate NPY/AgRP — orexigenic neurons",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["npy_level"] = 0.30
        self.state["agrp_output"] = 0.25
        self.state["hunger_drive"] = 0.30
        self.state["mc4r_competition"] = 0.0
        self.state["arcuate_hunger_integrator"] = 0.30
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        ghrelin = prior.get("GutSignalRelay", {}).get("ghrelin_signal", 0.20)
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        glucose = prior.get("GlucoseMonitor", {}).get("glucose_level", 0.50)
        insulin = prior.get("InsulinSignal", {}).get("insulin_level", 0.30)
        alpha_msh = prior.get("ArcuatePOMCOutput", {}).get("alpha_msh_output", 0.0)
        pomc_inhibition = prior.get("ArcuatePOMCOutput", {}).get("pomc_activity", 0.30)

        # NPY level: activated by ghrelin, leptin deficiency; inhibited by leptin + insulin
        leptin_inhibition = leptin * 0.45
        insulin_inhibition = insulin * 0.30
        glucose_inhibition = glucose * 0.20
        ghrelin_activates = ghrelin * 0.50
        npy_raw = ghrelin_activates - leptin_inhibition - insulin_inhibition - glucose_inhibition
        npy_level = min(1.0, max(0.0, npy_raw))

        # AgRP output: similar activation pattern to NPY
        agrp_raw = ghrelin * 0.45 - leptin * 0.40 - insulin * 0.25
        agrp_output = min(1.0, max(0.0, agrp_raw))

        # Hunger drive: net orexigenic drive
        hunger_drive = (npy_level * 0.50) + (agrp_output * 0.50)

        # MC4R competition: AgRP blocks MC4R; α-MSH activates MC4R
        # Positive = AgRP dominance (hunger); Negative = α-MSH dominance (satiety)
        mc4r_competition = agrp_output - alpha_msh * 0.80
        mc4r_competition = max(-1.0, min(1.0, mc4r_competition))

        # Arcuate hunger integrator
        arcuate_hunger_integrator = (npy_level + agrp_output + hunger_drive) / 3.0

        # --- Persist ---
        self.state["npy_level"] = round(npy_level, 4)
        self.state["agrp_output"] = round(agrp_output, 4)
        self.state["hunger_drive"] = round(hunger_drive, 4)
        self.state["mc4r_competition"] = round(mc4r_competition, 4)
        self.state["arcuate_hunger_integrator"] = round(arcuate_hunger_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "npy_level": round(npy_level, 4),
            "agrp_output": round(agrp_output, 4),
            "hunger_drive": round(hunger_drive, 4),
            "mc4r_competition": round(mc4r_competition, 4),
            "arcuate_hunger_integrator": round(arcuate_hunger_integrator, 4),
        }
