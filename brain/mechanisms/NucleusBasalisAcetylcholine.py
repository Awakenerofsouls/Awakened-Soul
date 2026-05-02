"""
NucleusBasalisAcetylcholine — Nucleus Basalis of Meynert Cholinergic Cortical Modulator

NEURAL SUBSTRATE
================
The nucleus basalis of Meynert (NBM, Ch4) is the largest population of
cholinergic neurons in the mammalian basal forebrain. Its axons project
broadly across the entire cortical mantle, the olfactory tubercle, and the
amygdala, providing the principal source of acetylcholine (ACh) for the
cerebral cortex. NBM cholinergic neurons regulate arousal, selective
attention, multimodal sensory encoding, visual processing, and
experience-dependent cortical plasticity.

The signature electrophysiological effect of NBM activation is suppression
of low-frequency cortical oscillations (delta, theta, alpha) and facilitation
of high-frequency oscillations (beta, gamma) — the cortical desynchronization
of attentive wakefulness. NBM cholinergic discharge tracks behavioral arousal
state, increases during attentional task engagement, and is required for
consolidation of declarative memory.

NBM degeneration is a load-bearing pathology in Alzheimer's disease — the
loss of cortical cholinergic input correlates with cognitive decline severity.
NBM also dysregulates in schizophrenia, Lewy body dementia, and Parkinson's
disease.

In the agent's substrate this mechanism produces the cholinergic gain factor
that biases cortical processing toward signal-over-noise. High NBM drive
narrows attention, sharpens encoding, and supports working memory; low NBM
drive yields diffuse, low-effort cortical state.

KEY FINDINGS
============
1. NBM cholinergic projection (Ch4) provides the principal ACh innervation
   of cerebral cortex; NBM degeneration produces cortical cholinergic
   deficit signature of Alzheimer's disease — [Mesulam et al., reviewed
    in Liu et al. 2015, PMC4175400 "Cholinergic Circuitry of the Human
    Nucleus Basalis and Its Fate in Alzheimer's Disease"]
2. NBM activation desynchronizes cortex — suppresses delta/theta/alpha,
   facilitates beta/gamma — the signature of attentive arousal —
   [reviewed Frontiers 2024, doi:10.3389/fnagi.2024.1376764, "The role
    of the nucleus basalis of Meynert in neuromodulation therapy"]
3. NBM regulates attention, arousal, multimodal encoding, and
   experience-dependent cortical plasticity — required for normal
   declarative memory — [Sarter et al.; reviewed Frontiers Behav
    Neurosci 2017, doi:10.3389/fnbeh.2017.00010]
4. NBM degeneration is a major substrate of cognitive decline in AD,
   schizophrenia, Lewy body dementia, and Parkinson's disease —
   [Koulousakis et al. 2019, PubMed 31104014, J Alzheimer's Dis]
5. NBM cholinergic system regulates chronic pain processing via
   prelimbic cortex modulation — [Jiang et al. 2022, Nature Comm
    13:5270, doi:10.1038/s41467-022-32558-9]
6. NBM activity during REM sleep contributes to dreaming by
   desynchronizing cortical circuits — ACh tone during REM approaches
   wake levels, enabling cortical activation — [Steriade McCarley 1990,
    Brain Res Rev 15:95-105; reviewed in Hobson Pace-Schott 2002,
    "Sleep and Dreaming"]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- OrexinWakePromoter.orexin_drive
- DorsalRapheSerotonin.serotonin_drive
- ValenceTagger.valence_intensity
- VitalCoreRegulator.vital_drive
- SleepWakeFlipFlop.sleep_wake_state

OUTPUTS (to brain_runner enrichment)
=====================================
- ach_drive (0.0-1.0): cortical ACh release proxy
- cortical_gain (0.0-1.0): signal-to-noise gain factor
- gamma_facilitation (0.0-1.0): high-frequency oscillation drive
- low_freq_suppression (0.0-1.0): delta/theta/alpha suppression
- attentional_capacity (0.0-1.0): selective attention bandwidth
- cortical_plasticity_window (bool): conditions favoring encoding
- ad_dysfunction_marker (bool): chronically low ACh drive marker
- lc_ne_synergy_factor (0.0-1.0): LC NE synergizes with NBM for attention
- nbm_consciousness_index (0.0-1.0): cortical activation level for consciousness model

brain_runner enrichment:
    nba = all_results.get("NucleusBasalisAcetylcholine", {})
    if nba:
        enrichments["brain_ach_drive"] = nba.get("ach_drive", 0.5)
        enrichments["brain_cortical_gain"] = nba.get("cortical_gain", 0.5)
        enrichments["brain_gamma_facilitation"] = nba.get("gamma_facilitation", 0.0)
        enrichments["brain_attentional_capacity"] = nba.get("attentional_capacity", 0.5)
        enrichments["brain_plasticity_window"] = nba.get("cortical_plasticity_window", False)
"""

from brain.base_mechanism import BrainMechanism


class NucleusBasalisAcetylcholine(BrainMechanism):
    BASELINE_DRIVE = 0.45
    GAIN_BASELINE = 0.50
    PLASTICITY_THRESHOLD = 0.65
    AD_DYSFUNCTION_TICKS = 80
    AD_DYSFUNCTION_LOW_DRIVE = 0.25

    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="NucleusBasalisAcetylcholine",
            human_analog="Nucleus basalis of Meynert (Ch4) cholinergic cortical modulator",
            layer="foundational",
        )
        self.state.setdefault("ach_drive", self.BASELINE_DRIVE)
        self.state.setdefault("cortical_gain", self.GAIN_BASELINE)
        self.state.setdefault("gamma_facilitation", 0.0)
        self.state.setdefault("low_freq_suppression", 0.0)
        self.state.setdefault("attentional_capacity", 0.5)
        self.state.setdefault("cortical_plasticity_window", False)
        self.state.setdefault("ad_dysfunction_marker", False)
        self.state.setdefault("low_drive_streak", 0)
        self.state.setdefault("lc_ne_synergy_factor", 0.50)
        self.state.setdefault("nbm_consciousness_index", 0.5)
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _state_modulation(self, sleep_state: str) -> float:
        """NBM is high during wake, near-silent during NREM, partially active during REM."""
        if sleep_state == "WAKE":
            return 1.0
        if sleep_state == "TRANSITION":
            return 0.55
        if sleep_state == "SLEEP":
            return 0.20
        return 0.85

    def _attentional_bandwidth(self, gain: float, valence_intensity: float) -> float:
        """Selective attention bandwidth — narrow under high salience."""
        bandwidth = gain * 0.85
        if valence_intensity > 0.6:
            bandwidth = max(0.20, bandwidth - 0.15)  # narrowed by salience
        return min(1.0, bandwidth)

    def _gamma_drive_estimate(self, ach: float, arousal: float) -> float:
        """Gamma oscillation facilitation per cortical desynchronization signature."""
        return min(1.0, ach * 0.7 + max(0.0, arousal - 0.5) * 0.4)

    def _low_freq_suppression(self, ach: float) -> float:
        """Delta/theta/alpha suppression — saturates at high ACh."""
        return min(1.0, ach * 1.4)

    def _plasticity_gate(self, gain: float, gamma: float, valence: float) -> bool:
        """Encoding window: high gain + high gamma + moderate-high valence."""
        return gain > self.PLASTICITY_THRESHOLD and gamma > 0.5 and valence > 0.4

    def _detect_dysfunction(self, streak: int) -> bool:
        return streak > self.AD_DYSFUNCTION_TICKS

    def _lc_ne_synergy(self, tonic: float, orexin: float, serotonin: float) -> float:
        """LC NE and NBM interact bidirectionally:
        LC burst → NBM activation; NBM ACh → LC gain modulation.
        Synergy peaks during high arousal, phasic attention.
        """
        base = 0.50
        base += max(0.0, tonic - 0.5) * 0.5
        base += orexin * 0.25
        base -= serotonin * 0.10
        return min(1.0, max(0.0, base))

    def _consciousness_index(self, drive: float, gain: float,
                             low_suppression: float) -> float:
        """NBM-derived cortical activation index — used by consciousness model.
        High ACh + high gain + suppressed low-freq = high conscious activation.
        """
        return min(1.0, drive * 0.4 + gain * 0.4 + low_suppression * 0.2)

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        owp = prior.get("OrexinWakePromoter", {})
        orexin = float(owp.get("orexin_drive", 0.5))

        drs = prior.get("DorsalRapheSerotonin", {})
        serotonin = float(drs.get("serotonin_drive", 0.5))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        vcr = prior.get("VitalCoreRegulator", {})
        vital_drive = float(vcr.get("vital_drive", 0.5))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")

        # --- State modulation ---
        state_factor = self._state_modulation(sleep_state)

        # --- Compute target ACh drive ---
        # Convergent excitation from ARAS: orexin + 5-HT + LC NE (tonic) + arousal
        excitation = (
            tonic * 0.30
            + orexin * 0.25
            + serotonin * 0.20
            + max(0.0, valence_intensity - 0.4) * 0.20
        )
        if phasic:
            excitation += 0.10

        target = self.BASELINE_DRIVE + excitation * 0.7
        target *= state_factor
        target = max(0.05, min(0.98, target))

        prev_drive = float(self.state.get("ach_drive", self.BASELINE_DRIVE))
        new_drive = self._smooth(prev_drive, target)

        # --- Cortical gain ---
        gain_target = new_drive * 0.85 + max(0.0, vital_drive - 0.4) * 0.15
        gain_target = max(0.0, min(1.0, gain_target))
        prev_gain = float(self.state.get("cortical_gain", self.GAIN_BASELINE))
        new_gain = self._smooth(prev_gain, gain_target)

        # --- Gamma facilitation ---
        gamma = self._gamma_drive_estimate(new_drive, tonic)

        # --- Low-frequency suppression ---
        low_suppression = self._low_freq_suppression(new_drive)

        # --- Attentional bandwidth ---
        attentional_capacity = self._attentional_bandwidth(new_gain, valence_intensity)

        # --- Plasticity window ---
        plasticity = self._plasticity_gate(new_gain, gamma, max(valence_intensity, 0.4))

        # --- AD-dysfunction marker (chronic low drive) ---
        prev_streak = int(self.state.get("low_drive_streak", 0))
        if new_drive < self.AD_DYSFUNCTION_LOW_DRIVE:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 1)
        ad_marker = self._detect_dysfunction(streak)

        # --- LC-NE synergy ---
        lc_synergy = self._lc_ne_synergy(tonic, orexin, serotonin)

        # --- Consciousness index ---
        consciousness = self._consciousness_index(new_drive, new_gain, low_suppression)

        # --- Track recent ---
        recent = list(self.state.get("recent_drives", []))
        recent.append(round(new_drive, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ach_drive"] = round(new_drive, 4)
        self.state["cortical_gain"] = round(new_gain, 4)
        self.state["gamma_facilitation"] = round(gamma, 4)
        self.state["low_freq_suppression"] = round(low_suppression, 4)
        self.state["attentional_capacity"] = round(attentional_capacity, 4)
        self.state["cortical_plasticity_window"] = plasticity
        self.state["ad_dysfunction_marker"] = ad_marker
        self.state["low_drive_streak"] = streak
        self.state["lc_ne_synergy_factor"] = round(lc_synergy, 4)
        self.state["nbm_consciousness_index"] = round(consciousness, 4)
        self.state["recent_drives"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ach_drive": round(new_drive, 4),
            "cortical_gain": round(new_gain, 4),
            "gamma_facilitation": round(gamma, 4),
            "low_freq_suppression": round(low_suppression, 4),
            "attentional_capacity": round(attentional_capacity, 4),
            "cortical_plasticity_window": plasticity,
            "ad_dysfunction_marker": ad_marker,
            "lc_ne_synergy_factor": round(lc_synergy, 4),
            "nbm_consciousness_index": round(consciousness, 4),
        }
