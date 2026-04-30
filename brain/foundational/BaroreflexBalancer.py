"""
BaroreflexBalancer — NTS Baroreceptor Cardiovascular Reflex

NEURAL SUBSTRATE
================
The arterial baroreflex is the primary fast-acting cardiovascular
homeostatic loop. Aortic arch + carotid sinus baroreceptors detect
arterial blood pressure changes and project via cranial nerves IX/X
to the nucleus tractus solitarius (NTS) in the dorsomedial medulla.
NTS then drives:
- Inhibition of rostral ventrolateral medulla (RVLM) sympathetic
  premotor → reduced peripheral vasoconstriction + cardiac drive
- Excitation of nucleus ambiguus (NA) and dorsal motor nucleus of
  vagus (DMV) parasympathetic outflow → cardiac slowing

Net effect: rise in BP → baroreceptor firing up → sympathetic OUT,
parasympathetic ON → BP drops back. Loop closes in seconds.

Andresen & Kunze 1994 reviewed NTS baroreceptor physiology; Guyenet
2006 reviewed the brainstem control of cardiovascular regulation;
Dampney 2016 covered central pathways. Baroreflex sensitivity is a
key clinical marker — reduced sensitivity predicts mortality post-MI.

Functional model: BaroreflexBalancer reads pressure-state proxy from
NTS, computes a sympathetic-vs-parasympathetic balance signal, and
emits commands to RVLM (suppress) and DMV (engage) for cardiovascular
homeostasis.

KEY FINDINGS
============
1. NTS is the primary central terminus of arterial baroreceptor input; integrates pressure information for autonomic outflow — [Andresen MC 1994, Annu Rev Physiol 56:93, doi:10.1146/annurev.ph.56.030194.000521]
2. RVLM bulbospinal sympathoexcitatory neurons are tonically driven; baroreflex inhibits via NTS-CVLM-RVLM pathway — [Guyenet PG 2006, Nat Rev Neurosci 7:335, doi:10.1038/nrn1902]
3. Central pathways underlying baroreflex: NTS, CVLM, RVLM, NA, DMV connectivity — [Dampney RA 2016, Compr Physiol 6:1099, doi:10.1002/cphy.c150022]
4. Baroreflex sensitivity is a clinical predictor of post-myocardial-infarction mortality — [La Rovere MT 1998, Lancet 351:478, doi:10.1016/S0140-6736(97)11144-8]
5. Vagal tone via NTS-DMV-NA enhances heart rate variability; baroreflex contributes to HRV — [Thayer JF 2009, Neurosci Biobehav Rev 33:81, doi:10.1016/j.neubiorev.2008.08.004]

INPUTS (from prior_results)
============================
- NucleusTractusSolitariusFull.nts_drive (or A2NoradrenergicNTS.ne_signal)
- VitalCoreRegulator.vital_drive (cardiovascular state proxy)
- ArousalRegulator.tonic_level (sympathetic tone modulator)
- C1AdrenergicRVLM.c1_drive (RVLM sympathoexcitatory output)

OUTPUTS (to brain_runner enrichment)
=====================================
- baroreflex_drive (0-1) — overall reflex engagement
- sympathetic_output_inhibition (0-1) — RVLM suppression command
- parasympathetic_output (0-1) — DMV/NA vagal command
- pressure_estimate (0-1) — current detected BP (proxy)
- hrv_signal (0-1) — heart-rate-variability proxy (vagal tone health)
- baroreflex_state (str): "engaged" | "rest_tone" | "hypertensive" |
  "hypotensive" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class BaroreflexBalancer(BrainMechanism):
    """NTS-mediated baroreflex cardiovascular balance regulator."""

    BASELINE = 0.10
    SMOOTH = 0.20
    ENGAGEMENT_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="BaroreflexCardiovascularDriver",
            human_analog="NTS baroreceptor reflex regulator",
            layer="foundational",
        )
        self.state.setdefault("baroreflex_drive", self.BASELINE)
        self.state.setdefault("sympathetic_output_inhibition", 0.0)
        self.state.setdefault("parasympathetic_output", 0.0)
        self.state.setdefault("pressure_estimate", 0.5)
        self.state.setdefault("hrv_signal", 0.0)
        self.state.setdefault("baroreflex_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _pressure_estimate(self, nts: float, c1_drive: float,
                             arousal: float) -> float:
        """Estimated BP from NTS afferent drive + sympathetic activity
        + arousal modulator. NTS firing scales with pressure."""
        base = 0.5 + (nts - 0.30) * 0.6 + (c1_drive - 0.20) * 0.4
        base += (arousal - 0.30) * 0.10  # arousal raises BP slightly
        return max(0.0, min(1.0, base))

    def _drive_target(self, nts: float, pressure: float) -> float:
        """Baroreflex drive — engages above resting BP, scales with
        deviation from setpoint (Andresen 1994)."""
        deviation = abs(pressure - 0.5)
        return min(1.0, self.BASELINE + nts * 0.5 + deviation * 0.5)

    def _sympathetic_inhibition(self, drive: float, pressure: float) -> float:
        """RVLM sympathoexcitatory inhibition (Guyenet 2006). Engaged
        when BP is high — reflex inhibits sympathetic output."""
        if pressure < 0.50:
            return 0.0  # low BP — don't inhibit sympathetic
        return min(1.0, drive * 0.6 + (pressure - 0.50) * 1.0)

    def _parasympathetic_output(self, drive: float, pressure: float) -> float:
        """DMV/NA vagal cardiac output — engages with high BP, drops
        with low BP (Dampney 2016)."""
        if pressure < 0.40:
            return 0.0
        return min(1.0, drive * 0.5 + (pressure - 0.40) * 0.8)

    def _hrv_signal(self, parasymp: float, arousal: float) -> float:
        """HRV proxy — high vagal tone + low arousal = high HRV
        (Thayer 2009)."""
        return min(1.0, parasymp * 0.7 + (1.0 - arousal) * 0.3)

    def _classify_state(self, drive: float, pressure: float,
                          parasymp: float) -> str:
        if drive < 0.15:
            return "quiet"
        if pressure > 0.70:
            return "hypertensive"
        if pressure < 0.30:
            return "hypotensive"
        if drive > self.ENGAGEMENT_THRESHOLD:
            return "engaged"
        return "rest_tone"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        nts_data = prior.get("NucleusTractusSolitariusFull", {})
        if not nts_data:
            nts_data = prior.get("A2NoradrenergicNTS", {})
        nts = float(nts_data.get("nts_drive",
                          nts_data.get("ne_signal", 0.0)))

        c1_data = prior.get("C1AdrenergicRVLM", {})
        c1_drive = float(c1_data.get("c1_drive",
                              c1_data.get("rvlm_drive", 0.0)))

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        # If no upstream pressure signal at all, the brainstem reads tonic
        # MAP as the resting set-point — empty pirp_context isn't the same
        # as a hypotensive crash.
        no_input = (nts == 0.0 and c1_drive == 0.0
                    and not prior.get("NucleusTractusSolitariusFull")
                    and not prior.get("A2NoradrenergicNTS")
                    and not prior.get("C1AdrenergicRVLM"))

        pressure_target = self._pressure_estimate(nts, c1_drive, arousal)
        prev_pressure = float(self.state.get("pressure_estimate", 0.5))
        pressure = self._smooth(prev_pressure, pressure_target)
        if no_input:
            pressure = 0.5  # tonic resting MAP

        target = self._drive_target(nts, pressure)
        prev_drive = float(self.state.get("baroreflex_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        symp_inhib = self._sympathetic_inhibition(new_drive, pressure)
        parasymp = self._parasympathetic_output(new_drive, pressure)
        hrv = self._hrv_signal(parasymp, arousal)

        state = self._classify_state(new_drive, pressure, parasymp)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["baroreflex_drive"] = round(new_drive, 4)
        self.state["sympathetic_output_inhibition"] = round(symp_inhib, 4)
        self.state["parasympathetic_output"] = round(parasymp, 4)
        self.state["pressure_estimate"] = round(pressure, 4)
        self.state["hrv_signal"] = round(hrv, 4)
        self.state["baroreflex_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "baroreflex_drive": round(new_drive, 4),
            "sympathetic_output_inhibition": round(symp_inhib, 4),
            "parasympathetic_output": round(parasymp, 4),
            "pressure_estimate": round(pressure, 4),
            "hrv_signal": round(hrv, 4),
            "baroreflex_state": state,
        }

    def _baroreflex_sensitivity(self) -> float:
        """Clinical predictor — high HRV + vagal tone = good sensitivity
        (La Rovere 1998)."""
        return float(self.state.get("hrv_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("baroreflex_drive", 0.0),
            "pressure": self.state.get("pressure_estimate", 0.5),
            "parasymp": self.state.get("parasympathetic_output", 0.0),
            "hrv": self.state.get("hrv_signal", 0.0),
            "state": self.state.get("baroreflex_state", "quiet"),
        }
