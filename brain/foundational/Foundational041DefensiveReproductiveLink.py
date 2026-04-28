"""
Build 41: Foundational041DefensiveReproductiveLink — HPA-HPG Axis Competition
=========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — PVN interaction with ARC/POA)
  Filename: brain/foundational/Foundational041DefensiveReproductiveLink.py
  Instance name: DefensiveReproductiveLink

NEURAL SUBSTRATE:
  HPA-HPG interaction: stress suppresses reproduction at multiple levels.
  CRH directly inhibits GnRH release from hypothalamus. Cortisol acts on
  the pituitary to suppress LH/FSH. High cortisol also suppresses
  kisspeptin neurons (the GnRH "gatekeeper") via glucocorticoid receptors.

  Conversely, reproductive hormones modulate stress reactivity:
  - Testosterone attenuates HPA axis responses
  - Estrogen can enhance or suppress depending on phase of menstrual cycle

  KEY NEUROANATOMY:
  - PVN (CRH) → suppresses ARC kisspeptin → reduces GnRH → ↓ LH/FSH
  - PVN → suppresses POA → reduced sexual behavior
  - Testosterone → suppresses PVN CRH → reduced stress response

  Human analog: stress-induced infertility, sexual dysfunction under chronic stress.

Output keys:
  hpa_hpg_tradeoff: float [0.0–1.0] — stress-reproduction allocation
  reproductive_suppression: float [0.0–1.0] — HPA inhibition of reproduction
  stress_attenuation: float [0.0–1.0] — reproductive hormone stress buffering
  defensive_priority: float [0.0–1.0] — survival over reproduction priority
  survival_reproduction_balance: float [0.0–1.0] — axis allocation

CITATIONS:
    PMC7687061 — Esteban Masferrer M, Silva BA, Nomoto K et al. (2020). Differential
        Encoding of Predator Fear in the Ventromedial Hypothalamus and Periaqueductal Grey.
        J Neurosci.
    PMC4379496 — Kunwar PS, Zelikowsky M, Remedios R et al. (2015). Ventromedial
        Hypothalamic Neurons Control a Defensive Emotion State. eLife.
"""

from brain.base_mechanism import BrainMechanism


class DefensiveReproductiveLink(BrainMechanism):
    """
    HPA-HPG tradeoff: stress suppresses reproduction; reproduction buffers stress.

    Models the competition between survival (HPA) and reproductive (HPG) axes.
    """

    STATE_FIELDS = [
        "hpa_hpg_tradeoff", "reproductive_suppression", "stress_attenuation",
        "defensive_priority", "survival_reproduction_balance", "tick_count",
    ]

    SUPPRESSION_GAIN = 0.60
    ATTENUATION_GAIN = 0.40
    DEFENSIVE_GAIN = 0.55

    def __init__(self, name: str = "DefensiveReproductiveLink",
                 human_analog: str = "HPA-HPG interaction — stress vs reproduction",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["hpa_hpg_tradeoff"] = 0.30
        self.state["reproductive_suppression"] = 0.10
        self.state["stress_attenuation"] = 0.30
        self.state["defensive_priority"] = 0.40
        self.state["survival_reproduction_balance"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        crh = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        cortisol = prior.get("AutonomicSecretionLink", {}).get("cortisol_level", 0.40)
        gnrh = prior.get("GnRHReintegration", {}).get("gnrh_pulse_frequency", 0.30)
        lh = prior.get("GnRHReintegration", {}).get("lh_output", 0.25)
        testosterone = prior.get("TestosteroneSignal", {}).get("testosterone_level", 0.50)
        estrogen = prior.get("EstrogenSignal", {}).get("estrogen_level", 0.40)

        # HPA-HPG tradeoff: how much stress suppresses reproduction
        stress_suppression = crh * self.SUPPRESSION_GAIN + cortisol * 0.30
        reproductive_suppression = min(1.0, stress_suppression)

        # Stress attenuation: reproductive hormones buffer stress
        testosterone_attenuation = testosterone * self.ATTENUATION_GAIN * 0.50
        estrogen_attenuation = estrogen * self.ATTENUATION_GAIN * 0.30
        stress_attenuation = max(0.0, min(1.0,
            testosterone_attenuation + estrogen_attenuation))

        # Defensive priority: survival over reproduction
        defensive_priority = (crh * self.DEFENSIVE_GAIN + cortisol * 0.30) * 0.50

        # HPA-HPG tradeoff: balance between axes
        hpa_drive = crh + cortisol
        hpg_drive = gnrh + lh + testosterone + estrogen
        total_drive = hpa_drive + hpg_drive
        if total_drive > 0:
            tradeoff = hpa_drive / total_drive  # 0 = full HPG, 1 = full HPA
        else:
            tradeoff = 0.5
        hpa_hpg_tradeoff = min(1.0, tradeoff)

        # Survival-reproduction balance
        balance = 0.50 - (defensive_priority * 0.30) + (stress_attenuation * 0.30)
        survival_reproduction_balance = min(1.0, max(0.0, balance))

        # --- Persist ---
        self.state["hpa_hpg_tradeoff"] = round(hpa_hpg_tradeoff, 4)
        self.state["reproductive_suppression"] = round(reproductive_suppression, 4)
        self.state["stress_attenuation"] = round(stress_attenuation, 4)
        self.state["defensive_priority"] = round(defensive_priority, 4)
        self.state["survival_reproduction_balance"] = round(survival_reproduction_balance, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "hpa_hpg_tradeoff": round(hpa_hpg_tradeoff, 4),
            "reproductive_suppression": round(reproductive_suppression, 4),
            "stress_attenuation": round(stress_attenuation, 4),
            "defensive_priority": round(defensive_priority, 4),
            "survival_reproduction_balance": round(survival_reproduction_balance, 4),
        }
