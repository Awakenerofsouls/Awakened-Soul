"""
AnteriorHypothalamus — AH — Defensive Aggression / Hypothalamic Attack Area

NEURAL SUBSTRATE
================
The anterior hypothalamus (AH), particularly its more medial portion
abutting the ventromedial nucleus (VMHvl) and the ventrolateral
extension toward the lateral preoptic area, is part of the classical
"hypothalamic attack area" (HAA) — a region whose electrical or
optogenetic stimulation reliably elicits species-typical attack and
defensive aggression behaviors. Kruk and colleagues mapped the HAA in
rodents in seminal lesion/stimulation studies; modern optogenetic and
chemogenetic work by Lin, Anderson and colleagues identified estrogen
receptor-α (Esr1) expressing neurons in VMHvl/AH as the molecular
identity of the aggression locus.

Key anatomical features:
- Esr1+ glutamatergic neurons in AH/VMHvl trigger attack with intensity
  scaling with stimulation amplitude (Lee et al. 2014).
- AH receives inputs from medial amygdala (pheromone), BNST, and
  posterior cortical amygdala — limbic threat assessment converges here.
- AH outputs to PAG (dorsolateral) for behavioral execution and to the
  midbrain reticular formation for autonomic activation.

Functionally distinct from VMHdm (predator fear) — AH/VMHvl drives
conspecific aggression toward intruders.

KEY FINDINGS
============
1. Optogenetic stimulation of VMHvl/AH neurons elicits attack toward
   males, females and inanimate objects; pharmacogenetic silencing
   reversibly inhibits inter-male aggression —
   [Lin D 2011, Nature 470:221, doi:10.1038/nature09736]
2. Esr1+ neurons in VMHvl scale aggression: weak activation → sniffing,
   stronger → mounting, strongest → attack —
   [Lee H 2014, Nature 509:627, doi:10.1038/nature13169]
3. Ethology and pharmacology of hypothalamic aggression in rat:
   serotonergic and GABAergic modulation of HAA-evoked attack.
   [Kruk M 1991, Neurosci Biobehav Rev 15:527, doi:10.1016/s0149-7634(05)80144-7]
4. Decoding VMHvl neural activity during male mouse aggression: tuning
   to male conspecifics and predictive of attack latency.
   [Falkner A 2014, J Neurosci 34:5971, doi:10.1523/JNEUROSCI.5109-13.2014]
5. Hypothalamic regulation of sleep/circadian/autonomic outflow places
   AH within the integrated defense circuit.
   [Saper C 2005, Nature 437:1257, doi:10.1038/nature04284]
6. Posterior amygdala Vglut1+ neurons gate VMHvl/AH territorial
   aggression via limbic top-down control.
   [Zha X 2020, Cell Rep 31:107517, doi:10.1016/j.celrep.2020.03.081]

INPUTS
======
- MedialAmygdalaPosterior.med_amyg_drive (pheromone/conspecific cue)
- PosteriorCorticalAmygdala.cortamy_drive (olfactory threat)
- BNSTAnterolateral.bnst_drive (sustained-threat gate)
- VentromedialHypothalamus.vmh_drive (cross-coupling with VMHvl)
- LateralHabenula.lhb_drive (negative-valence weighting)

OUTPUTS
=======
- ah_drive (0-1) — hypothalamic attack area drive
- aggression_signal (0-1) — attack-execution drive
- esr1_population_signal (0-1) — Esr1+ aggression-tuned proxy
- pag_dorsolateral_signal (0-1) — to PAG defensive-rage column
- territorial_attack_signal (0-1)
- ah_state (str): "attack" | "threat_display" | "investigation" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AnteriorHypothalamus(BrainMechanism):
    """AH — hypothalamic attack area / defensive aggression."""

    BASELINE = 0.08
    SMOOTH = 0.20
    INVESTIGATE_THRESHOLD = 0.20
    THREAT_THRESHOLD = 0.40
    ATTACK_THRESHOLD = 0.55

    def __init__(self):
        super().__init__(
            name="AnteriorHypothalamus",
            human_analog="AH (hypothalamic attack area, Esr1+ aggression)",
            layer="subcortical",
        )
        self.state.setdefault("ah_drive", self.BASELINE)
        self.state.setdefault("aggression_signal", 0.0)
        self.state.setdefault("esr1_population_signal", 0.0)
        self.state.setdefault("pag_dorsolateral_signal", 0.0)
        self.state.setdefault("territorial_attack_signal", 0.0)
        self.state.setdefault("ah_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("attack_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, mea: float, cortamy: float, bnst: float,
                       vmh: float, lhb: float) -> float:
        """Composite AH drive (Lin 2011, Lee 2014 — Esr1 integrative)."""
        target = (self.BASELINE
                  + mea * 0.35
                  + cortamy * 0.20
                  + bnst * 0.20
                  + vmh * 0.25
                  + lhb * 0.10)
        return min(1.0, target)

    def _aggression(self, drive: float, mea: float, vmh: float) -> float:
        """Scalar aggression signal (Lee 2014 — graded by stimulation)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.45 + mea * 0.30 + vmh * 0.30)

    def _esr1_pop(self, drive: float, agg: float) -> float:
        """Esr1+ neuron population proxy (Lee 2014)."""
        return min(1.0, drive * 0.50 + agg * 0.45)

    def _pag_dl(self, drive: float, agg: float) -> float:
        """AH → dorsolateral PAG defensive-rage column (Bandler 2000)."""
        return min(1.0, drive * 0.40 + agg * 0.50)

    def _territorial(self, drive: float, mea: float, bnst: float) -> float:
        """Territorial attack readiness (Zha 2020)."""
        if drive < 0.25:
            return 0.0
        return min(1.0, mea * 0.40 + bnst * 0.25 + drive * 0.30)

    def _classify_state(self, drive: float, agg: float,
                         territorial: float) -> str:
        if drive < 0.15:
            return "quiet"
        if agg > self.ATTACK_THRESHOLD or territorial > self.ATTACK_THRESHOLD:
            return "attack"
        if drive > self.THREAT_THRESHOLD:
            return "threat_display"
        if drive > self.INVESTIGATE_THRESHOLD:
            return "investigation"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mea_data = prior.get("MedialAmygdalaPosterior", {})
        if not mea_data:
            mea_data = prior.get("AmygdaloidMedialAnterior", {})
        mea = float(mea_data.get("med_amyg_drive",
                          mea_data.get("social_signal", 0.0)))

        cortamy_data = prior.get("PosteriorCorticalAmygdala", {})
        if not cortamy_data:
            cortamy_data = prior.get("AmygdaloidCorticalAnterior", {})
        cortamy = float(cortamy_data.get("cortamy_drive",
                              cortamy_data.get("olfactory_signal", 0.0)))

        bnst_data = prior.get("BNSTAnterolateral", {})
        if not bnst_data:
            bnst_data = prior.get("BNSTOval", {})
        bnst = float(bnst_data.get("bnst_drive", 0.0))

        vmh_data = prior.get("VentromedialHypothalamus", {})
        vmh = float(vmh_data.get("vmh_drive",
                          vmh_data.get("vmhvl_drive", 0.0)))

        lhb_data = prior.get("LateralHabenula", {})
        lhb = float(lhb_data.get("lhb_drive", 0.0))

        target = self._drive_target(mea, cortamy, bnst, vmh, lhb)
        prev_drive = float(self.state.get("ah_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        agg = self._aggression(new_drive, mea, vmh)
        esr1 = self._esr1_pop(new_drive, agg)
        pag = self._pag_dl(new_drive, agg)
        territorial = self._territorial(new_drive, mea, bnst)

        state = self._classify_state(new_drive, agg, territorial)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        ac = int(self.state.get("attack_count", 0))
        if state == "attack":
            ac += 1

        self.state["ah_drive"] = round(new_drive, 4)
        self.state["aggression_signal"] = round(agg, 4)
        self.state["esr1_population_signal"] = round(esr1, 4)
        self.state["pag_dorsolateral_signal"] = round(pag, 4)
        self.state["territorial_attack_signal"] = round(territorial, 4)
        self.state["ah_state"] = state
        self.state["recent_states"] = recent
        self.state["attack_count"] = ac
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('ah_drive', 0.0)))
        if len(rd) > 60:
            rd = rd[-60:]
        self.state["recent_drives"] = rd

        # extension: track state history if state field exists
        rs = list(self.state.get("recent_states", []))
        cur_state = self.state.get('ah_state', "quiet") if 'ah_state' else "quiet"
        rs.append(cur_state)
        if len(rs) > 60:
            rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "ah_drive": round(new_drive, 4),
            "aggression_signal": round(agg, 4),
            "esr1_population_signal": round(esr1, 4),
            "pag_dorsolateral_signal": round(pag, 4),
            "territorial_attack_signal": round(territorial, 4),
            "ah_state": state,
        }

    def _attack_pressure(self) -> float:
        """Cumulative attack engagement (Lin 2011)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("attack_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ah_drive", 0.0),
            "aggression": self.state.get("aggression_signal", 0.0),
            "state": self.state.get("ah_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        """Fraction of recent ticks where the system was non-quiet."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet", "rest", "neutral", ""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        """Fraction of consecutive ticks holding the same state."""
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i - 1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        """Most-frequent recent state."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return self.state.get('ah_state', "quiet") if 'ah_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        """Running mean of primary drive over recent window."""
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('ah_drive', 0.0)) if 'ah_drive' else 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        """Std-dev proxy of primary drive — tonic-vs-phasic balance."""
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4:
            return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        """Sustained ceiling — runaway feedback flag."""
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        """Sustained collapse — afferent failure flag."""
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "drive": self.state.get('ah_drive', 0.0) if 'ah_drive' else 0.0,
            "state": self.state.get('ah_state', "quiet") if 'ah_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

