"""
Build 61: Foundational061VentromedialDorsalLink — VMH Dorsal Integration
====================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — ventromedial hypothalamus dorsal zone)
  Filename: brain/foundational/Foundational061VentromedialDorsalLink.py
  Instance name: VentromedialDorsalLink

NEURAL SUBSTRATE:
  Ventromedial hypothalamus (VMH) dorsal zone — integrates metabolic
  state with defensive behaviors. VMH contains SF-1 (steroidogenic
  factor 1) neurons that project to:
  - Periaqueductal gray (defensive behaviors)
  - Dorsomedial hypothalamus (behavioral arousal)
  - Anterior hypothalamus (thermoregulation)

  The VMH is estrogen-responsive (aromatase converts testosterone to
  estrogen locally). High estrogen enhances VMH-mediated defensive
  behavior. VMH lesions cause hyperphagia and obesity (VMH obesity
  syndrome in rats).

  KEY FUNCTION: The VMH is the site where glucocorticoids act to
  produce "stress-induced eating" — cortisol stimulates VMH neurons
  that drive food-seeking.

  Human analog: metabolic obesity, stress eating, VMH dysfunction.

Output keys:
  vmh_defensive_output: float [0.0–1.0] — VMH defensive activation
  metabolic_defensive_link: float [0.0–1.0] — stress-eating metabolic link
  estrogen_vmh_modulation: float [0.0–1.0] — estrogen enhancement of VMH
  glucocorticoid_feedback: float [0.0–1.0] — cortisol feedback to VMH
  vmh_dorsal_integrator: float [0.0–1.0] — composite VMH dorsal output

CITATIONS:
    PMC4875659 — Sokolowski K, Tran T, Esumi S et al. (2016). Molecular and Behavioral
        Profiling of Dbx1-Derived Neurons in the Arcuate, Lateral and Ventromedial
        Hypothalamic Nuclei. Front Neural Circuits.
    PMC3930178 — Hahn JD, Swanson LW (2012). Connections of the Lateral Hypothalamic
        Area Juxtadorsomedial Region in the Male Rat. J Comp Neurol.
"""

from brain.base_mechanism import BrainMechanism


class VentromedialDorsalLink(BrainMechanism):
    """
    VMH dorsal: defensive output, stress-eating link, estrogen modulation.

    Models VMH as the metabolic-defensive integration site.
    """

    STATE_FIELDS = [
        "vmh_defensive_output", "metabolic_defensive_link", "estrogen_vmh_modulation",
        "glucocorticoid_feedback", "vmh_dorsal_integrator", "tick_count",
    ]

    DEFENSIVE_GAIN = 0.50
    EAT_GAIN = 0.55

    def __init__(self, name: str = "VentromedialDorsalLink",
                 human_analog: str = "VMH dorsal zone — metabolic-defensive integration",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["vmh_defensive_output"] = 0.30
        self.state["metabolic_defensive_link"] = 0.20
        self.state["estrogen_vmh_modulation"] = 0.30
        self.state["glucocorticoid_feedback"] = 0.20
        self.state["vmh_dorsal_integrator"] = 0.30
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        estrogen = prior.get("EstrogenSignal", {}).get("estrogen_level", 0.40)
        cortisol = prior.get("AutonomicSecretionLink", {}).get("cortisol_level", 0.40)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        amygdala = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        pag = prior.get("VocalAutonomicLink", {}).get("vocal_defensive_response", 0.0)

        # VMH defensive output: PAG and amygdala inputs
        vmh_defensive = amygdala * self.DEFENSIVE_GAIN
        vmh_defensive += pag * 0.30
        vmh_defensive_output = min(1.0, vmh_defensive)

        # Metabolic-defensive link: cortisol drives stress eating via VMH
        metabolic_defensive_link = cortisol * self.EAT_GAIN
        # High leptin suppresses this link (satiety)
        metabolic_defensive_link *= leptin
        metabolic_defensive_link = min(1.0, metabolic_defensive_link)

        # Estrogen VMH modulation: estrogen enhances VMH defensive output
        estrogen_vmh_modulation = estrogen * self.DEFENSIVE_GAIN * 0.50

        # Glucocorticoid feedback: cortisol modulates VMH activity
        glucocorticoid_feedback = cortisol * 0.30
        # But cortisol also acts as negative feedback on stress-eating VMH
        glucocorticoid_feedback = max(0.0, glucocorticoid_feedback - stress * 0.10)

        # VMH dorsal integrator
        vmh_dorsal_integrator = (
            vmh_defensive_output * 0.30 +
            metabolic_defensive_link * 0.40 +
            estrogen_vmh_modulation * 0.30
        )

        # --- Persist ---
        self.state["vmh_defensive_output"] = round(vmh_defensive_output, 4)
        self.state["metabolic_defensive_link"] = round(metabolic_defensive_link, 4)
        self.state["estrogen_vmh_modulation"] = round(estrogen_vmh_modulation, 4)
        self.state["glucocorticoid_feedback"] = round(glucocorticoid_feedback, 4)
        self.state["vmh_dorsal_integrator"] = round(vmh_dorsal_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "vmh_defensive_output": round(vmh_defensive_output, 4),
            "metabolic_defensive_link": round(metabolic_defensive_link, 4),
            "estrogen_vmh_modulation": round(estrogen_vmh_modulation, 4),
            "glucocorticoid_feedback": round(glucocorticoid_feedback, 4),
            "vmh_dorsal_integrator": round(vmh_dorsal_integrator, 4),
        }
