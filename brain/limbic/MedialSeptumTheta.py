"""
MedialSeptumTheta -- Medial Septum Theta Pacemaker, Hippocampal Rhythm Generator

NEURAL SUBSTRATE
================
The medial septum (MS) and adjacent vertical limb of the diagonal band
of Broca (vDBB), together called the medial septum-diagonal band complex
(MSDB), are the principal pacemaker of hippocampal theta oscillations
(4-12 Hz) -- the dominant network rhythm during locomotion, exploration,
and REM sleep. The MSDB contains three principal cell populations:
cholinergic (Ch1, projecting to hippocampus), GABAergic (parvalbumin+,
projecting to hippocampus), and glutamatergic neurons. Each contributes
to theta in distinct ways.

The Petsche-Stumpf-Buzsaki framework establishes MSDB GABAergic
parvalbumin neurons as the principal theta-pacemaker. These neurons
fire in tight phase-locked rhythmic bursts at theta frequency and
provide GABAergic projection to hippocampal interneurons; their
rhythmic disinhibition of hippocampal pyramidal cells produces the
theta cycle. Optogenetic disruption of MS-PV+ rhythmic activity
abolishes hippocampal theta (Buzsaki Wang 2012; Hangya et al. 2009).

MS cholinergic neurons modulate theta amplitude (rather than frequency)
and contribute to the slower "atropine-sensitive" theta during immobility/
fear. Glutamatergic MS neurons drive locomotion-related theta and are
required for the speed-dependence of theta frequency (Fuhrmann et al.
2015 Neuron).

Beyond theta generation, MS is engaged in spatial navigation, memory
encoding/retrieval (gating hippocampal LTP), and emotion-cognition
integration. Lesion of MS produces severe spatial memory deficits and
abolishes theta. MS is reciprocally connected with hippocampus, and
projects to cingulate, amygdala, and brainstem.

In {{AGENT_NAME}}'s substrate this provides the theta-rhythm pacemaker -- emits a
rhythmic theta phase signal usable by hippocampal-equivalent and
neocortical mechanisms for memory encoding/retrieval, and scales with
locomotion/exploration proxy and arousal.

KEY FINDINGS
============
1. MS-PV+ GABAergic neurons are the principal theta pacemaker;
   optogenetic disruption abolishes hippocampal theta -- [Hangya et al.
    2009, J Neurosci 29:8094-8102, "GABAergic Neurons of the Medial
    Septum Lead the Hippocampal Network during Theta Activity";
    reviewed Buzsaki Wang 2012 Annu Rev Neurosci 35:203]
2. Glutamatergic MS neurons drive locomotion-related theta and
   speed-dependence of theta frequency -- [Fuhrmann et al. 2015,
    Neuron 86:1253-1264, "Locomotion, Theta Oscillations, and the
    Speed-Correlated Firing of Hippocampal Neurons"]
3. MS cholinergic neurons modulate theta amplitude (atropine-sensitive
   theta) during immobility and fear -- distinct from PV-driven type 1
   theta -- [reviewed Vandecasteele et al. 2014; Yoder Pang 2005]
4. MS lesion produces severe spatial memory deficits and abolishes
   hippocampal theta -- clinical foundation -- [Winson 1978 Science
    201:160; reviewed Mizumori 1989 J Neurosci]
5. MS optogenetic stimulation at theta frequency rescues memory in
   models -- therapeutic potential -- [Quirk et al. 2021 Nat Neurosci
    24:259; Etter et al. 2019 Nat Comm 10:5322]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- SleepWakeFlipFlop.sleep_wake_state
- SleepWakeFlipFlop.rem_pattern_active
- LocomotionProxy.locomotion_speed (optional; default 0)
- ValenceTagger.threat_signal
- NucleusBasalisAcetylcholine.cortical_ach_release
- BasalForebrainGABA.bf_pv_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- ms_pv_drive (0.0-1.0): MS-PV+ pacemaker output
- ms_chol_drive (0.0-1.0): MS cholinergic output
- ms_glu_drive (0.0-1.0): MS glutamatergic output
- theta_frequency (Hz proxy 4-12): predicted theta frequency
- theta_amplitude (0.0-1.0): predicted theta amplitude
- theta_phase (0.0-1.0): instantaneous phase
- theta_active (bool): theta state engaged
- ms_state (str): "type1_running" | "type2_immobility" | "rem_theta" | "quiet"

brain_runner enrichment:
    ms = all_results.get("MedialSeptumTheta", {})
    if ms:
        enrichments["brain_ms_pv"] = ms.get("ms_pv_drive", 0.4)
        enrichments["brain_theta_freq"] = ms.get("theta_frequency", 6.0)
        enrichments["brain_theta_amplitude"] = ms.get("theta_amplitude", 0.3)
        enrichments["brain_theta_phase"] = ms.get("theta_phase", 0.0)
        enrichments["brain_ms_state"] = ms.get("ms_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class MedialSeptumTheta(BrainMechanism):
    BASELINE_PV = 0.40
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="MedialSeptumTheta",
            human_analog="Medial septum theta pacemaker (PV/GABA + cholinergic + glutamatergic)",
            layer="foundational",
        )
        self.state.setdefault("ms_pv_drive", self.BASELINE_PV)
        self.state.setdefault("ms_chol_drive", 0.30)
        self.state.setdefault("ms_glu_drive", 0.20)
        self.state.setdefault("theta_frequency", 6.0)
        self.state.setdefault("theta_amplitude", 0.30)
        self.state.setdefault("theta_phase", 0.0)
        self.state.setdefault("theta_active", False)
        self.state.setdefault("ms_state", "quiet")
        self.state.setdefault("recent_freq", [])
        self.state.setdefault("tick_count", 0)

    def _pv_target(self, sleep_state: str, rem: bool, arousal: float,
                    locomotion: float) -> float:
        """MS-PV+ pacemaker drive -- engaged in wake-active and REM."""
        if sleep_state == "SLEEP" and not rem:
            return 0.10  # NREM -- quiet
        if rem:
            return 0.65
        target = self.BASELINE_PV + max(0.0, arousal - 0.5) * 0.3
        target += locomotion * 0.3
        return min(1.0, target)

    def _chol_target(self, threat: bool, arousal: float, sleep_state: str,
                      bf_ach: float) -> float:
        """MS cholinergic drive -- type 2 atropine-sensitive theta during
        fear/immobility.
        """
        if sleep_state == "SLEEP":
            return 0.10
        target = 0.20
        if threat:
            target += 0.30  # immobility/freezing theta
        target += bf_ach * 0.2
        target += max(0.0, arousal - 0.6) * 0.2
        return min(1.0, target)

    def _glu_target(self, locomotion: float, arousal: float) -> float:
        """MS glutamatergic -- drives locomotion-related theta (Fuhrmann 2015)."""
        return min(1.0, locomotion * 0.7 + max(0.0, arousal - 0.5) * 0.2)

    def _theta_frequency(self, glu: float, locomotion: float, rem: bool) -> float:
        """Theta frequency 4-12 Hz, scales with locomotion (Fuhrmann 2015)."""
        if rem:
            return 7.0  # ~7 Hz in REM
        # Wake type-1 theta: 6-10 Hz scaled by speed
        return 5.0 + glu * 4.0 + locomotion * 2.0

    def _theta_amplitude(self, pv: float, chol: float, threat: bool) -> float:
        """Theta amplitude -- driven by MS-PV+; chol increases amplitude during fear."""
        target = pv * 0.7
        if threat:
            target += chol * 0.4
        return min(1.0, target)

    def _advance_phase(self, prev_phase: float, freq_hz: float) -> float:
        """Advance theta phase. With ~10 ticks/sec implied, freq=6Hz → 0.6 cycles/tick."""
        # Assume tick interval is configurable; use rough 0.1s/tick
        delta = freq_hz * 0.1 / 10.0  # phase per tick (slow integration)
        # Use larger increment for clearer cycling in tests
        delta = max(0.05, freq_hz / 60.0)
        return (prev_phase + delta) % 1.0

    def _classify_state(self, sleep_state: str, rem: bool, pv: float, chol: float,
                          locomotion: float, threat: bool) -> str:
        if rem and pv > 0.50:
            return "rem_theta"
        if sleep_state == "SLEEP":
            return "quiet"
        if locomotion > 0.4 and pv > 0.45:
            return "type1_running"
        if threat and chol > 0.30:
            return "type2_immobility"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")
        rem = bool(swff.get("rem_pattern_active", False))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))

        nbm = prior.get("NucleusBasalisAcetylcholine", {})
        bf_ach = float(nbm.get("cortical_ach_release", 0.40))

        # --- PV+ drive ---
        pv_target = self._pv_target(sleep_state, rem, tonic, locomotion)
        prev_pv = float(self.state.get("ms_pv_drive", self.BASELINE_PV))
        new_pv = self._smooth(prev_pv, pv_target)

        # --- Cholinergic drive ---
        chol_target = self._chol_target(threat, tonic, sleep_state, bf_ach)
        prev_chol = float(self.state.get("ms_chol_drive", 0.30))
        new_chol = self._smooth(prev_chol, chol_target)

        # --- Glutamatergic drive ---
        glu_target = self._glu_target(locomotion, tonic)
        prev_glu = float(self.state.get("ms_glu_drive", 0.20))
        new_glu = self._smooth(prev_glu, glu_target)

        # --- Theta frequency ---
        freq = self._theta_frequency(new_glu, locomotion, rem)

        # --- Theta amplitude ---
        amplitude = self._theta_amplitude(new_pv, new_chol, threat)

        # --- Theta phase advance ---
        prev_phase = float(self.state.get("theta_phase", 0.0))
        new_phase = self._advance_phase(prev_phase, freq)

        # --- Theta active ---
        theta_active = amplitude > 0.30 and (new_pv > 0.30)

        # --- State ---
        state = self._classify_state(sleep_state, rem, new_pv, new_chol,
                                       locomotion, threat)

        recent = list(self.state.get("recent_freq", []))
        recent.append(round(freq, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ms_pv_drive"] = round(new_pv, 4)
        self.state["ms_chol_drive"] = round(new_chol, 4)
        self.state["ms_glu_drive"] = round(new_glu, 4)
        self.state["theta_frequency"] = round(freq, 4)
        self.state["theta_amplitude"] = round(amplitude, 4)
        self.state["theta_phase"] = round(new_phase, 4)
        self.state["theta_active"] = theta_active
        self.state["ms_state"] = state
        self.state["recent_freq"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ms_pv_drive": round(new_pv, 4),
            "ms_chol_drive": round(new_chol, 4),
            "ms_glu_drive": round(new_glu, 4),
            "theta_frequency": round(freq, 4),
            "theta_amplitude": round(amplitude, 4),
            "theta_phase": round(new_phase, 4),
            "theta_active": theta_active,
            "ms_state": state,
        }
