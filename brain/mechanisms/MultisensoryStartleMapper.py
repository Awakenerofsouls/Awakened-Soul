"""
MultisensoryStartleMapper — Caudal Pontine Reticular Nucleus Startle Reflex

NEURAL SUBSTRATE
================
The acoustic / multisensory startle reflex is mediated by giant neurons in
the caudal pontine reticular nucleus (PnC) of the pons. PnC receives short-
latency convergent input from cochlear root neurons (auditory startle),
trigeminal mesencephalic afferents (tactile startle), and superior colliculus
(visual looming startle). PnC outputs to spinal motor neurons via reticulospinal
tract within ~6-10 ms of the eliciting stimulus, producing the rapid whole-body
startle response (eyeblink, neck flexion, limb flexion).

Startle is modulated bidirectionally:
  • Fear-potentiated startle (FPS): central nucleus of amygdala (CeA) projects
    to PnC; pre-existing fear state amplifies startle magnitude.
  • Pre-pulse inhibition (PPI): a weak preceding stimulus presented 30-500 ms
    before a startling stimulus reduces startle. PPI is mediated by pedunculopontine
    tegmental nucleus (PPT) inhibition of PnC and is a marker of sensorimotor gating.
  • Habituation: repeated startle stimuli produce progressively smaller responses
    via short-term synaptic depression in PnC.

PPI deficits are clinically associated with schizophrenia, OCD, and PTSD.
FPS is amplified in PTSD (hypervigilance). The startle system thus provides
a rapid index of both threat readiness and sensorimotor gating health.

KEY FINDINGS
============
1. PnC giant neurons mediate the primary startle pathway with ~6-10 ms latency
   from acoustic stimulus to motor output — [Yeomans Frankland 1995, Brain
    Res Rev 21:301-314]
2. CeA projection to PnC mediates fear-potentiated startle (FPS) — [Davis
    2006, Annu Rev Psychol 57:1-32]
3. Pre-pulse inhibition (PPI) reflects sensorimotor gating; PPT projects to
   PnC to inhibit startle when a weak prepulse precedes — [Swerdlow et al.
    2001, Schizophr Res 47:171-185]
4. Repeated startle elicits progressive habituation through synaptic depression
   at PnC — [Pilz Schnitzler 1996, Behav Brain Res 80:163-167]

INPUTS (from prior_results)
============================
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- VitalCoreRegulator.survival_threat_level
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- PredictionErrorDrift.surprise_magnitude

OUTPUTS
=======
- startle_baseline_threshold (0.0-1.0): how much surprise is needed to startle
- startle_event (bool): a startle just fired this tick
- startle_amplitude (0.0-1.0): magnitude of last startle
- fear_potentiated (bool): currently in FPS state
- ppi_active (bool): pre-pulse inhibition currently engaging
- habituation_level (0.0-1.0): repeated startle has dulled response

brain_runner enrichment:
    msm = all_results.get("MultisensoryStartleMapper", {})
    if msm:
        enrichments["brain_startle_event"] = msm.get("startle_event", False)
        enrichments["brain_startle_amplitude"] = msm.get("startle_amplitude", 0.0)
        enrichments["brain_fear_potentiated"] = msm.get("fear_potentiated", False)
        enrichments["brain_ppi_active"] = msm.get("ppi_active", False)
        enrichments["brain_startle_habituation"] = msm.get("habituation_level", 0.0)
"""

from brain.base_mechanism import BrainMechanism


class MultisensoryStartleMapper(BrainMechanism):
    BASELINE_THRESHOLD = 0.55
    FPS_THRESHOLD_REDUCTION = 0.20    # threat lowers threshold (more startles)
    HABITUATION_RATE = 0.05
    HABITUATION_RECOVERY = 0.02
    PPI_PREPULSE_TICKS = 1            # ticks where prior surprise was elevated but not enough

    SMOOTH = 0.30

    def __init__(self):
        super().__init__(
            name="MultisensoryStartleMapper_MultisensoryStartleMapper",
            human_analog="PnC startle reflex with FPS and PPI modulation",
            layer="foundational",
        )
        self.state.setdefault("startle_baseline_threshold", self.BASELINE_THRESHOLD)
        self.state.setdefault("startle_event", False)
        self.state.setdefault("startle_amplitude", 0.0)
        self.state.setdefault("fear_potentiated", False)
        self.state.setdefault("ppi_active", False)
        self.state.setdefault("habituation_level", 0.0)
        self.state.setdefault("startle_count", 0)
        self.state.setdefault("recent_surprises", [])
        self.state.setdefault("tick_count", 0)

    def _compute_threshold(self, threat: bool, threat_level: float, hab: float) -> float:
        thr = self.BASELINE_THRESHOLD
        if threat:
            thr -= self.FPS_THRESHOLD_REDUCTION
        thr -= max(0.0, threat_level - 0.5) * 0.2
        thr += hab * 0.2  # habituation raises threshold
        return max(0.20, min(0.95, thr))

    def _detect_ppi(self, recent: list) -> bool:
        """If a moderate-magnitude surprise occurred 1 tick ago, current startle is gated."""
        if len(recent) < 2:
            return False
        prior = recent[-2]
        return 0.30 < prior < self.BASELINE_THRESHOLD

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _ppi_strength_estimate(self, recent: list) -> float:
        """Strength of pre-pulse inhibition gating (Swerdlow 2001).
        Healthy gating shows sustained PPI; deficits suggest dysregulation
        (clinical correlate of schizophrenia, OCD, PTSD).
        """
        if len(recent) < 10:
            return 0.7  # default healthy
        sample = recent[-20:]
        # Count moderate prepulses (between 0.30-0.55)
        prepulses = sum(1 for x in sample if 0.30 < x < 0.55)
        return min(1.0, prepulses / 5.0)

    def _amygdala_modulation_drive(self, threat: bool, intensity: float, sustained: bool) -> float:
        """CeA → PnC drive (Davis 2006).
        Phasic threat = phasic CeA drive; sustained threat (BNST-mediated) = different pattern.
        """
        if not threat:
            return 0.0
        base = intensity * 0.7
        if sustained:
            base *= 1.2
        return min(1.0, base)

    def _detect_hypervigilance(self, startle_count: int, recent_modes: list, fear_pot: bool) -> bool:
        """Persistent fear-potentiated state with frequent startles = hypervigilance.
        Clinical PTSD correlate.
        """
        if startle_count < 5:
            return False
        recent_fps = sum(1 for _ in recent_modes[-30:] if _)  # placeholder
        return fear_pot and startle_count > 5

    def _classify_gating_state(self, ppi: bool, hab: float, threshold: float) -> str:
        """Classify current sensorimotor gating health."""
        if ppi:
            return "ppi_engaged"
        if hab > 0.6:
            return "habituated"
        if threshold < 0.30:
            return "low_threshold_hyper"
        return "normal_gating"

    def _short_latency_pathway_proxy(self, surprise: float) -> float:
        """6-10 ms cochlear-root → PnC → spinal motor latency proxy.
        Returns '1.0' = full short-latency response on this tick.
        """
        # Above threshold → full response within tick
        if surprise > 0.55:
            return 1.0
        return surprise * 1.5

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        vcr = prior.get("VitalCoreRegulator", {})
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic_burst = bool(arousal.get("phasic_burst_active", False))

        ped = prior.get("PredictionErrorDrift", {})
        surprise = float(ped.get("surprise_magnitude", 0.0))

        # --- Track surprise history ---
        recent = list(self.state.get("recent_surprises", []))

        # --- Determine current threshold (FPS reduction, habituation rise) ---
        prev_hab = float(self.state.get("habituation_level", 0.0))
        threshold = self._compute_threshold(threat_signal, survival_threat, prev_hab)

        # --- PPI detection from prior tick ---
        ppi_active = self._detect_ppi(recent)

        # --- Determine if this tick triggers a startle ---
        adjusted_surprise = surprise
        if ppi_active:
            adjusted_surprise *= 0.5    # PPI attenuates startle by ~50%

        startle_fires = adjusted_surprise > threshold

        # --- Compute startle amplitude ---
        if startle_fires:
            amplitude = min(1.0, adjusted_surprise * 1.2)
            if threat_signal:
                amplitude = min(1.0, amplitude + 0.15)  # FPS amplification
            new_hab = min(1.0, prev_hab + self.HABITUATION_RATE)
            startle_count = int(self.state.get("startle_count", 0)) + 1
        else:
            amplitude = max(0.0, float(self.state.get("startle_amplitude", 0.0)) - 0.15)
            new_hab = max(0.0, prev_hab - self.HABITUATION_RECOVERY)
            startle_count = int(self.state.get("startle_count", 0))

        # --- Track surprise (after PPI computation) ---
        recent.append(round(surprise, 4))
        if len(recent) > 30:
            recent = recent[-30:]

        # --- PPI strength estimate (Swerdlow 2001) ---
        ppi_strength = self._ppi_strength_estimate(recent)

        # --- CeA-PnC modulation (Davis 2006) ---
        cea_drive = self._amygdala_modulation_drive(threat_signal, valence_intensity, survival_threat > 0.5)

        # --- Short-latency response proxy ---
        short_latency = self._short_latency_pathway_proxy(adjusted_surprise)

        # --- Hypervigilance detection ---
        recent_modes = list(self.state.get("recent_surprises", []))[-30:]
        hypervigilant = self._detect_hypervigilance(startle_count, recent_modes, threat_signal and survival_threat > 0.5)

        # --- Fear potentiation flag ---
        fear_potentiated = (
            threat_signal
            and survival_threat > 0.45
            and tonic > 0.55
        )

        # --- Gating state classification ---
        gating_state = self._classify_gating_state(ppi_active, new_hab, threshold)

        self.state["startle_baseline_threshold"] = round(threshold, 4)
        self.state["startle_event"] = startle_fires
        self.state["startle_amplitude"] = round(amplitude, 4)
        self.state["fear_potentiated"] = fear_potentiated
        self.state["ppi_active"] = ppi_active
        self.state["habituation_level"] = round(new_hab, 4)
        self.state["startle_count"] = startle_count
        self.state["recent_surprises"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        self.state["ppi_strength"] = round(ppi_strength, 4)
        self.state["cea_drive"] = round(cea_drive, 4)
        self.state["short_latency_response"] = round(short_latency, 4)
        self.state["hypervigilance_state"] = hypervigilant
        self.state["gating_state"] = gating_state

        return {
            "startle_baseline_threshold": round(threshold, 4),
            "startle_event": startle_fires,
            "startle_amplitude": round(amplitude, 4),
            "fear_potentiated": fear_potentiated,
            "ppi_active": ppi_active,
            "habituation_level": round(new_hab, 4),
            "ppi_strength": round(ppi_strength, 4),
            "cea_drive": round(cea_drive, 4),
            "short_latency_response": round(short_latency, 4),
            "hypervigilance_state": hypervigilant,
            "gating_state": gating_state,
        }
