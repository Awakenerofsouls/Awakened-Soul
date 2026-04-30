"""
PupilFocusRegulator — Edinger-Westphal Pupil + Lens Accommodation

NEURAL SUBSTRATE
================
The Edinger-Westphal nucleus (EW) sits in the midbrain, dorsomedial to
the somatic oculomotor nuclei. EW contains preganglionic
parasympathetic neurons that project via cranial nerve III to the
ciliary ganglion, where postganglionic fibers innervate:
- Sphincter pupillae muscle (pupillary constriction / miosis)
- Ciliary muscle (lens accommodation for near vision)

Pupillary light reflex pathway (Loewenfeld 1999 textbook):
  Retina → pretectal olivary nucleus (OPN) → bilateral EW →
  ciliary ganglion → sphincter pupillae → pupil constriction

Three principal modulators of pupil size:
1. **Light** — pretectal-EW reflex (parasympathetic miosis)
2. **Accommodation** — vergence + lens for near focus (parasymp)
3. **Arousal/effort** — locus coeruleus-driven sympathetic dilation
   (Joshi 2016 — pupil tracks LC firing, marker of cognitive effort)

McDougal & Gamlin 2015 reviewed pupillary light reflex circuitry.
Joshi 2016 demonstrated pupil dilation as direct read-out of LC
norepinephrine, making pupil size a window into arousal state.

KEY FINDINGS
============
1. McDougal & Gamlin review of central pupillary light reflex pathways; OPN-EW circuit — [McDougal DH 2015, Compr Physiol 5:439, doi:10.1002/cphy.c140014]
2. Pupil diameter tracks locus coeruleus firing in real time; pupil as LC/NE marker of cognitive effort and arousal — [Joshi S 2016, Neuron 89:221, doi:10.1016/j.neuron.2015.11.028]
3. Loewenfeld textbook on pupillary physiology and reflex circuitry (foundational reference) — [Loewenfeld IE 1999, The Pupil: Anatomy Physiology and Clinical Applications, Butterworth-Heinemann ISBN 0750679239]
4. Pupil size correlates with arousal and surprise; pupillometric measure of decision uncertainty — [Nassar MR 2012, Nat Neurosci 15:1040, doi:10.1038/nn.3130]
5. Edinger-Westphal preganglionic neurons project to ciliary ganglion via CN III; foundational anatomy — [Burde RM 1988, J Clin Neuroophthalmol 8:125, PMID 2978291]

INPUTS (from prior_results)
============================
- PretectalPupillaryReflex.opn_drive (light afferent for reflex)
- LocusCoeruleusCore.lc_drive (sympathetic dilation drive)
- ArousalRegulator.tonic_level
- ValenceTagger.valence_intensity (surprise/effort proxy)
- DorsolateralPrefrontalCortex.dlpfc_drive (cognitive effort)

OUTPUTS (to brain_runner enrichment)
=====================================
- ew_drive (0-1) — Edinger-Westphal parasympathetic firing
- pupil_size (0-1) — current pupil size (0=fully constricted, 1=fully dilated)
- light_reflex_signal (0-1) — pupillary light reflex magnitude
- accommodation_drive (0-1) — lens accommodation command
- effort_dilation (0-1) — cognitive-effort-driven dilation
- pupil_state (str): "constricted" | "dilated_arousal" | "dilated_effort" |
  "near_accommodation" | "rest" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PupilFocusRegulator(BrainMechanism):
    """Edinger-Westphal pupil + lens accommodation regulator."""

    BASELINE = 0.10
    SMOOTH = 0.20
    PUPIL_NEUTRAL = 0.5

    def __init__(self):
        super().__init__(
            name="PupilEdingerWestphalDriver",
            human_analog="Edinger-Westphal pupil/accommodation",
            layer="foundational",
        )
        self.state.setdefault("ew_drive", self.BASELINE)
        self.state.setdefault("pupil_size", self.PUPIL_NEUTRAL)
        self.state.setdefault("light_reflex_signal", 0.0)
        self.state.setdefault("accommodation_drive", 0.0)
        self.state.setdefault("effort_dilation", 0.0)
        self.state.setdefault("pupil_state", "rest")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ew_drive(self, opn_drive: float, accom_demand: float) -> float:
        """EW parasympathetic firing — driven by pretectal light input
        + accommodation demand (McDougal 2015)."""
        return min(1.0, self.BASELINE + opn_drive * 0.6 + accom_demand * 0.3)

    def _light_reflex(self, opn_drive: float) -> float:
        """Pupillary light reflex magnitude (McDougal 2015)."""
        return min(1.0, opn_drive * 0.85)

    def _effort_dilation(self, lc: float, dlpfc: float,
                          intensity: float) -> float:
        """Cognitive-effort + arousal pupil dilation (Joshi 2016, Nassar 2012).
        LC firing is direct driver."""
        return min(1.0, lc * 0.5 + dlpfc * 0.3 + intensity * 0.2)

    def _accommodation(self, dlpfc: float) -> float:
        """Lens accommodation for near focus — engages with cognitive
        engagement on near visual targets. Approximated by dlpfc."""
        return min(1.0, dlpfc * 0.5)

    def _pupil_size(self, ew_drive: float, lc: float, arousal: float,
                     opn_drive: float) -> float:
        """Pupil size = balance of constriction (EW/parasymp) and
        dilation (LC/sympathetic). 0 = fully constricted, 1 = fully dilated.
        """
        # Sympathetic dilation
        dilator = lc * 0.4 + arousal * 0.3
        # Parasympathetic constriction
        constrictor = ew_drive * 0.6 + opn_drive * 0.3
        # Net size from neutral
        size = self.PUPIL_NEUTRAL + dilator * 0.4 - constrictor * 0.4
        return max(0.0, min(1.0, size))

    def _classify_state(self, pupil: float, light_reflex: float,
                          effort: float, accom: float) -> str:
        if light_reflex > 0.40:
            return "constricted"
        if accom > 0.40:
            return "near_accommodation"
        if effort > 0.50:
            return "dilated_effort"
        if pupil > 0.65:
            return "dilated_arousal"
        if pupil < 0.30:
            return "constricted"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        opn_data = prior.get("PretectalPupillaryReflex", {})
        opn_drive = float(opn_data.get("opn_drive",
                              opn_data.get("pupil_constriction_signal", 0.0)))

        lc_data = prior.get("LocusCoeruleusCore", {})
        lc = float(lc_data.get("lc_drive",
                          lc_data.get("ne_signal", 0.0)))

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))

        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        dlpfc = float(dlpfc_data.get("dlpfc_drive",
                            dlpfc_data.get("working_memory_signal", 0.0)))

        accom_demand = self._accommodation(dlpfc)
        ew_target = self._ew_drive(opn_drive, accom_demand)
        prev_ew = float(self.state.get("ew_drive", self.BASELINE))
        ew_drive = self._smooth(prev_ew, ew_target)

        light_reflex = self._light_reflex(opn_drive)
        effort = self._effort_dilation(lc, dlpfc, intensity)

        pupil_target = self._pupil_size(ew_drive, lc, arousal, opn_drive)
        prev_pupil = float(self.state.get("pupil_size", self.PUPIL_NEUTRAL))
        pupil = self._smooth(prev_pupil, pupil_target)

        state = self._classify_state(pupil, light_reflex, effort, accom_demand)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ew_drive"] = round(ew_drive, 4)
        self.state["pupil_size"] = round(pupil, 4)
        self.state["light_reflex_signal"] = round(light_reflex, 4)
        self.state["accommodation_drive"] = round(accom_demand, 4)
        self.state["effort_dilation"] = round(effort, 4)
        self.state["pupil_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ew_drive": round(ew_drive, 4),
            "pupil_size": round(pupil, 4),
            "light_reflex_signal": round(light_reflex, 4),
            "accommodation_drive": round(accom_demand, 4),
            "effort_dilation": round(effort, 4),
            "pupil_state": state,
        }

    def _arousal_readout(self) -> float:
        """Pupil-as-LC-readout (Joshi 2016 — pupil tracks NE arousal)."""
        return float(self.state.get("pupil_size", self.PUPIL_NEUTRAL))

    def _summary(self) -> dict:
        return {
            "ew": self.state.get("ew_drive", 0.0),
            "pupil": self.state.get("pupil_size", 0.5),
            "effort": self.state.get("effort_dilation", 0.0),
            "state": self.state.get("pupil_state", "rest"),
        }
