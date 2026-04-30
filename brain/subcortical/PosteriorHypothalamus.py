"""
PosteriorHypothalamus — PH — Sympathetic Activation, Arousal, Panic-Defense

NEURAL SUBSTRATE
================
The posterior hypothalamus (PH) sits caudal to the dorsomedial nucleus
and rostral to the mammillary bodies. It is the classical "ergotropic"
zone of the hypothalamus: stimulation produces sympathetic activation
(rise in heart rate and blood pressure, pupil dilation, piloerection),
arousal, and panic-like defensive behavior. PH lies in close proximity
to the histaminergic tuberomammillary nucleus (TMN), and PH/TMN circuits
together orchestrate cortical arousal.

Anatomy:
- Glutamatergic projection neurons → DMH, PVN, RVLM (sympathetic outflow).
- Receives afferents from amygdala, prefrontal cortex, and sensory
  thalamus.
- Outputs to midbrain PAG (dorsolateral) for active defense.
- Adjacent perifornical / dorsal PH region implicated in panic
  attack-like states (Bandler 2000; DiMicco 2002).

Stimulation studies in cats and rats produce a coordinated "fight-or-
flight" pattern with cardiovascular, respiratory and behavioral
components. Lesions of PH reduce sympathetic tone and arousal.

KEY FINDINGS
============
1. Central circuits mediating patterned autonomic activity during
   active vs. passive emotional coping (PH-PAG axis).
   [Bandler R 2000, Brain Res Bull 53:95, doi:10.1016/s0361-9230(00)00313-0]
2. Dorsomedial/posterior hypothalamus and the response to stress:
   coordination of sympathetic, neuroendocrine and behavioral activation.
   [DiMicco J 2002, Pharmacol Biochem Behav 71:469, doi:10.1016/s0091-3057(01)00689-x]
3. Neural regulation of endocrine and autonomic stress responses:
   PH integrates with PVN and brainstem.
   [Ulrich-Lai Y 2009, Nat Rev Neurosci 10:397, doi:10.1038/nrn2647]
4. Hypothalamic regulation of sleep/circadian rhythms; PH-TMN
   histaminergic arousal coupling.
   [Saper C 2005, Nature 437:1257, doi:10.1038/nature04284]
5. Paraventricular CRH/HPA axis chronic-stress integration converges
   on PH-DMH cardiovascular outflow.
   [Herman J 2003, Front Neuroendocrinol 24:151, doi:10.1016/j.yfrne.2003.07.001]
6. Aversive Esr1+ aggression circuit reverberates with PH defensive
   arousal — [Lin D 2011, Nature 470:221, doi:10.1038/nature09736]

INPUTS
======
- AnteriorHypothalamus.ah_drive (defensive aggression)
- DorsomedialHypothalamus.dmh_drive (autonomic coupling)
- LateralHabenula.lhb_drive (negative valence)
- LocusCoeruleusCore.lc_drive (NA arousal)
- ParaventricularNucleusHypothalamus.pvn_drive (HPA coupling)

OUTPUTS
=======
- ph_drive (0-1)
- sympathetic_activation (0-1) → RVLM/IML
- arousal_signal (0-1) — cortical arousal
- panic_defense_signal (0-1) — panic-attack proxy
- cardiovascular_signal (0-1) — HR/BP rise
- pag_active_defense_signal (0-1)
- ph_state (str): "panic_defense" | "arousal" | "sympathetic_burst" |
                    "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PosteriorHypothalamus(BrainMechanism):
    """PH — sympathetic activation, arousal, panic defense."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AROUSAL_THRESHOLD = 0.30
    SYMPATHETIC_THRESHOLD = 0.45
    PANIC_THRESHOLD = 0.55

    def __init__(self):
        super().__init__(
            name="PosteriorHypothalamus",
            human_analog="PH (sympathetic activation, panic defense)",
            layer="subcortical",
        )
        self.state.setdefault("ph_drive", self.BASELINE)
        self.state.setdefault("sympathetic_activation", 0.0)
        self.state.setdefault("arousal_signal", 0.0)
        self.state.setdefault("panic_defense_signal", 0.0)
        self.state.setdefault("cardiovascular_signal", 0.0)
        self.state.setdefault("pag_active_defense_signal", 0.0)
        self.state.setdefault("ph_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("panic_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ah: float, dmh: float, lhb: float,
                       lc: float, pvn: float) -> float:
        """Composite PH drive (Bandler 2000 — defense-arousal hub)."""
        target = (self.BASELINE
                  + ah * 0.30
                  + dmh * 0.25
                  + lhb * 0.18
                  + lc * 0.18
                  + pvn * 0.15)
        return min(1.0, target)

    def _sympathetic(self, drive: float, dmh: float, pvn: float) -> float:
        """Sympathetic outflow (DiMicco 2002)."""
        if drive < 0.18:
            return 0.0
        return min(1.0, drive * 0.45 + dmh * 0.30 + pvn * 0.25)

    def _arousal(self, drive: float, lc: float) -> float:
        """Cortical arousal (Saper 2005; PH-TMN)."""
        return min(1.0, drive * 0.55 + lc * 0.40)

    def _panic_defense(self, drive: float, ah: float, lhb: float) -> float:
        """Panic-defense proxy (Bandler 2000; classic stim panic)."""
        if drive < 0.30:
            return 0.0
        return min(1.0, drive * 0.50 + ah * 0.30 + lhb * 0.30)

    def _cardiovascular(self, sympathetic: float, drive: float) -> float:
        """HR/BP rise (DiMicco 2002)."""
        return min(1.0, sympathetic * 0.65 + drive * 0.30)

    def _pag_active(self, drive: float, ah: float, panic: float) -> float:
        """PH→PAG (dorsolateral, active defense) (Bandler 2000)."""
        return min(1.0, drive * 0.35 + ah * 0.30 + panic * 0.40)

    def _classify_state(self, drive: float, sympathetic: float,
                         panic: float, arousal: float) -> str:
        if drive < 0.18:
            return "quiet"
        if panic > self.PANIC_THRESHOLD:
            return "panic_defense"
        if sympathetic > self.SYMPATHETIC_THRESHOLD:
            return "sympathetic_burst"
        if arousal > self.AROUSAL_THRESHOLD:
            return "arousal"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ah_data = prior.get("AnteriorHypothalamus", {})
        ah = float(ah_data.get("ah_drive",
                          ah_data.get("aggression_signal", 0.0)))

        dmh_data = prior.get("DorsomedialHypothalamus", {})
        dmh = float(dmh_data.get("dmh_drive",
                          dmh_data.get("autonomic_drive", 0.0)))

        lhb_data = prior.get("LateralHabenula", {})
        lhb = float(lhb_data.get("lhb_drive", 0.0))

        lc_data = prior.get("LocusCoeruleusCore", {})
        if not lc_data:
            lc_data = prior.get("LocusCoeruleus", {})
        lc = float(lc_data.get("lc_drive",
                          lc_data.get("ne_signal", 0.0)))

        pvn_data = prior.get("ParaventricularNucleusHypothalamus", {})
        pvn = float(pvn_data.get("pvn_drive", 0.0))

        target = self._drive_target(ah, dmh, lhb, lc, pvn)
        prev_drive = float(self.state.get("ph_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        sym = self._sympathetic(new_drive, dmh, pvn)
        ar = self._arousal(new_drive, lc)
        panic = self._panic_defense(new_drive, ah, lhb)
        cv = self._cardiovascular(sym, new_drive)
        pag = self._pag_active(new_drive, ah, panic)

        state = self._classify_state(new_drive, sym, panic, ar)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        pc = int(self.state.get("panic_count", 0))
        if state == "panic_defense":
            pc += 1

        self.state["ph_drive"] = round(new_drive, 4)
        self.state["sympathetic_activation"] = round(sym, 4)
        self.state["arousal_signal"] = round(ar, 4)
        self.state["panic_defense_signal"] = round(panic, 4)
        self.state["cardiovascular_signal"] = round(cv, 4)
        self.state["pag_active_defense_signal"] = round(pag, 4)
        self.state["ph_state"] = state
        self.state["recent_states"] = recent
        self.state["panic_count"] = pc
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ph_drive": round(new_drive, 4),
            "sympathetic_activation": round(sym, 4),
            "arousal_signal": round(ar, 4),
            "panic_defense_signal": round(panic, 4),
            "cardiovascular_signal": round(cv, 4),
            "pag_active_defense_signal": round(pag, 4),
            "ph_state": state,
        }

    def _panic_pressure(self) -> float:
        """Cumulative panic engagement (Bandler 2000)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("panic_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ph_drive", 0.0),
            "sympathetic": self.state.get("sympathetic_activation", 0.0),
            "panic": self.state.get("panic_defense_signal", 0.0),
            "state": self.state.get("ph_state", "quiet"),
        }
