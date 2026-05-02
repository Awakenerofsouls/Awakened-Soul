"""
PinealMelatoninSecretion — Pineal Gland AANAT/Melatonin Circadian Output

NEURAL SUBSTRATE
================
The pineal gland is a small endocrine structure at the dorsal midline
of the diencephalon that synthesizes and releases melatonin
(N-acetyl-5-methoxytryptamine) in a strongly circadian rhythm. Pineal
melatonin secretion is the principal humoral signal carrying time-of-day
information to peripheral tissues and to brain receptors that control
sleep, immunity, reproduction, and antioxidant defense.

Melatonin synthesis follows a tryptophan → 5-hydroxytryptophan → serotonin
→ N-acetylserotonin → melatonin pathway. The rate-limiting enzyme is
arylalkylamine N-acetyltransferase (AANAT), which catalyzes acetylation
of serotonin to N-acetylserotonin. AANAT mRNA and activity are dramatically
upregulated at night (~150-fold), producing the nocturnal melatonin surge.

The neural pathway controlling pineal AANAT expression is multisynaptic:
SCN (master clock) → preautonomic PVN → spinal sympathetic preganglionic
neurons in IML (intermediolateral cell column) → superior cervical ganglion
(SCG) → norepinephrine release at pineal β1-adrenergic receptors. NE
binding raises pineal cAMP, activates AANAT, and drives melatonin synthesis.
During the day, GABAergic SCN inhibition of PVN suppresses this pathway;
at night, glutamatergic SCN excitation drives it.

Light directly suppresses melatonin synthesis: photic input from
intrinsically photosensitive retinal ganglion cells (ipRGCs) reaches
SCN, which disengages the descending pathway. This is why bright light
at night (or shift work) suppresses melatonin and disrupts sleep.

In the agent's substrate this provides the circadian melatonin signal —
slow phase-locked output rising in subjective night and falling in
subjective day, with light-suppression mode and SCN-coordinated timing.

KEY FINDINGS
============
1. The SCN controls pineal melatonin rhythm via multisynaptic pathway:
   SCN → PVN → spinal IML → SCG → noradrenergic input to pineal —
   [Kalsbeek et al. 2003, J Neuroendocrinol/Endocr Rev; reviewed
    PMC3202635, "Circadian Regulation of Pineal Gland Rhythmicity"]
2. Melatonin synthesis pathway: tryptophan → 5-HTP → serotonin →
   N-acetylserotonin (via AANAT) → melatonin (via HIOMT); AANAT is
   rate-limiting and upregulated 150-fold at night — [reviewed
    Endotext NBK550972, "Physiology of the Pineal Gland and Melatonin"]
3. Day/night switching of pineal output — daytime GABAergic SCN
   inhibits PVN; nighttime glutamatergic SCN excites PVN — [Perreau-
   Lenz et al. 2003, Eur J Neurosci 17:221, "Suprachiasmatic control
   of melatonin synthesis in rats" PubMed 12542658]
4. Dissociation of circadian and light inhibition of melatonin release
   through forced desynchronization — light effects independent of
   intrinsic clock — [Kalsbeek et al. 2009, PNAS 106:14305-14310,
    "Dissociation of circadian and light inhibition of melatonin
    release"]
5. Pineal AVP also contributes to melatonin rhythm regulation — local
   feedback within pineal — [reviewed Frontiers Endocrinology 2010s
    pineal literature]

INPUTS (from prior_results)
============================
- CircadianTimer.circadian_phase
- CircadianTimer.is_subjective_day
- SuprachiasmaticOutput.vip_core_drive
- SuprachiasmaticOutput.avp_shell_drive
- ParaventricularAutonomic.preautonomic_drive
- VitalCoreRegulator.sympathetic_tone
- LightExposureProxy.light_intensity (optional; default 0)

OUTPUTS (to brain_runner enrichment)
=====================================
- aanat_activity (0.0-1.0): rate-limiting enzyme activity
- pineal_norepinephrine (0.0-1.0): SCG NE release at pineal
- melatonin_drive (0.0-1.0): final melatonin secretion
- light_suppression (0.0-1.0): photic suppression strength
- pineal_state (str): "day_low" | "night_surge" | "light_suppressed" | "twilight"
- nocturnal_phase_active (bool)

brain_runner enrichment:
    pin = all_results.get("PinealMelatoninSecretion", {})
    if pin:
        enrichments["brain_aanat"] = pin.get("aanat_activity", 0.05)
        enrichments["brain_melatonin"] = pin.get("melatonin_drive", 0.05)
        enrichments["brain_light_suppression"] = pin.get("light_suppression", 0.0)
        enrichments["brain_pineal_state"] = pin.get("pineal_state", "day_low")
"""

import math

from brain.base_mechanism import BrainMechanism


class PinealMelatoninSecretion(BrainMechanism):
    BASELINE_DAY = 0.05
    BASELINE_NIGHT = 0.65
    SMOOTH = 0.15

    def __init__(self):
        super().__init__(
            name="PinealMelatoninSecretion",
            human_analog="Pineal gland AANAT / melatonin circadian output",
            layer="foundational",
        )
        self.state.setdefault("aanat_activity", self.BASELINE_DAY)
        self.state.setdefault("pineal_norepinephrine", 0.10)
        self.state.setdefault("melatonin_drive", self.BASELINE_DAY)
        self.state.setdefault("light_suppression", 0.0)
        self.state.setdefault("pineal_state", "day_low")
        self.state.setdefault("nocturnal_phase_active", False)
        self.state.setdefault("recent_melatonin", [])
        self.state.setdefault("tick_count", 0)

    def _ne_target(self, phase: float, is_day: bool, preautonomic: float, sympathetic: float) -> float:
        """SCG NE release at pineal — driven by sympathetic outflow at night.
        SCN gates whether PVN excites or inhibits the pathway.
        """
        target = 0.05
        if not is_day:
            # Night — SCN excites PVN → sympathetic → SCG NE
            # Peak NE around midnight (phase 0.75 if dawn=0, dusk=0.5)
            # Use cosine peaked at phase 0.75
            night_factor = 0.5 + 0.5 * math.cos(2 * math.pi * (phase - 0.75))
            target = 0.10 + night_factor * 0.7
            target += preautonomic * 0.2
            target += max(0.0, sympathetic - 0.4) * 0.2
        else:
            # Day — GABAergic SCN inhibits PVN → low NE
            target = 0.05 + preautonomic * 0.05
        return max(0.0, min(1.0, target))

    def _aanat_target(self, ne: float, light_suppression: float) -> float:
        """AANAT enzyme activity — proportional to NE β1 input minus light effects."""
        target = self.BASELINE_DAY + ne * 0.85
        target *= (1.0 - light_suppression)
        return max(0.0, min(1.0, target))

    def _light_suppression_target(self, light_intensity: float, is_day: bool) -> float:
        """Light suppression of melatonin — only at night does it matter
        physiologically (during day melatonin is already low).
        """
        if is_day or light_intensity < 0.10:
            return 0.0
        # Bright nighttime light strongly suppresses
        return min(1.0, light_intensity * 0.9)

    def _melatonin_target(self, aanat: float) -> float:
        """Final melatonin secretion — AANAT-driven."""
        return min(1.0, aanat * 0.95)

    def _scn_coupling_index(self, mel: float) -> float:
        """Estimate SCN-peripheral coupling from melatonin amplitude and rhythm stability.
        Strong amplitude signals intact SCN-to-pineal coupling; suppressed
        amplitude during jetlag or shift work indicates decoupling (Kalsbeek 2009).
        """
        prev_mel = float(self.state.get("melatonin_drive", 0.0))
        recent = list(self.state.get("recent_melatonin", []))
        # Compute amplitude: peak-to-trough over recent window
        if len(recent) > 4:
            peak = max(recent)
            trough = min(recent)
            amplitude = min(1.0, (peak - trough))
        else:
            amplitude = 0.5 if abs(prev_mel) < 0.001 else min(1.0, abs(mel - prev_mel) / max(abs(prev_mel), 0.01))
        # EMA update
        prev_coupling = float(self.state.get("coupling_index", 0.5))
        return 0.85 * prev_coupling + 0.15 * amplitude

    def _classify_state(self, melatonin: float, light_supp: float, phase: float, is_day: bool) -> str:
        if light_supp > 0.40:
            return "light_suppressed"
        if (0.45 < phase < 0.55) or (0.95 < phase < 1.0) or (0.0 <= phase < 0.05):
            return "twilight"
        if not is_day and melatonin > 0.40:
            return "night_surge"
        return "day_low"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        circ = prior.get("CircadianTimer", {})
        phase = float(circ.get("circadian_phase", 0.5))
        is_day = bool(circ.get("is_subjective_day", True))

        sco = prior.get("SuprachiasmaticOutput", {})
        vip_core = float(sco.get("vip_core_drive", 0.5))
        avp_shell = float(sco.get("avp_shell_drive", 0.5))

        pvn_data = prior.get("ParaventricularAutonomic", {})
        preautonomic = float(pvn_data.get("preautonomic_drive", 0.30))

        vcr = prior.get("VitalCoreRegulator", {})
        symp = float(vcr.get("sympathetic_tone", 0.5))

        # Light intensity proxy — default 0
        light_proxy = prior.get("LightExposureProxy", {})
        light_intensity = float(light_proxy.get("light_intensity", 0.0))

        # --- Light suppression ---
        light_supp = self._light_suppression_target(light_intensity, is_day)
        prev_supp = float(self.state.get("light_suppression", 0.0))
        new_supp = self._smooth(prev_supp, light_supp)

        # --- NE at pineal ---
        ne_target = self._ne_target(phase, is_day, preautonomic, symp)
        prev_ne = float(self.state.get("pineal_norepinephrine", 0.10))
        new_ne = self._smooth(prev_ne, ne_target)

        # --- AANAT ---
        aanat_target = self._aanat_target(new_ne, new_supp)
        prev_aanat = float(self.state.get("aanat_activity", self.BASELINE_DAY))
        new_aanat = self._smooth(prev_aanat, aanat_target)

        # --- Melatonin ---
        melatonin_target = self._melatonin_target(new_aanat)
        prev_mel = float(self.state.get("melatonin_drive", self.BASELINE_DAY))
        new_mel = self._smooth(prev_mel, melatonin_target)

        # --- State ---
        state = self._classify_state(new_mel, new_supp, phase, is_day)
        nocturnal = (not is_day) and new_mel > 0.30

        recent = list(self.state.get("recent_melatonin", []))
        recent.append(round(new_mel, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["aanat_activity"] = round(new_aanat, 4)
        self.state["pineal_norepinephrine"] = round(new_ne, 4)
        self.state["melatonin_drive"] = round(new_mel, 4)
        self.state["light_suppression"] = round(new_supp, 4)
        self.state["pineal_state"] = state
        self.state["nocturnal_phase_active"] = nocturnal
        self.state["recent_melatonin"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "aanat_activity": round(new_aanat, 4),
            "pineal_norepinephrine": round(new_ne, 4),
            "melatonin_drive": round(new_mel, 4),
            "light_suppression": round(new_supp, 4),
            "scn_phase_degrees": round(phase, 4),
            "nocturnal_signal": nocturnal,
            "nocturnal_phase_active": bool(nocturnal),
            "pineal_state": state,
            "scn_coupling_index": round(self._scn_coupling_index(new_mel), 4),
            "is_daytime": is_day,
        }
