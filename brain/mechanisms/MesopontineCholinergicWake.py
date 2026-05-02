"""
MesopontineCholinergicWake — PPT/LDT Cholinergic Wake/REM Drivers

NEURAL SUBSTRATE
================
The pedunculopontine tegmental nucleus (PPT, also PPN or PPTg) and the
laterodorsal tegmental nucleus (LDT) are clusters of large cholinergic
neurons at the junction of the midbrain and pons. Together with intermixed
glutamatergic and GABAergic populations, PPT/LDT form the mesopontine
cholinergic system that is part of the ascending arousal system.

PPT/LDT cholinergic neurons project broadly to arousal-related targets:
ventral tegmental area (VTA), lateral hypothalamus, basal forebrain,
frontal cortex, and many thalamic nuclei. These projections control thalamic
firing mode through nicotinic and muscarinic effects, gating information
flow to cortex during wake-sleep transitions and during arousal modulation
within wakefulness.

A subpopulation of LDT/PPT cholinergic neurons is selectively active during
REM sleep — these are the principal substrate of REM-state ACh release that
desynchronizes cortex during dreaming. Other LDT/PPT cholinergic neurons
are active in both wake and REM (the "wake/REM-on" population).

Glutamatergic and GABAergic LDT/PPT subpopulations have distinct effects
on sleep/wake — recent optogenetic work (Kroeger 2017) showed that
cholinergic, glutamatergic, and GABAergic PPT neurons each have separable
roles in promoting wake or sleep.

In the agent's substrate this provides the cortical-thalamic ACh signal that
gates information flow to cortex, complementing NBM (which handles
cortical ACh directly to neocortex) by providing the thalamic gating layer.

KEY FINDINGS
============
1. PPT/LDT cholinergic neurons are part of the ascending arousal system,
   projecting to thalamus, VTA, basal forebrain, and frontal cortex —
   [reviewed PMC10900045, "The regulation of the pedunculopontine
    tegmental nucleus in sleep-wake states"]
2. PPT contains cholinergic, glutamatergic, and GABAergic populations
   with distinct effects on sleep/wake behavior — [Kroeger et al. 2017,
    J Neurosci 37:1352-1366, doi:10.1523/JNEUROSCI.1405-16.2016 PMC5296799]
3. A subpopulation of LDT/PPT cholinergic neurons is selectively active
   during REM sleep, mediating REM-state ACh release — [reviewed
    SpringerLink "Involvement of GABAergic Mechanisms in the LDT-PPT
    in the Promotion of REM Sleep"]
4. PPT/LDT cholinergic projection gates thalamocortical firing mode
   through nicotinic and muscarinic effects, controlling sensory
   information flow to cortex — [reviewed PMC2972721, Frontiers
    Neuroanatomy "Cholinergic and Non-Cholinergic Projections from
    PPT and LDT Nuclei to the Medial Geniculate Body"]
5. The PPT/LDT cholinergic system is a clinical target — degeneration
   in Parkinson disease produces sleep-wake disturbance, RBD —
   [reviewed PMC3026477, "Neuropharmacology of Sleep and Wakefulness"]
6. LDT/PPT cholinergic neurons encode reward prediction errors via
   VTA and basal forebrain projections — their activity tracks
   expectation of reward, integrating with dopaminergic signaling —
   [Dja et al. 2022, Curr Biol 32:R1305-R1317, doi:10.1016/j.cub.2022.11.023]
7. Burst-type stimulation of PPT induces cortical gamma oscillations
   (30-80 Hz) via thalamocortical relay — effective frequency for
   cortical activation differs from tonic stimulation —
   [Razik McGreevy 2012, PMC3581098 "Cholinergic Mechanisms of
    Brain Stem Neurons"}

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- SleepWakeFlipFlop.sleep_wake_state
- SleepWakeFlipFlop.rem_pattern_active
- OrexinWakePromoter.orexin_drive
- DorsalRapheSerotonin.serotonin_drive
- ValenceTagger.valence_intensity
- RewardPavlovianAssociative.approaching_reward

OUTPUTS (to brain_runner enrichment)
=====================================
- ach_wake_drive (0.0-1.0): wake-active cholinergic output
- ach_rem_drive (0.0-1.0): REM-active cholinergic output
- ppt_glutamate_drive (0.0-1.0)
- ppt_gaba_drive (0.0-1.0)
- thalamocortical_gain (0.0-1.0): thalamic gating effect on cortex
- mesopontine_state (str): "wake_active" | "rem_active" | "nrem_silent" | "transition"
- mesopontine_reward_prediction_signal (0.0-1.0): LDT/PPT RPE encoding
- cortical_gamma_burst_proxy (0.0-1.0): gamma oscillation facilitation

brain_runner enrichment:
    mcw = all_results.get("MesopontineCholinergicWake", {})
    if mcw:
        enrichments["brain_ach_wake_drive"] = mcw.get("ach_wake_drive", 0.5)
        enrichments["brain_ach_rem_drive"] = mcw.get("ach_rem_drive", 0.0)
        enrichments["brain_thalamocortical_gain"] = mcw.get("thalamocortical_gain", 0.5)
        enrichments["brain_mesopontine_state"] = mcw.get("mesopontine_state", "wake_active")
"""

from brain.base_mechanism import BrainMechanism


class MesopontineCholinergicWake(BrainMechanism):
    BASELINE_WAKE = 0.55
    BASELINE_REM = 0.05
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="MesopontineCholinergicWake",
            human_analog="PPT/LDT cholinergic wake/REM drivers",
            layer="foundational",
        )
        self.state.setdefault("ach_wake_drive", self.BASELINE_WAKE)
        self.state.setdefault("ach_rem_drive", self.BASELINE_REM)
        self.state.setdefault("ppt_glutamate_drive", 0.40)
        self.state.setdefault("ppt_gaba_drive", 0.30)
        self.state.setdefault("thalamocortical_gain", 0.5)
        self.state.setdefault("mesopontine_state", "wake_active")
        self.state.setdefault("mesopontine_reward_prediction_signal", 0.0)
        self.state.setdefault("cortical_gamma_burst_proxy", 0.0)
        self.state.setdefault("prev_ach_wake", self.BASELINE_WAKE)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _wake_active_target(self, sleep_state: str, orexin: float, tonic: float) -> float:
        if sleep_state == "WAKE":
            return min(1.0, self.BASELINE_WAKE + orexin * 0.3 + (tonic - 0.5) * 0.4)
        if sleep_state == "TRANSITION":
            return self.BASELINE_WAKE * 0.6
        return 0.10

    def _rem_active_target(self, sleep_state: str, rem_pattern: bool) -> float:
        if rem_pattern:
            return 0.85
        if sleep_state == "SLEEP":
            return 0.20
        return self.BASELINE_REM

    def _glutamate_target(self, tonic: float, sleep_state: str) -> float:
        """Glutamatergic PPT — mostly wake-promoting (Kroeger 2017)."""
        if sleep_state == "WAKE":
            return min(1.0, 0.4 + tonic * 0.3)
        return 0.15

    def _gaba_target(self, sleep_state: str) -> float:
        """GABAergic PPT — mostly sleep-promoting."""
        if sleep_state == "SLEEP":
            return 0.65
        if sleep_state == "TRANSITION":
            return 0.45
        return 0.20

    def _thalamocortical_gain(self, ach_wake: float, ach_rem: float, glut: float) -> float:
        """Net thalamocortical gain — both wake and REM ACh enhance cortical
        processing, GABA reduces it.
        """
        return max(0.0, min(1.0, ach_wake * 0.5 + ach_rem * 0.4 + glut * 0.2))

    def _reward_prediction_signal(self, valence_intensity: float, orexin: float,
                                   serotonin: float, approaching: bool) -> float:
        """LDT/PPT encodes reward prediction errors via VTA/basal forebrain.
        RPE tracks valence, orexin, 5-HT mod, and behavioral approach.
        """
        base = 0.20
        base += max(0.0, valence_intensity - 0.5) * 0.3
        base += orexin * 0.20
        base -= serotonin * 0.10
        if approaching:
            base += 0.15
        return min(1.0, max(0.0, base))

    def _gamma_burst_proxy(self, prev_wake: float, new_wake: float,
                           ach_rem: float) -> float:
        """Burst-type stimulation of PPT → cortical gamma oscillations.
        Gamma burst detected when wake drive shows sharp rise (burst onset).
        """
        wake_delta = new_wake - prev_wake
        if wake_delta > 0.05:
            return min(1.0, wake_delta * 5.0 + ach_rem * 0.3)
        return ach_rem * 0.4

    def _classify_state(self, sleep_state: str, ach_wake: float, ach_rem: float) -> str:
        if ach_rem > 0.6:
            return "rem_active"
        if sleep_state == "WAKE" and ach_wake > 0.4:
            return "wake_active"
        if sleep_state == "TRANSITION":
            return "transition"
        return "nrem_silent"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")
        rem_pattern = bool(swff.get("rem_pattern_active", False))

        owp = prior.get("OrexinWakePromoter", {})
        orexin = float(owp.get("orexin_drive", 0.5))

        drs = prior.get("DorsalRapheSerotonin", {})
        serotonin = float(drs.get("serotonin_drive", 0.5))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        rpa = prior.get("RewardPavlovianAssociative", {})
        approaching = bool(rpa.get("approaching_reward", False))

        # --- Drives ---
        wake_target = self._wake_active_target(sleep_state, orexin, tonic)
        rem_target = self._rem_active_target(sleep_state, rem_pattern)
        glut_target = self._glutamate_target(tonic, sleep_state)
        gaba_target = self._gaba_target(sleep_state)

        prev_wake = float(self.state.get("ach_wake_drive", self.BASELINE_WAKE))
        prev_rem = float(self.state.get("ach_rem_drive", self.BASELINE_REM))
        prev_glut = float(self.state.get("ppt_glutamate_drive", 0.40))
        prev_gaba = float(self.state.get("ppt_gaba_drive", 0.30))

        new_wake = self._smooth(prev_wake, wake_target)
        new_rem = self._smooth(prev_rem, rem_target)
        new_glut = self._smooth(prev_glut, glut_target)
        new_gaba = self._smooth(prev_gaba, gaba_target)

        # --- Thalamocortical gain ---
        thalamocortical = self._thalamocortical_gain(new_wake, new_rem, new_glut)

        # --- Reward prediction signal ---
        rpe_signal = self._reward_prediction_signal(
            valence_intensity, orexin, serotonin, approaching
        )

        # --- Cortical gamma burst ---
        gamma_burst = self._gamma_burst_proxy(prev_wake, new_wake, new_rem)

        # --- State classification ---
        state = self._classify_state(sleep_state, new_wake, new_rem)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ach_wake_drive"] = round(new_wake, 4)
        self.state["ach_rem_drive"] = round(new_rem, 4)
        self.state["ppt_glutamate_drive"] = round(new_glut, 4)
        self.state["ppt_gaba_drive"] = round(new_gaba, 4)
        self.state["thalamocortical_gain"] = round(thalamocortical, 4)
        self.state["mesopontine_state"] = state
        self.state["mesopontine_reward_prediction_signal"] = round(rpe_signal, 4)
        self.state["cortical_gamma_burst_proxy"] = round(gamma_burst, 4)
        self.state["prev_ach_wake"] = round(new_wake, 4)
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ach_wake_drive": round(new_wake, 4),
            "ach_rem_drive": round(new_rem, 4),
            "ppt_glutamate_drive": round(new_glut, 4),
            "ppt_gaba_drive": round(new_gaba, 4),
            "thalamocortical_gain": round(thalamocortical, 4),
            "mesopontine_state": state,
            "mesopontine_reward_prediction_signal": round(rpe_signal, 4),
            "cortical_gamma_burst_proxy": round(gamma_burst, 4),
        }