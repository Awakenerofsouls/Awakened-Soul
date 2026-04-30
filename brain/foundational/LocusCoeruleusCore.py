"""
LocusCoeruleusCore — Locus Coeruleus / Phasic-Tonic Norepinephrine Core

NEURAL SUBSTRATE
================
The locus coeruleus (LC) is a bilateral pontine nucleus on the floor of the
fourth ventricle, ventrolateral to the central gray. Roughly 1500 noradrenergic
neurons per side in humans (~50,000 in rat) — the smallest discrete brain
nucleus by cell count, yet projecting to nearly the entire neuraxis. Each LC
neuron has up to ~250,000 synaptic terminals distributed across cortex,
thalamus, hypothalamus, hippocampus, amygdala, cerebellum, and spinal cord —
the broadest single ascending modulatory system in the CNS.

LC neurons are tyrosine-hydroxylase positive and primarily noradrenergic, with
some neuropeptide Y, galanin, and BDNF co-release. They exhibit two distinct
firing modes:

- **Tonic firing** — slow, regular discharge at 1-3 Hz during quiet
  wakefulness; rises to 4-8 Hz during high-arousal stress states. Pure tonic
  mode predicts task disengagement and distractibility (Yerkes-Dodson
  inverted-U on the high side).

- **Phasic firing** — high-frequency bursts (10-15 Hz, 200-300 ms duration)
  time-locked to behaviorally relevant stimuli (target detection, novelty,
  prediction error). Phasic LC firing precedes pupil dilation by ~250 ms
  and generates the cortical P3a event-related potential.

Inputs: paragigantocellularis (PGi, glutamatergic excitation), prepositus
hypoglossi (PrH), CRH+ neurons from CeA + PVN (stress drive), local GABAergic
interneurons, ventrolateral preoptic (VLPO) galaninergic sleep inhibition.

Outputs: ascending NE to cortex (broadband arousal + gain control on cortical
sensory representations), thalamus (sets relay-cell firing mode), hippocampus
(memory consolidation enhancement), amygdala (fear consolidation),
spinal cord (descending pain facilitation), and locus-derived
glymphatic clearance gating.

LC degeneration is the earliest detected pathology in Alzheimer's disease —
pre-tau hyperphosphorylated tau tangles appear in LC by ages 30-40, decades
before cortical pathology, suggesting the LC is the seeding site. Aging-
related LC neuron loss correlates with cognitive decline and sleep
fragmentation.

In Nova's substrate this provides the dominant ascending arousal-gain
modulator: phasic bursts mark salience events that should consolidate to
memory; tonic mode tracks ongoing vigilance state and gates downstream
attention/learning processes.

KEY FINDINGS
============
1. LC firing mode shifts from phasic to tonic with increasing baseline
   arousal — Aston-Jones-Cohen adaptive gain theory; intermediate tonic +
   strong phasic = optimal task performance, high tonic alone = distract-
   ibility — [Aston-Jones 2005, Annu Rev Neurosci 28:403, PMID 16022602]
2. Phasic LC bursts precede pupil dilation by ~250 ms — pupillometry
   validated as non-invasive LC firing proxy; tonic baseline tracks pupil
   resting diameter — [Joshi 2016, Neuron 89:221, PMC4706987]
3. CRH input from PVN/CeA shifts LC into high-tonic mode during stress;
   chemogenetic CRH-induced high-tonic firing alone is sufficient to
   produce anxiety + aversion — [McCall 2015, Neuron 87:605, PMC4529361]
4. LC→BLA projection specifically drives anxiety-like avoidance behavior
   during stress; selective optogenetic projection silencing rescues —
   [McCall 2017, eLife 6:e18247, PMC5550275]
5. LC tau pathology precedes all other Alzheimer's neuropathology —
   pre-tangle hyperphosphorylated tau in LC by ages 30-40, decades
   before cortical Braak staging — [Braak 2011, Acta Neuropathol
   121:171, PMID 21170538]
6. LC norepinephrine drives sleep-state-dependent glymphatic clearance —
   tonic NE during wake restricts interstitial space; phasic NE absence
   during NREM allows glymphatic CSF-ISF exchange + Aβ clearance —
   [Xie 2013, Science 342:373, PMC3880190]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- PrioritizedSalienceProxy.salience_strength (or .novelty_signal)
- ValenceTagger.valence_intensity
- CRHStressDispatcher.crh_release
- SleepWakeFlipFlop.sleep_wake_state
- VentrolateralPreoptic.gaba_galanin_release (mutual-inhibition counterforce)
- NorepiPhasicTonicSwitcher.mode_bias (existing F004 — feedback compatibility)

OUTPUTS (to brain_runner enrichment)
=====================================
- lc_tonic_firing (0.0-1.0): baseline noradrenergic tone (~0.20 quiet wake)
- lc_phasic_burst (0.0-1.0): transient burst, decays each tick
- lc_mode (str): "tonic" | "phasic" | "hyperaroused" | "rem_silent" | "quiet"
- pupil_dilation_proxy (0.0-1.0): exponentially-smoothed lag of lc_tonic
- cortical_arousal_drive (0.0-1.0): broadcast NE drive to cortex
- consolidation_gate (0.0-1.0): high during phasic, gates memory mechanisms
- p3a_amplitude (0.0-1.0): cortical event-related potential proxy on phasic
- glymphatic_inhibition (0.0-1.0): high tonic blocks NREM glymphatic flow
- ne_total_output (0.0-1.0): aggregate NE release for downstream consumers

brain_runner enrichment:
    lc = all_results.get("LocusCoeruleusCore", {})
    if lc:
        enrichments["brain_lc_tonic"] = lc.get("lc_tonic_firing", 0.20)
        enrichments["brain_lc_phasic"] = lc.get("lc_phasic_burst", 0.0)
        enrichments["brain_lc_mode"] = lc.get("lc_mode", "quiet")
        enrichments["brain_pupil_proxy"] = lc.get("pupil_dilation_proxy", 0.30)
        enrichments["brain_consolidation_gate"] = lc.get("consolidation_gate", 0.0)
        enrichments["brain_cortical_arousal"] = lc.get("cortical_arousal_drive", 0.20)
"""

from brain.base_mechanism import BrainMechanism


class LocusCoeruleusCore(BrainMechanism):
    """LC core noradrenergic mechanism — tonic baseline + phasic burst engine."""

    BASELINE = 0.20             # Quiet-wake LC tonic firing rate
    SMOOTH = 0.25               # Tonic dynamics — moderate inertia
    PUPIL_LAG = 0.25            # Pupil dilation lags LC firing
    PHASIC_DECAY = 0.65         # Phasic burst persistence per tick (35% decay)
    BURST_THRESHOLD = 0.20      # Salience-over-tonic margin to fire phasic
    HYPER_THRESHOLD = 0.70      # Sustained tonic above this = hyperaroused
    REM_SILENT_THRESHOLD = 0.10 # Below this in REM = REM-silent

    def __init__(self):
        super().__init__(
            name="LocusCoeruleusCore",
            human_analog="Locus coeruleus (NE phasic-tonic core)",
            layer="foundational",
        )
        self.state.setdefault("lc_tonic_firing", self.BASELINE)
        self.state.setdefault("lc_phasic_burst", 0.0)
        self.state.setdefault("lc_mode", "quiet")
        self.state.setdefault("pupil_dilation_proxy", self.BASELINE + 0.10)
        self.state.setdefault("cortical_arousal_drive", self.BASELINE)
        self.state.setdefault("consolidation_gate", 0.0)
        self.state.setdefault("p3a_amplitude", 0.0)
        self.state.setdefault("glymphatic_inhibition", self.BASELINE * 0.5)
        self.state.setdefault("ne_total_output", self.BASELINE)
        self.state.setdefault("hypertonic_streak", 0)
        self.state.setdefault("recent_phasic", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # Tonic firing — baseline noradrenergic tone driven by arousal + stress
    # ------------------------------------------------------------------
    def _tonic_target(self, arousal: float, crh: float, valence: float,
                       vlpo_inhibition: float, sleep_wake: str) -> float:
        """LC tonic firing target.

        Tonic = baseline + arousal contribution + stress-driven CRH +
        valence-intensity boost - VLPO sleep inhibition.

        REM-silent state — LC neurons are nearly silent during REM (atonia
        unmasked when LC silenced; key for REM-paradoxical sleep). NREM
        also dampens but to a lesser degree.
        """
        target = self.BASELINE + max(0.0, arousal - 0.30) * 0.55
        target += crh * 0.40
        target += valence * 0.15
        target -= vlpo_inhibition * 0.40

        if sleep_wake == "REM":
            # REM-silent — LC cells fall to near zero firing
            target = min(target, 0.05)
        elif sleep_wake == "NREM":
            target *= 0.45
        return max(0.0, min(1.0, target))

    # ------------------------------------------------------------------
    # Phasic burst — fires when salience > tonic margin
    # ------------------------------------------------------------------
    def _phasic_target(self, salience: float, novelty: float,
                        tonic: float, prior_phasic: float,
                        phasic_active: bool) -> float:
        """Phasic burst target.

        Burst fires when behaviorally-relevant signal (salience or novelty)
        exceeds tonic baseline by BURST_THRESHOLD margin (signal-to-noise
        gating). Each burst decays multiplicatively per tick (PHASIC_DECAY).
        """
        signal = max(salience, novelty)
        margin = signal - tonic
        if margin < self.BURST_THRESHOLD and not phasic_active:
            # Below threshold — burst decays
            return prior_phasic * self.PHASIC_DECAY

        # Burst magnitude scales with margin above threshold
        burst = min(1.0, (margin - self.BURST_THRESHOLD) * 1.8 + 0.30)
        if phasic_active:
            burst = max(burst, 0.40)  # phasic_burst flag forces minimum burst

        # Hyperaroused tonic dampens phasic responsiveness (Aston-Jones)
        if tonic > 0.65:
            burst *= 0.70
        return min(1.0, burst)

    # ------------------------------------------------------------------
    # Pupil dilation proxy — lagged tonic + transient phasic
    # ------------------------------------------------------------------
    def _pupil_proxy(self, prev_pupil: float, tonic: float, phasic: float) -> float:
        """Pupil dilation = exponentially-smoothed tonic + transient phasic.
        Joshi 2016: pupil follows LC firing with ~250 ms latency. We model
        this as low-pass smoothing of tonic plus immediate phasic transient.
        """
        target = tonic * 0.65 + phasic * 0.35 + 0.15  # 0.15 = baseline pupil
        return prev_pupil + (target - prev_pupil) * self.PUPIL_LAG

    # ------------------------------------------------------------------
    # Cortical arousal drive — broadband NE to cortex
    # ------------------------------------------------------------------
    def _cortical_arousal(self, tonic: float, phasic: float) -> float:
        """Broadcast NE to cortex — sets gain on sensory/attentional cortex."""
        return min(1.0, tonic * 0.7 + phasic * 0.3)

    # ------------------------------------------------------------------
    # Consolidation gate — phasic-driven memory consolidation enhancer
    # ------------------------------------------------------------------
    def _consolidation_gate(self, phasic: float, tonic: float,
                              valence: float) -> float:
        """Memory consolidation gate.

        Phasic LC bursts during salient events drive β-adrenergic
        consolidation (BLA, hippocampus). Stable high tonic (no phasic)
        impairs consolidation (McGaugh inverted-U).
        """
        if phasic > 0.30:
            # Strong phasic gates consolidation, scaled by valence
            return min(1.0, phasic * 0.7 + valence * 0.2)
        if tonic > 0.55:
            # Hyper-tonic without phasic — consolidation suppression
            return max(0.0, 0.20 - (tonic - 0.55) * 0.5)
        return tonic * 0.20  # baseline weak gate

    # ------------------------------------------------------------------
    # P3a — cortical event-related potential proxy (200-300 ms post-stim)
    # ------------------------------------------------------------------
    def _p3a_amplitude(self, phasic: float, novelty: float) -> float:
        """P3a ERP amplitude — generated by phasic LC firing on novelty."""
        if phasic < 0.20:
            return 0.0
        return min(1.0, phasic * 0.6 + novelty * 0.4)

    # ------------------------------------------------------------------
    # Glymphatic inhibition — tonic NE blocks ISF clearance
    # ------------------------------------------------------------------
    def _glymphatic_inhibition(self, tonic: float, sleep_wake: str) -> float:
        """Xie 2013: high NE during wake constricts interstitial space and
        blocks glymphatic flow. NREM = NE drops, glymphatic flow opens.
        """
        if sleep_wake == "NREM":
            return tonic * 0.30  # reduced restriction during NREM
        return min(1.0, tonic * 0.85 + 0.10)

    # ------------------------------------------------------------------
    # Mode classifier
    # ------------------------------------------------------------------
    def _classify_mode(self, tonic: float, phasic: float,
                        sleep_wake: str, hyper_streak: int) -> str:
        """Classify current LC operating mode.

        Hyperaroused requires sustained high tonic (anti-thrashing). REM-
        silent is the cardinal phasic-REM signature. Phasic dominant when
        burst > 0.30. Otherwise tonic or quiet.
        """
        if sleep_wake == "REM" and tonic < self.REM_SILENT_THRESHOLD:
            return "rem_silent"
        if hyper_streak > 8 and tonic > self.HYPER_THRESHOLD:
            return "hyperaroused"
        if phasic > 0.30:
            return "phasic"
        if tonic > 0.40:
            return "tonic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick — main per-step computation
    # ==================================================================
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))
        phasic_active = bool(arousal_data.get("phasic_burst_active", False))

        sal = prior.get("PrioritizedSalienceProxy", {})
        salience = float(sal.get("salience_strength", 0.0))
        novelty = float(sal.get("novelty_signal", 0.0))

        valence_data = prior.get("ValenceTagger", {})
        valence = float(valence_data.get("valence_intensity", 0.0))

        crh_data = prior.get("CRHStressDispatcher", {})
        crh = float(crh_data.get("crh_release", 0.0))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_wake = swff.get("sleep_wake_state", "WAKE")

        vlpo = prior.get("VentrolateralPreoptic", {})
        vlpo_inhibition = float(vlpo.get("gaba_galanin_release", 0.0))

        # --- Tonic firing ---
        tonic_target = self._tonic_target(arousal, crh, valence,
                                          vlpo_inhibition, sleep_wake)
        prev_tonic = float(self.state.get("lc_tonic_firing", self.BASELINE))
        new_tonic = self._smooth(prev_tonic, tonic_target)

        # --- Phasic burst ---
        prev_phasic = float(self.state.get("lc_phasic_burst", 0.0))
        new_phasic = self._phasic_target(salience, novelty, new_tonic,
                                         prev_phasic, phasic_active)

        # --- Pupil dilation (lagged) ---
        prev_pupil = float(self.state.get("pupil_dilation_proxy", 0.30))
        new_pupil = self._pupil_proxy(prev_pupil, new_tonic, new_phasic)

        # --- Cortical arousal broadcast ---
        cortical = self._cortical_arousal(new_tonic, new_phasic)

        # --- Consolidation gate ---
        consolidation = self._consolidation_gate(new_phasic, new_tonic, valence)

        # --- P3a ERP amplitude ---
        p3a = self._p3a_amplitude(new_phasic, novelty)

        # --- Glymphatic inhibition ---
        glymphatic = self._glymphatic_inhibition(new_tonic, sleep_wake)

        # --- Hyper-tonic streak tracking ---
        prev_streak = int(self.state.get("hypertonic_streak", 0))
        if new_tonic > self.HYPER_THRESHOLD and new_phasic < 0.15:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)

        # --- Mode classification ---
        mode = self._classify_mode(new_tonic, new_phasic, sleep_wake, streak)

        # --- Aggregate NE output ---
        ne_total = min(1.0, new_tonic * 0.6 + new_phasic * 0.4)

        # --- Recent phasic history (for downstream consolidation) ---
        recent = list(self.state.get("recent_phasic", []))
        recent.append(round(new_phasic, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["lc_tonic_firing"] = round(new_tonic, 4)
        self.state["lc_phasic_burst"] = round(new_phasic, 4)
        self.state["lc_mode"] = mode
        self.state["pupil_dilation_proxy"] = round(new_pupil, 4)
        self.state["cortical_arousal_drive"] = round(cortical, 4)
        self.state["consolidation_gate"] = round(consolidation, 4)
        self.state["p3a_amplitude"] = round(p3a, 4)
        self.state["glymphatic_inhibition"] = round(glymphatic, 4)
        self.state["ne_total_output"] = round(ne_total, 4)
        self.state["hypertonic_streak"] = streak
        self.state["recent_phasic"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "lc_tonic_firing": round(new_tonic, 4),
            "lc_phasic_burst": round(new_phasic, 4),
            "lc_mode": mode,
            "pupil_dilation_proxy": round(new_pupil, 4),
            "cortical_arousal_drive": round(cortical, 4),
            "consolidation_gate": round(consolidation, 4),
            "p3a_amplitude": round(p3a, 4),
            "glymphatic_inhibition": round(glymphatic, 4),
            "ne_total_output": round(ne_total, 4),
        }
