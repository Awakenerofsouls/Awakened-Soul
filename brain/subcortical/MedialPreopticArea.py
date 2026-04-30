"""
MedialPreopticArea — MPOA — Thermoregulation, Parental & Sexual Behavior

NEURAL SUBSTRATE
================
The medial preoptic area (MPOA) of the anterior hypothalamus is a
multifunctional integrative nucleus that controls thermoregulation,
parental behavior, sexual/courtship behavior, and contributes to NREM
sleep promotion. It sits just rostral and dorsal to the suprachiasmatic
nucleus, dorsal to the optic chiasm.

Cell types:
- Warm-sensitive neurons (WSNs): BDNF/PACAP-expressing neurons that
  fire in response to local hypothalamic warmth and trigger heat-loss
  effectors (vasodilation, sweating/panting, behavioral cooling).
- Galanin (Gal+) neurons: dual roles — promote NREM sleep and heat loss
  (overlap with VLPO Gal+); separate Gal+ population governs parental
  behavior in mice.
- Estrogen receptor-α (ERα) and aromatase neurons: implement female
  receptivity (lordosis) and male copulatory behavior; classic Pfaff
  hormonal-circuit substrate.
- GnRH-projecting integrative cells: relay reproductive signals to ARC
  kisspeptin / pituitary axis.

KEY FINDINGS
============
1. Warm-sensitive POA neurons (BDNF/PACAP) drive hypothermia and cool-
   seeking behavior; activation triggers vasodilation —
   [Tan C 2016, Cell 167:47, doi:10.1016/j.cell.2016.09.016]
2. Galanin neurons in the ventrolateral/medial preoptic area promote
   NREM sleep and heat loss in mice.
   [Kroeger D 2018, Nat Commun 9:4129, doi:10.1038/s41467-018-06590-7]
3. Galanin neurons in the medial preoptic area govern parental behavior
   in male and female mice.
   [Wu Z 2014, Nature 509:325, doi:10.1038/nature13307]
4. Hypothalamic regulation of sleep/circadian rhythms; MPOA-VLPO flip-flop.
   [Saper C 2005, Nature 437:1257, doi:10.1038/nature04284]
5. Estrogen receptor systems in the hypothalamus underpin female sexual
   behavior; lordosis circuit substrate.
   [Pfaff D 1973, Brain Res 54:135, doi:10.1016/0006-8993(73)90040-0]
6. Vasopressin/oxytocin sex-difference review covers MPOA peptidergic
   social-behavior modulation.
   [Dumais K 2016, Front Neuroendocrinol 40:1, doi:10.1016/j.yfrne.2015.04.003]

INPUTS
======
- DorsomedialHypothalamus.dmh_drive (thermal/stress)
- VentrolateralPreoptic.vlpo_drive (sleep coupling)
- MedialAmygdalaPosterior.social_signal (pup/mate cues)
- ParaventricularNucleusHypothalamus.pvn_drive (stress modulation)
- (thermal_input proxy — not always present)

OUTPUTS
=======
- mpoa_drive (0-1)
- heat_loss_signal (0-1) — vasodilation/cooling
- nrem_promoter_signal (0-1) — Gal+ sleep
- parental_signal (0-1) — Gal+ parental
- sexual_behavior_signal (0-1) — ERα female/male
- gnrh_modulation (0-1)
- mpoa_state (str): "thermoregulating" | "parental" | "sexual" |
                    "nrem_promoting" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class MedialPreopticArea(BrainMechanism):
    """MPOA — preoptic integrative nucleus."""

    BASELINE = 0.10
    SMOOTH = 0.20
    HEAT_THRESHOLD = 0.40
    PARENTAL_THRESHOLD = 0.40
    SEXUAL_THRESHOLD = 0.40
    NREM_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="MedialPreopticArea",
            human_analog="MPOA (thermoregulation, parental, sexual)",
            layer="subcortical",
        )
        self.state.setdefault("mpoa_drive", self.BASELINE)
        self.state.setdefault("heat_loss_signal", 0.0)
        self.state.setdefault("nrem_promoter_signal", 0.0)
        self.state.setdefault("parental_signal", 0.0)
        self.state.setdefault("sexual_behavior_signal", 0.0)
        self.state.setdefault("gnrh_modulation", 0.0)
        self.state.setdefault("mpoa_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("parental_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, dmh: float, vlpo: float,
                       social: float, pvn: float, thermal: float) -> float:
        """Composite MPOA drive (Saper 2005 — integrative hub)."""
        target = (self.BASELINE
                  + dmh * 0.20
                  + vlpo * 0.20
                  + social * 0.25
                  + pvn * 0.10
                  + thermal * 0.30)
        return min(1.0, target)

    def _heat_loss(self, drive: float, thermal: float) -> float:
        """Warm-sensitive neuron output (Tan 2016)."""
        # WSNs fire to local thermal warmth + drive
        if thermal < 0.15 and drive < 0.15:
            return 0.0
        return min(1.0, thermal * 0.65 + drive * 0.30)

    def _nrem_promoter(self, drive: float, vlpo: float,
                        thermal: float) -> float:
        """Galanin-mediated NREM promotion (Kroeger 2018)."""
        if drive < 0.15:
            return 0.0
        # Heat loss & sleep onset are coupled (Kroeger 2018)
        return min(1.0, vlpo * 0.50 + drive * 0.30 + thermal * 0.20)

    def _parental(self, drive: float, social: float) -> float:
        """Gal+ parental output (Wu 2014)."""
        if social < 0.20:
            return 0.0
        return min(1.0, social * 0.65 + drive * 0.30)

    def _sexual(self, drive: float, social: float, gnrh: float) -> float:
        """ERα-mediated sexual behavior (Pfaff 1973)."""
        if social < 0.15:
            return 0.0
        return min(1.0, social * 0.45 + gnrh * 0.30 + drive * 0.20)

    def _gnrh_mod(self, drive: float, social: float) -> float:
        """GnRH/kisspeptin modulation index."""
        return min(1.0, drive * 0.40 + social * 0.40)

    def _classify_state(self, drive: float, heat: float, parental: float,
                         sexual: float, nrem: float) -> str:
        if drive < 0.18:
            return "quiet"
        # Priority: parental > sexual > heat_loss > nrem
        if parental > self.PARENTAL_THRESHOLD:
            return "parental"
        if sexual > self.SEXUAL_THRESHOLD:
            return "sexual"
        if heat > self.HEAT_THRESHOLD:
            return "thermoregulating"
        if nrem > self.NREM_THRESHOLD:
            return "nrem_promoting"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dmh_data = prior.get("DorsomedialHypothalamus", {})
        dmh = float(dmh_data.get("dmh_drive",
                          dmh_data.get("autonomic_drive", 0.0)))

        vlpo_data = prior.get("VentrolateralPreoptic", {})
        vlpo = float(vlpo_data.get("vlpo_drive",
                            vlpo_data.get("sleep_drive", 0.0)))

        social_data = prior.get("MedialAmygdalaPosterior", {})
        if not social_data:
            social_data = prior.get("MedialAmygdalaPosteriorVentral", {})
        social = float(social_data.get("social_signal",
                            social_data.get("med_amyg_drive", 0.0)))

        pvn_data = prior.get("ParaventricularNucleusHypothalamus", {})
        pvn = float(pvn_data.get("pvn_drive", 0.0))

        # Thermal context (warm-sensitive neuron input proxy)
        thermal_data = prior.get("ThermalInput", {})
        thermal = float(thermal_data.get("warm_signal",
                              prior.get("thermal_signal", {}).get(
                                  "warmth", 0.0)))

        target = self._drive_target(dmh, vlpo, social, pvn, thermal)
        prev_drive = float(self.state.get("mpoa_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        gnrh = self._gnrh_mod(new_drive, social)
        heat = self._heat_loss(new_drive, thermal)
        nrem = self._nrem_promoter(new_drive, vlpo, thermal)
        parental = self._parental(new_drive, social)
        sexual = self._sexual(new_drive, social, gnrh)

        state = self._classify_state(new_drive, heat, parental, sexual, nrem)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        pcount = int(self.state.get("parental_count", 0))
        if state == "parental":
            pcount += 1

        self.state["mpoa_drive"] = round(new_drive, 4)
        self.state["heat_loss_signal"] = round(heat, 4)
        self.state["nrem_promoter_signal"] = round(nrem, 4)
        self.state["parental_signal"] = round(parental, 4)
        self.state["sexual_behavior_signal"] = round(sexual, 4)
        self.state["gnrh_modulation"] = round(gnrh, 4)
        self.state["mpoa_state"] = state
        self.state["recent_states"] = recent
        self.state["parental_count"] = pcount
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mpoa_drive": round(new_drive, 4),
            "heat_loss_signal": round(heat, 4),
            "nrem_promoter_signal": round(nrem, 4),
            "parental_signal": round(parental, 4),
            "sexual_behavior_signal": round(sexual, 4),
            "gnrh_modulation": round(gnrh, 4),
            "mpoa_state": state,
        }

    def _parental_engagement(self) -> float:
        """Cumulative parental engagement (Wu 2014)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("parental_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("mpoa_drive", 0.0),
            "heat": self.state.get("heat_loss_signal", 0.0),
            "parental": self.state.get("parental_signal", 0.0),
            "state": self.state.get("mpoa_state", "quiet"),
        }
