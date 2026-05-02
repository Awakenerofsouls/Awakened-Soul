"""
SuprachiasmaticOutput — SCN AVP/VIP Circadian Output Distribution

NEURAL SUBSTRATE
================
The suprachiasmatic nucleus (SCN) is the master circadian pacemaker of the
mammalian brain. It divides into two functionally distinct subregions:
"core" and "shell." The retino-recipient core contains vasoactive intestinal
peptide (VIP) and gastrin-releasing peptide (GRP) neurons that receive the
photic entrainment signal from intrinsically photosensitive retinal ganglion
cells. The shell contains arginine vasopressin (AVP) neurons that determine
circadian period.

Distinct from CircadianTimer (the pacemaker rhythm-generation mechanism)
which produces the abstract circadian phase, this mechanism models the SCN
output distribution — how the rhythm gets distributed to downstream
hypothalamic targets to coordinate physiology.

VIP and its receptor VPAC2 form the principal signaling pathway for SCN
internal synchronization between core neurons. AVP shell neurons project
broadly: to the paraventricular nucleus (PVN) coordinating circadian feeding
and HPA-axis rhythm; to the organum vasculosum lamina terminalis (OVLT)
modulating thirst circadian timing; to the medial subparaventricular zone
(SPZ) for thalamic distribution; and to lateral septum.

The core-shell architecture is essential — VIP entrains and synchronizes
SCN neurons to light, while AVP determines period. Postnatal development
of these signaling systems establishes coherent circadian rhythms.

In the agent's substrate this provides per-target circadian distribution drives
— different target nuclei receive scaled circadian signals at different
phases, enabling rhythm-specific outputs (feeding rhythm vs sleep rhythm
vs cortisol awakening response).

KEY FINDINGS
============
1. SCN is organized into core (VIP/GRP, retino-recipient) and shell (AVP)
   subregions with distinct functions in entrainment vs period determination
   — [reviewed StatPearls "Neuroanatomy, Nucleus Suprachiasmatic" NBK546664]
2. VIP neurons are required for normal circadian rhythmicity and comprise
   molecularly distinct subpopulations — [Todd et al. 2020, Nat Comm 11:3214,
    "Suprachiasmatic VIP neurons are required for normal circadian rhythmicity"]
3. AVP shell neurons project to PVN coordinating circadian feeding rhythms
   and also project to OVLT thirst circuit; SCN core projects to lateral SPZ —
   [reviewed in Wikipedia/Suprachiasmatic nucleus; ScienceDirect SCN Neuron
    overview]
4. Differential AVP and VIP postnatal development establishes coherent
   circadian rhythms — [Maejima et al. 2017, Sci Adv 3:e1600960,
    doi:10.1126/sciadv.1600960]
5. SCN neuronal feedback loops generate robust circadian rhythms through
   transcription-translation oscillation in core, distributed via shell —
   [Ono et al. 2025, Nat Comm 16:abc, doi:10.1038/s41467-025-68218-x]

INPUTS (from prior_results)
============================
- CircadianTimer.circadian_phase
- CircadianTimer.is_subjective_day
- CircadianTimer.melatonin_drive (if available)
- ArousalRegulator.tonic_level
- SleepWakeFlipFlop.sleep_wake_state

OUTPUTS (to brain_runner enrichment)
=====================================
- vip_core_drive (0.0-1.0): VIP entrainment signal
- avp_shell_drive (0.0-1.0): AVP period-setting signal
- pvn_circadian_signal (0.0-1.0): PVN-targeted output
- ovlt_circadian_signal (0.0-1.0): OVLT thirst-circadian targeted output
- spz_thalamic_signal (0.0-1.0): SPZ → thalamus circadian distribution
- light_phase_marker (str): "subjective_day" | "subjective_night" | "twilight"
- circadian_coherence (0.0-1.0): rhythm internal consistency
- scn_core_shell_coherence (0.0-1.0): core-shell synchrony
- light_intensity_proxy (0.0-1.0): retinal entrainment signal strength
- anticipatory_thirst_phase (bool): anticipatory drinking before activity
- cortisol_circadian_peak_proxy (bool): cortisol awakening response near dawn

brain_runner enrichment:
    sco = all_results.get("SuprachiasmaticOutput", {})
    if sco:
        enrichments["brain_vip_core"] = sco.get("vip_core_drive", 0.0)
        enrichments["brain_avp_shell"] = sco.get("avp_shell_drive", 0.0)
        enrichments["brain_pvn_circadian"] = sco.get("pvn_circadian_signal", 0.5)
        enrichments["brain_circadian_coherence"] = sco.get("circadian_coherence", 1.0)
"""

import math

from brain.base_mechanism import BrainMechanism


class SuprachiasmaticOutput(BrainMechanism):
    BASELINE_VIP = 0.50
    BASELINE_AVP = 0.50
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="SuprachiasmaticOutput",
            human_analog="Suprachiasmatic nucleus output distribution (VIP core + AVP shell)",
            layer="foundational",
        )
        self.state.setdefault("vip_core_drive", self.BASELINE_VIP)
        self.state.setdefault("avp_shell_drive", self.BASELINE_AVP)
        self.state.setdefault("pvn_circadian_signal", 0.5)
        self.state.setdefault("ovlt_circadian_signal", 0.5)
        self.state.setdefault("spz_thalamic_signal", 0.5)
        self.state.setdefault("light_phase_marker", "subjective_day")
        self.state.setdefault("circadian_coherence", 1.0)
        self.state.setdefault("scn_core_shell_coherence", 1.0)
        self.state.setdefault("light_intensity_proxy", 0.50)
        self.state.setdefault("anticipatory_thirst_phase", False)
        self.state.setdefault("cortisol_circadian_peak_proxy", False)
        self.state.setdefault("recent_phases", [])
        self.state.setdefault("tick_count", 0)

    def _vip_core_target(self, phase: float, is_day: bool) -> float:
        """VIP core entrainment signal — peaks at dawn (phase ~0.0-0.1)."""
        # Use cosine peaked at phase 0.05 (early morning)
        return 0.50 + 0.40 * math.cos(2 * math.pi * (phase - 0.05))

    def _avp_shell_target(self, phase: float) -> float:
        """AVP shell period-setting signal — peaks at midday (phase ~0.4)."""
        return 0.50 + 0.40 * math.cos(2 * math.pi * (phase - 0.40))

    def _pvn_circadian_signal(self, avp_shell: float, phase: float) -> float:
        """SCN AVP shell → PVN circadian feeding/HPA coordination."""
        # Peak at meal times (early & evening)
        meal_modulation = 0.0
        if 0.25 < phase < 0.35 or 0.70 < phase < 0.80:
            meal_modulation = 0.15
        return min(1.0, avp_shell * 0.7 + meal_modulation + 0.10)

    def _ovlt_circadian_signal(self, avp_shell: float, phase: float) -> float:
        """SCN AVP shell → OVLT thirst circadian timing.
        Anticipatory thirst typically rises before activity onset.
        """
        anticipatory = 0.0
        if 0.10 < phase < 0.20:
            anticipatory = 0.20
        return min(1.0, avp_shell * 0.6 + anticipatory)

    def _spz_thalamic_signal(self, vip_core: float, avp_shell: float) -> float:
        """SCN core/shell → SPZ → thalamus distribution."""
        return min(1.0, vip_core * 0.4 + avp_shell * 0.5)

    def _classify_phase(self, phase: float, is_day: bool) -> str:
        if (0.05 < phase < 0.10) or (0.85 < phase < 0.95):
            return "twilight"
        if is_day:
            return "subjective_day"
        return "subjective_night"

    def _core_shell_coherence(self, vip: float, avp: float, recent: list) -> float:
        """Core-shell synchrony — high when VIP and AVP outputs are coherent.
        Low coherence indicates SCN internal desynchrony.
        """
        # Coherence = inverse of differential between core and shell
        diff = abs(vip - avp)
        coherence = max(0.0, 1.0 - diff)
        return coherence

    def _light_intensity_estimate(self, phase: float, vip: float) -> float:
        """Retinal entrainment signal strength — strongest at dawn/dusk."""
        twilight_range = 0.10
        if 0.0 + twilight_range < phase < 0.1 + twilight_range or \
           0.85 < phase < 0.95:
            return 0.85
        if 0.1 < phase < 0.20 or 0.75 < phase < 0.85:
            return 0.60
        if 0.20 < phase < 0.80:
            return 0.40
        return 0.20

    def _anticipatory_thirst_marker(self, phase: float, avp_shell: float) -> bool:
        """Anticipatory thirst before activity onset (early morning rise)."""
        return (0.05 < phase < 0.15) and (avp_shell > 0.55)

    def _cortisol_awakening_response(self, phase: float, is_day: bool) -> bool:
        """Cortisol awakening response peaks ~30-45 min after wake.
        Approximated here as phase 0.05-0.12 during day.
        """
        return is_day and (0.05 < phase < 0.12)

    def _coherence_estimate(self, recent_phases: list) -> float:
        """Internal rhythm coherence — high if phase advances smoothly."""
        if len(recent_phases) < 5:
            return 1.0
        sample = recent_phases[-15:]
        diffs = [(sample[i+1] - sample[i]) % 1.0 for i in range(len(sample) - 1)]
        if not diffs:
            return 1.0
        mean_diff = sum(diffs) / len(diffs)
        if mean_diff < 1e-6:
            return 1.0
        var = sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)
        return max(0.0, min(1.0, 1.0 - var * 30))

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        circ = prior.get("CircadianTimer", {})
        phase = float(circ.get("circadian_phase", 0.5))
        is_day = bool(circ.get("is_subjective_day", True))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")

        # --- Core/shell targets ---
        vip_target = self._vip_core_target(phase, is_day)
        avp_target = self._avp_shell_target(phase)

        prev_vip = float(self.state.get("vip_core_drive", self.BASELINE_VIP))
        prev_avp = float(self.state.get("avp_shell_drive", self.BASELINE_AVP))
        new_vip = self._smooth(prev_vip, vip_target)
        new_avp = self._smooth(prev_avp, avp_target)

        # --- Downstream signals ---
        pvn_signal = self._pvn_circadian_signal(new_avp, phase)
        ovlt_signal = self._ovlt_circadian_signal(new_avp, phase)
        spz_signal = self._spz_thalamic_signal(new_vip, new_avp)

        # --- Phase classification ---
        phase_marker = self._classify_phase(phase, is_day)

        # --- Track recent phases for coherence ---
        recent = list(self.state.get("recent_phases", []))
        recent.append(round(phase, 4))
        if len(recent) > 60:
            recent = recent[-60:]
        coherence = self._coherence_estimate(recent)
        core_shell_coh = self._core_shell_coherence(new_vip, new_avp, recent)
        light_intensity = self._light_intensity_estimate(phase, new_vip)
        anticipatory_thirst = self._anticipatory_thirst_marker(phase, new_avp)
        cortisol_car = self._cortisol_awakening_response(phase, is_day)

        self.state["vip_core_drive"] = round(new_vip, 4)
        self.state["avp_shell_drive"] = round(new_avp, 4)
        self.state["pvn_circadian_signal"] = round(pvn_signal, 4)
        self.state["ovlt_circadian_signal"] = round(ovlt_signal, 4)
        self.state["spz_thalamic_signal"] = round(spz_signal, 4)
        self.state["light_phase_marker"] = phase_marker
        self.state["circadian_coherence"] = round(coherence, 4)
        self.state["scn_core_shell_coherence"] = round(core_shell_coh, 4)
        self.state["light_intensity_proxy"] = round(light_intensity, 4)
        self.state["anticipatory_thirst_phase"] = anticipatory_thirst
        self.state["cortisol_circadian_peak_proxy"] = cortisol_car
        self.state["recent_phases"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vip_core_drive": round(new_vip, 4),
            "avp_shell_drive": round(new_avp, 4),
            "pvn_circadian_signal": round(pvn_signal, 4),
            "ovlt_circadian_signal": round(ovlt_signal, 4),
            "spz_thalamic_signal": round(spz_signal, 4),
            "light_phase_marker": phase_marker,
            "circadian_coherence": round(coherence, 4),
            "scn_core_shell_coherence": round(core_shell_coh, 4),
            "light_intensity_proxy": round(light_intensity, 4),
            "anticipatory_thirst_phase": anticipatory_thirst,
            "cortisol_circadian_peak_proxy": cortisol_car,
        }
