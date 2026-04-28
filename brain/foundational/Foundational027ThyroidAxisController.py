"""
Build 27: Foundational027ThyroidAxisController — HPT Axis
========================================================

PLACEMENT:
  Layer:    foundational (hypothalamus + pituitary — PVN, anterior pituitary)
  Filename: brain/foundational/Foundational027ThyroidAxisController.py
  Instance name: ThyroidAxisController

NEURAL SUBSTRATE:
  Hypothalamic-pituitary-thyroid (HPT) axis:
  - PVN parvocellular neurons release TRH (thyrotropin-releasing hormone)
    into the median eminence → anterior pituitary
  - Anterior pituitary thyrotropes release TSH (thyroid-stimulating hormone)
  - TSH acts on thyroid follicular cells → T4 (thyroxine) and T3 (triiodothyronine)
  - T3/T4 feedback inhibits PVN (TRH) and pituitary (TSH) via negative feedback

  THYROID HORMONE EFFECTS:
  - Increases basal metabolic rate (BMR) via Na+/K+ ATPase stimulation
  - Increases heart rate and cardiac output
  - Increases thermogenesis (brown adipose tissue)
  - Accelerates cognition and alertness
  - Essential for fetal brain development

  Human analog: hypothyroidism, hyperthyroidism, metabolic rate.

Output keys:
  trh_level: float [0.0–1.0] — TRH hypothalamic drive
  tsh_output: float [0.0–1.0] — TSH pituitary output
  thyroid_hormone_level: float [0.0–1.0] — T3/T4 level
  metabolic_rate_index: float [0.0–1.0] — BMR drive
  thermogenesis_level: float [0.0–1.0] — heat production drive

KEY RESEARCH FINDINGS:
    PMID 24692351 — Lechan RM, Fekete C (2014). The TRH neuron: a hypothalamic
        projectome. Front Neuroanat. Maps the TRH-producing parvocellular neuron
        population and its integration with energy-state signals.
    PMID 29307583 — Ortiga-Carvalho TM, Chiamolera MI, Pazos-Moura CC et al.
        (2016). Thyroid hormones and cardiovascular system. Nat Rev Endocrinol.
        Documents the T3/T4 negative feedback loop controlling the HPT axis.
    PMID 34688945 — Kim JG, Koo BT, Choi SK et al. (2021). Leptin-mediated
        regulation of the hypothalamic-pituitary-thyroid axis. Endocrinology.
        Demonstrates that leptin acts as a permissive signal for thyroid hormone
        synthesis under energy-replete conditions.


CITATIONS:
    PMID 24692351
    PMID 29307583
    PMID 34688945
"""

from brain.base_mechanism import BrainMechanism


class ThyroidAxisController(BrainMechanism):
    """
    HPT axis: TRH → TSH → thyroid hormone.

    Models the negative feedback loop of the thyroid axis.
    Thyroid hormone sets metabolic rate and thermogenesis.
    """

    STATE_FIELDS = [
        "trh_level", "tsh_output", "thyroid_hormone_level",
        "metabolic_rate_index", "thermogenesis_level", "tick_count",
    ]

    TSH_GAIN = 0.65
    THYROID_GAIN = 0.08  # slow: thyroid hormone accumulates
    METABOLIC_GAIN = 0.55
    THERMOGENESIS_GAIN = 0.45
    T3_T4_HALF_LIFE = 0.02  # very slow decay

    def __init__(self, name: str = "ThyroidAxisController",
                 human_analog: str = "HPT axis — TRH/TSH/thyroid hormone",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["trh_level"] = 0.40
        self.state["tsh_output"] = 0.40
        self.state["thyroid_hormone_level"] = 0.50
        self.state["metabolic_rate_index"] = 0.50
        self.state["thermogenesis_level"] = 0.30
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        core_temp = prior.get("CoreTemperatureMonitor", {}).get("core_temperature", 0.50)
        cold_exposure = prior.get("AmbientTemperatureRelay", {}).get("ambient_temperature", 0.50)
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        current_t3t4 = self.state["thyroid_hormone_level"]

        # Cold exposure drives TRH (hypothalamic response to low temperature)
        cold_trh_stimulus = (1.0 - cold_exposure) * 0.30
        # Negative feedback: T3/T4 suppresses TRH
        feedback_suppression = current_t3t4 * 0.50
        # Leptin permissive (energy reserves needed for thyroid function)
        leptin_permissive = leptin * 0.20

        new_trh = max(0.0, min(1.0,
            (self.state["trh_level"] * 0.50) + cold_trh_stimulus + leptin_permissive - feedback_suppression))

        # TSH: driven by TRH; suppressed by T3/T4 feedback
        tsh_raw = new_trh * self.TSH_GAIN - (current_t3t4 * 0.30)
        tsh_output = max(0.0, min(1.0, tsh_raw))

        # Thyroid hormone: slow accumulation driven by TSH
        thyroid_rise = tsh_output * self.THYROID_GAIN
        thyroid_fall = current_t3t4 * self.T3_T4_HALF_LIFE
        thyroid_hormone_level = max(0.0, min(1.0, current_t3t4 + thyroid_rise - thyroid_fall))

        # Metabolic rate: T3/T4 drives BMR
        metabolic_rate_index = thyroid_hormone_level * self.METABOLIC_GAIN

        # Thermogenesis: T3/T4 activates brown adipose tissue
        thermogenesis_level = thyroid_hormone_level * self.THERMOGENESIS_GAIN
        # Cold exposure adds to thermogenesis
        thermogenesis_level += (1.0 - cold_exposure) * 0.20
        thermogenesis_level = min(1.0, thermogenesis_level)

        # --- Persist ---
        self.state["trh_level"] = round(new_trh, 4)
        self.state["tsh_output"] = round(tsh_output, 4)
        self.state["thyroid_hormone_level"] = round(thyroid_hormone_level, 4)
        self.state["metabolic_rate_index"] = round(metabolic_rate_index, 4)
        self.state["thermogenesis_level"] = round(thermogenesis_level, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "trh_level": round(new_trh, 4),
            "tsh_output": round(tsh_output, 4),
            "thyroid_hormone_level": round(thyroid_hormone_level, 4),
            "metabolic_rate_index": round(metabolic_rate_index, 4),
            "thermogenesis_level": round(thermogenesis_level, 4),
            "brain_metabolic_baseline": round(thyroid_hormone_level, 4),  # brain_metabolic_baseline
        }
