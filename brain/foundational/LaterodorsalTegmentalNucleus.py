"""
LaterodorsalTegmentalNucleus — LDT / Mesopontine Cholinergic REM-on Generator

NEURAL SUBSTRATE
================
The laterodorsal tegmental nucleus (LDT) sits in the dorsolateral pontine
tegmentum, lateral to the central gray and immediately rostral to the locus
coeruleus. Anatomically distinct from but functionally coupled with the
pedunculopontine tegmental nucleus (PPN) — together they form the
mesopontine cholinergic REM-generating system (the "Ch5/Ch6" cholinergic
groups in Mesulam's classification).

LDT cholinergic neurons (~30-40% of LDT cells) project to:
  - Thalamus — intralaminar nuclei + reticular nucleus + relay nuclei.
    Drives the wake/REM thalamic activation that produces cortical
    desynchronization (low-voltage fast EEG).
  - Ventral tegmental area (VTA) — facilitates dopaminergic neuron burst
    firing during REM and salience events. Major contributor to REM-DA
    coupling.
  - Basal forebrain — modulates BF cholinergic activity.
  - Lateral hypothalamus / orexin neurons — feedback loop.
  - Locus coeruleus — modulates LC firing mode.

LDT also contains glutamatergic (~30%) and GABAergic (~30%) populations,
each with distinct sleep-wake firing profiles. Cholinergic LDT neurons
fire selectively during wake AND REM (REM-on). The transition from wake
to NREM silences LDT cholinergic; the transition from NREM to REM
re-activates it. Phasic cholinergic bursts during REM generate
ponto-geniculo-occipital (PGO) waves — the characteristic phasic events
of REM sleep that propagate from pontine generators through lateral
geniculate to occipital cortex.

Co-release: ACh + glutamate + nitric oxide. Some LDT cholinergic neurons
also express substance P or galanin.

Distinct from PPN: more dorsal, projects more heavily to thalamus + VTA
than to MLR (mesencephalic locomotor region). PPN is the primary locomotor
command nucleus; LDT is the primary REM/PGO + VTA-DA modulator. Both
contribute to thalamic activation but via partly separate circuits.

Clinical: LDT degeneration contributes to REM-sleep behavior disorder
(RBD) — when LDT cholinergic activity becomes desynchronized with the
LC noradrenergic atonia signal, REM atonia fails and patients enact
their dreams. RBD is a strong prodromal marker for Parkinson's disease.

In {{AGENT_NAME}}'s substrate this provides the dedicated REM/PGO substrate plus
the cholinergic→VTA pathway, complementing the broader mesopontine wake
substrate (MesopontineCholinergicWake) and the locomotor-focused PPN.

KEY FINDINGS
============
1. LDT cholinergic neurons fire selectively during wake + REM, with
   phasic burst firing time-locked to PGO waves; silenced during NREM —
   [Datta 2002, J Neurophysiol 87:1986]
2. PPT/LDT cholinergic neurons are necessary + sufficient for PGO wave
   generation — pharmacological + lesion + optogenetic convergence —
   [Datta 1997, J Neurophysiol 77:2975, PMID 9187490]
3. Optogenetic stimulation of PPT/LDT cholinergic neurons during NREM
   shifts EEG into REM-like activation pattern — direct causal evidence
   that cholinergic mesopontine drive is sufficient to induce REM —
   [Van Dort 2015, Proc Natl Acad Sci 112:584, PMC4291655]
4. LDT-thalamic cholinergic projection sets thalamocortical relay-cell
   firing mode (tonic vs burst) — major source of ascending arousal
   during REM and active wake — [Steriade 1991, Trends Neurosci 14:480]
5. LDT cholinergic projection to VTA facilitates dopaminergic burst
   firing — couples REM activation to mesolimbic dopamine release —
   [Lodge 2006, J Neurosci 26:5453, PMID 16707477]

INPUTS (from prior_results)
============================
- SleepWakeFlipFlop.sleep_wake_state, .rem_pattern_active
- LocusSubcoeruleusREM.subC_drive
- PedunculopontineCholinergic.ppn_cholinergic_drive
- MedullaryRapheMagnus.raphe_5HT_drive (REM-off inhibition)
- LocusCoeruleusCore.lc_tonic_firing (REM-off counterforce)
- ArousalRegulator.tonic_level
- OrexinWakePromoter.orexin_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- ldt_cholinergic_drive (0-1): cholinergic firing rate
- ldt_glutamate_drive (0-1): glutamatergic component
- ldt_gaba_drive (0-1): GABAergic component
- pgo_wave_active (bool): phasic PGO wave currently firing
- pgo_amplitude (0-1): PGO wave amplitude when active
- vta_burst_facilitation (0-1): cholinergic→VTA gain on DA burst firing
- thalamic_burst_to_tonic_shift (0-1): cholinergic-driven relay-mode shift
- rem_pgo_coupling (0-1): coupling between REM state and PGO firing
- ldt_state (str): "rem_burst" | "wake_tonic" | "nrem_silent" |
  "rem_pgo_storm" | "quiet"

brain_runner enrichment:
    ldt = all_results.get("LaterodorsalTegmentalNucleus", {})
    if ldt:
        enrichments["brain_ldt_chol"] = ldt.get("ldt_cholinergic_drive", 0.20)
        enrichments["brain_pgo_active"] = ldt.get("pgo_wave_active", False)
        enrichments["brain_pgo_amp"] = ldt.get("pgo_amplitude", 0.0)
        enrichments["brain_vta_burst_facil"] = ldt.get("vta_burst_facilitation", 0.0)
        enrichments["brain_thalamic_shift"] = ldt.get("thalamic_burst_to_tonic_shift", 0.0)
        enrichments["brain_ldt_state"] = ldt.get("ldt_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class LaterodorsalTegmentalNucleus(BrainMechanism):
    """LDT — REM-on cholinergic + PGO wave generator + VTA-DA modulator."""

    BASELINE_CHOL = 0.20
    BASELINE_GLU = 0.15
    BASELINE_GABA = 0.20
    SMOOTH = 0.25
    PGO_THRESHOLD = 0.40         # Cholinergic + REM threshold for PGO wave
    PGO_DECAY = 0.55             # PGO bursts decay 45% per tick
    REM_OFF_5HT_THRESHOLD = 0.45 # Above this 5HT, REM-on cells silenced

    def __init__(self):
        super().__init__(
            name="LaterodorsalTegmentalNucleus",
            human_analog="Laterodorsal tegmental nucleus (Ch6 cholinergic + PGO)",
            layer="foundational",
        )
        self.state.setdefault("ldt_cholinergic_drive", self.BASELINE_CHOL)
        self.state.setdefault("ldt_glutamate_drive", self.BASELINE_GLU)
        self.state.setdefault("ldt_gaba_drive", self.BASELINE_GABA)
        self.state.setdefault("pgo_wave_active", False)
        self.state.setdefault("pgo_amplitude", 0.0)
        self.state.setdefault("vta_burst_facilitation", 0.0)
        self.state.setdefault("thalamic_burst_to_tonic_shift", 0.0)
        self.state.setdefault("rem_pgo_coupling", 0.0)
        self.state.setdefault("ldt_state", "quiet")
        self.state.setdefault("rem_burst_streak", 0)
        self.state.setdefault("recent_pgo", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # Cholinergic — REM-selective + wake-active (Datta 2002)
    # ------------------------------------------------------------------
    def _cholinergic_target(self, sleep_wake: str, rem_active: bool,
                              subC: float, raphe_5HT: float, lc_tonic: float,
                              arousal: float) -> float:
        """LDT cholinergic firing — wake + REM active, NREM silent.

        REM-on disinhibition: high 5HT (raphe) silences cholinergic during
        wake; raphe falls during REM, releasing cholinergic burst. LC
        moderately suppresses cholinergic during high-tonic wake.
        """
        # NREM — silenced
        if sleep_wake == "NREM":
            return self.BASELINE_CHOL * 0.25

        # REM — strong cholinergic if 5HT below threshold (canonical REM-on)
        if sleep_wake == "REM" or rem_active:
            base = 0.50 + subC * 0.30
            base -= max(0.0, raphe_5HT - 0.20) * 0.50
            base += max(0.0, arousal - 0.30) * 0.10
            return max(0.0, min(1.0, base))

        # Wake — moderate cholinergic, inversely modulated by 5HT + LC tonic
        target = self.BASELINE_CHOL + max(0.0, arousal - 0.30) * 0.40
        target -= max(0.0, raphe_5HT - 0.30) * 0.30
        target -= max(0.0, lc_tonic - 0.65) * 0.20
        return max(0.0, min(1.0, target))

    # ------------------------------------------------------------------
    # Glutamatergic — wake-active component
    # ------------------------------------------------------------------
    def _glutamate_target(self, sleep_wake: str, arousal: float,
                            orexin: float) -> float:
        """LDT glutamatergic — wake-active, supports cortical activation."""
        if sleep_wake in ("NREM", "REM"):
            return self.BASELINE_GLU * 0.5
        return min(1.0, self.BASELINE_GLU + arousal * 0.30 + orexin * 0.25)

    # ------------------------------------------------------------------
    # GABAergic — gates state transitions
    # ------------------------------------------------------------------
    def _gaba_target(self, sleep_wake: str) -> float:
        """LDT GABAergic — gates wake/REM transitions, NREM-biased."""
        if sleep_wake == "NREM":
            return self.BASELINE_GABA + 0.25
        if sleep_wake == "REM":
            return self.BASELINE_GABA * 0.5
        return self.BASELINE_GABA

    # ------------------------------------------------------------------
    # PGO wave — phasic cholinergic burst during REM
    # ------------------------------------------------------------------
    def _pgo_compute(self, cholinergic: float, rem_active: bool,
                       raphe_5HT: float, prev_pgo_amp: float,
                       prev_pgo_active: bool) -> tuple:
        """Compute PGO wave state.

        Datta 1997 / Van Dort 2015: PGO firing requires
          (a) cholinergic activity above threshold AND
          (b) reduced 5HT inhibition (REM-state).
        Amplitude decays each tick to model phasic burst dynamics.
        """
        if not rem_active or raphe_5HT > self.REM_OFF_5HT_THRESHOLD:
            # Not in REM or 5HT still high — PGO decays toward zero
            new_amp = prev_pgo_amp * self.PGO_DECAY
            return (False if new_amp < 0.10 else prev_pgo_active, new_amp)

        # In REM with low 5HT — cholinergic threshold crossing fires PGO
        if cholinergic > self.PGO_THRESHOLD:
            # Burst — amplitude scales with cholinergic above threshold
            new_amp = min(1.0, (cholinergic - self.PGO_THRESHOLD) * 1.8 + 0.40)
            return (True, new_amp)

        # In REM but cholinergic below threshold — slow decay
        new_amp = prev_pgo_amp * self.PGO_DECAY
        return (new_amp >= 0.20, new_amp)

    # ------------------------------------------------------------------
    # VTA dopamine burst facilitation (Lodge 2006)
    # ------------------------------------------------------------------
    def _vta_facilitation(self, cholinergic: float, sleep_wake: str,
                            rem_active: bool) -> float:
        """LDT cholinergic→VTA promotes DA burst firing.

        Strongest during REM (couples REM to mesolimbic activation) and
        during salience-driven phasic wake activations.
        """
        if rem_active:
            return min(1.0, cholinergic * 0.85)
        if sleep_wake == "WAKE":
            return min(1.0, cholinergic * 0.55)
        return cholinergic * 0.20

    # ------------------------------------------------------------------
    # Thalamic relay-mode shift (Steriade 1991)
    # ------------------------------------------------------------------
    def _thalamic_shift(self, cholinergic: float, gaba: float) -> float:
        """LDT cholinergic→thalamus shifts relay cells from burst to tonic
        firing — produces cortical desynchronization characteristic of wake
        + REM. GABAergic locally suppresses output.
        """
        return min(1.0, max(0.0, cholinergic * 0.85 - gaba * 0.20))

    # ------------------------------------------------------------------
    # REM-PGO coupling — measure of phase-locking
    # ------------------------------------------------------------------
    def _rem_pgo_coupling(self, rem_active: bool, pgo_amp: float,
                            recent_pgo: list) -> float:
        """Coupling between REM state and PGO firing — high when PGO bursts
        are happening during REM. Failure of coupling = REM-sleep behavior
        disorder (RBD) prodrome.
        """
        if not rem_active:
            return 0.0
        recent_pgo_avg = sum(recent_pgo[-20:]) / max(1, len(recent_pgo[-20:]))
        return min(1.0, pgo_amp * 0.6 + recent_pgo_avg * 0.4)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, cholinergic: float, sleep_wake: str,
                          rem_active: bool, pgo_active: bool,
                          rem_burst_streak: int) -> str:
        """Classify LDT operating mode."""
        if sleep_wake == "NREM" or cholinergic < 0.10:
            return "nrem_silent"
        if rem_active and pgo_active:
            if rem_burst_streak > 8:
                return "rem_pgo_storm"
            return "rem_burst"
        if sleep_wake == "WAKE" and cholinergic > 0.30:
            return "wake_tonic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick — main per-step computation
    # ==================================================================
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_wake = swff.get("sleep_wake_state", "WAKE")
        rem_active = bool(swff.get("rem_pattern_active", False))

        subC_data = prior.get("LocusSubcoeruleusREM", {})
        subC = float(subC_data.get("subC_drive", 0.0))

        raphe_data = prior.get("MedullaryRapheMagnus", {})
        raphe_5HT = float(raphe_data.get("raphe_5HT_drive",
                            raphe_data.get("serotonin_drive", 0.30)))

        lc_data = prior.get("LocusCoeruleusCore", {})
        lc_tonic = float(lc_data.get("lc_tonic_firing", 0.20))

        ppn_data = prior.get("PedunculopontineCholinergic", {})
        ppn_chol = float(ppn_data.get("ppn_cholinergic_drive", 0.0))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        orexin_data = prior.get("OrexinWakePromoter", {})
        orexin = float(orexin_data.get("orexin_drive", 0.30))

        # --- Cholinergic ---
        chol_target = self._cholinergic_target(sleep_wake, rem_active, subC,
                                                raphe_5HT, lc_tonic, arousal)
        # PPN cross-coupling — boosts LDT cholinergic during shared activation
        chol_target = min(1.0, chol_target + ppn_chol * 0.10)
        prev_chol = float(self.state.get("ldt_cholinergic_drive",
                                          self.BASELINE_CHOL))
        new_chol = self._smooth(prev_chol, chol_target)

        # --- Glutamatergic ---
        glu_target = self._glutamate_target(sleep_wake, arousal, orexin)
        prev_glu = float(self.state.get("ldt_glutamate_drive",
                                         self.BASELINE_GLU))
        new_glu = self._smooth(prev_glu, glu_target)

        # --- GABAergic ---
        gaba_target = self._gaba_target(sleep_wake)
        prev_gaba = float(self.state.get("ldt_gaba_drive", self.BASELINE_GABA))
        new_gaba = self._smooth(prev_gaba, gaba_target)

        # --- PGO wave ---
        prev_pgo_amp = float(self.state.get("pgo_amplitude", 0.0))
        prev_pgo_active = bool(self.state.get("pgo_wave_active", False))
        pgo_active, pgo_amp = self._pgo_compute(new_chol, rem_active,
                                                 raphe_5HT, prev_pgo_amp,
                                                 prev_pgo_active)

        # --- VTA burst facilitation ---
        vta_facil = self._vta_facilitation(new_chol, sleep_wake, rem_active)

        # --- Thalamic shift ---
        thalamic = self._thalamic_shift(new_chol, new_gaba)

        # --- REM-PGO coupling ---
        recent_pgo = list(self.state.get("recent_pgo", []))
        recent_pgo.append(round(pgo_amp, 4))
        if len(recent_pgo) > 60:
            recent_pgo = recent_pgo[-60:]
        coupling = self._rem_pgo_coupling(rem_active, pgo_amp, recent_pgo)

        # --- REM burst streak (PGO storm detection) ---
        prev_streak = int(self.state.get("rem_burst_streak", 0))
        if rem_active and pgo_active:
            rem_burst_streak = prev_streak + 1
        else:
            rem_burst_streak = max(0, prev_streak - 2)

        state = self._classify_state(new_chol, sleep_wake, rem_active,
                                      pgo_active, rem_burst_streak)

        self.state["ldt_cholinergic_drive"] = round(new_chol, 4)
        self.state["ldt_glutamate_drive"] = round(new_glu, 4)
        self.state["ldt_gaba_drive"] = round(new_gaba, 4)
        self.state["pgo_wave_active"] = pgo_active
        self.state["pgo_amplitude"] = round(pgo_amp, 4)
        self.state["vta_burst_facilitation"] = round(vta_facil, 4)
        self.state["thalamic_burst_to_tonic_shift"] = round(thalamic, 4)
        self.state["rem_pgo_coupling"] = round(coupling, 4)
        self.state["ldt_state"] = state
        self.state["rem_burst_streak"] = rem_burst_streak
        self.state["recent_pgo"] = recent_pgo
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ldt_cholinergic_drive": round(new_chol, 4),
            "ldt_glutamate_drive": round(new_glu, 4),
            "ldt_gaba_drive": round(new_gaba, 4),
            "pgo_wave_active": pgo_active,
            "pgo_amplitude": round(pgo_amp, 4),
            "vta_burst_facilitation": round(vta_facil, 4),
            "thalamic_burst_to_tonic_shift": round(thalamic, 4),
            "rem_pgo_coupling": round(coupling, 4),
            "ldt_state": state,
            "rem_burst_streak": rem_burst_streak,
        }
