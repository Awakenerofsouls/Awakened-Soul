"""
PedunculopontineCholinergic — Pedunculopontine Tegmental Nucleus / Mesopontine
                              Cholinergic + Glutamatergic + MLR Locomotor Hub

NEURAL SUBSTRATE
================
The pedunculopontine tegmental nucleus (PPN, also PPT) sits at the pontine-
midbrain junction in the brainstem reticular formation, surrounding the
superior cerebellar peduncle. PPN is anatomically and functionally heterogen-
eous, comprising three distinct neurochemical populations that have separate
projection targets and behavioral effects:

- **Cholinergic neurons** (~40% of PPN, Ch5 group) — project broadly to
  thalamus (intralaminar + reticular nucleus), basal forebrain, basal
  ganglia (striatum, GPi, STN), substantia nigra compacta, and ventral
  tegmental area. Wake-active and REM-active firing pattern.
- **Glutamatergic neurons** (~35-40%) — project to mesencephalic locomotor
  region targets, reticulospinal premotor, and SNc dopamine neurons.
  Wake-active selective firing.
- **GABAergic neurons** (~20-25%) — local inhibitory interneurons + some
  long-range projections; gate state transitions.

PPN is the canonical mesencephalic locomotor region (MLR) — the brainstem
locomotor command center identified by Skinner (1990) and refined by
Roseberry (2016) at cell-type resolution. PPN glutamatergic neurons encode
locomotor state and speed bidirectionally and are selectively innervated by
basal ganglia direct (excitation) and indirect (suppression) pathways.

Beyond locomotion, PPN cholinergic→thalamus projections modulate thalamo-
cortical relay-cell firing mode (tonic vs burst) — a major source of
ascending arousal, distinct from but complementary to LC noradrenergic and
basal forebrain cholinergic systems. PPN cholinergic→VTA facilitates burst
firing in dopamine neurons, coupling REM activation to mesolimbic activation.

Clinical: PPN degeneration is a hallmark of Parkinson's disease, contribut-
ing to gait freezing and postural instability (the axial-symptom cluster
unresponsive to L-DOPA). Low-frequency PPN deep brain stimulation has been
trialed for L-DOPA-resistant gait dysfunction (Mazzone 2005). PPN cell loss
is also documented in progressive supranuclear palsy.

In Nova's substrate this provides the brainstem locomotor command + ascend-
ing thalamic arousal modulator, distinct from the more dorsal mesopontine
cholinergic wake substrate (MesopontineCholinergicWake) and from the
laterodorsal tegmental REM/PGO substrate (LaterodorsalTegmentalNucleus).

KEY FINDINGS
============
1. PPN comprises three distinct neurochemical populations with separable
   roles in sleep, arousal, and locomotion: cholinergic (REM + wake),
   glutamatergic (wake-locomotor), GABAergic (gate transitions) —
   [Mena-Segovia 2017, Neuron 94:7]
2. PPN glutamatergic MLR neurons encode locomotor speed bidirectionally;
   cell-type-specific opto activation drives gait initiation in mice;
   basal ganglia direct/indirect pathways selectively excite/suppress
   them — [Roseberry 2016, Cell 164:526, PMID 26824660]
3. PPN cholinergic neurons modulate thalamocortical relay-cell firing
   mode (tonic vs burst) — major source of ascending arousal during
   wake + REM — [Steriade 1990, Brain Res Rev 15:97]
4. PPN cholinergic + glutamatergic + GABAergic populations have
   dissociable effects on sleep architecture; selective optogenetic
   activation of glutamatergic increases wake, GABAergic increases
   NREM, cholinergic biases REM — [Kroeger 2017, J Neurosci 37:1352,
   PMC5296799]
5. PPN low-frequency (10-25 Hz) deep brain stimulation reduces
   L-DOPA-resistant gait freezing + postural instability in Parkinson's
   disease — [Mazzone 2005, Neuroreport 16:1877]

INPUTS (from prior_results)
============================
- BasalGangliaDirectIndirect.gpi_inhibition (or proxy: GPi.inhibitory_drive)
- CuneiformLocomotorRegion.cnf_drive
- LaterodorsalTegmentalNucleus.ldt_cholinergic_drive
- ArousalRegulator.tonic_level
- SleepWakeFlipFlop.sleep_wake_state
- LocomotionProxy.locomotion_demand (intent)
- VentralTegmentalDopamine.dopamine_burst_signal (feedback)

OUTPUTS (to brain_runner enrichment)
=====================================
- ppn_cholinergic_drive (0-1): Ch5 cholinergic output
- ppn_glutamate_drive (0-1): MLR glutamatergic locomotor command
- ppn_gaba_drive (0-1): local + projection GABAergic gate
- thalamic_activation_signal (0-1): cholinergic to thalamic relay-mode shift
- gait_initiation_command (0-1): glutamatergic→reticulospinal locomotor cmd
- gait_speed_signal (0-1): proportional locomotor speed encoding
- vta_burst_facilitation (0-1): cholinergic→VTA DA burst gain
- ppn_state (str): "wake_locomotor" | "rem_active" | "freeze" |
  "wake_quiet" | "quiet"

brain_runner enrichment:
    ppn = all_results.get("PedunculopontineCholinergic", {})
    if ppn:
        enrichments["brain_ppn_chol"] = ppn.get("ppn_cholinergic_drive", 0.20)
        enrichments["brain_ppn_glu"] = ppn.get("ppn_glutamate_drive", 0.15)
        enrichments["brain_gait_command"] = ppn.get("gait_initiation_command", 0.0)
        enrichments["brain_gait_speed"] = ppn.get("gait_speed_signal", 0.0)
        enrichments["brain_thalamic_activation"] = ppn.get("thalamic_activation_signal", 0.20)
        enrichments["brain_ppn_state"] = ppn.get("ppn_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class PedunculopontineCholinergic(BrainMechanism):
    """PPN — three-population mesopontine hub (cholinergic + glutamate + GABA)."""

    BASELINE_CHOL = 0.20
    BASELINE_GLU = 0.15
    BASELINE_GABA = 0.20
    SMOOTH = 0.25
    GPI_FREEZE_THRESHOLD = 0.65   # GPi inhibition above this → gait freezing
    LOCOMOTOR_THRESHOLD = 0.30    # Glutamate above this → gait initiation

    def __init__(self):
        super().__init__(
            name="PedunculopontineCholinergic",
            human_analog="Pedunculopontine tegmental nucleus (MLR + Ch5)",
            layer="foundational",
        )
        self.state.setdefault("ppn_cholinergic_drive", self.BASELINE_CHOL)
        self.state.setdefault("ppn_glutamate_drive", self.BASELINE_GLU)
        self.state.setdefault("ppn_gaba_drive", self.BASELINE_GABA)
        self.state.setdefault("thalamic_activation_signal", self.BASELINE_CHOL)
        self.state.setdefault("gait_initiation_command", 0.0)
        self.state.setdefault("gait_speed_signal", 0.0)
        self.state.setdefault("vta_burst_facilitation", 0.0)
        self.state.setdefault("ppn_state", "quiet")
        self.state.setdefault("freeze_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # Cholinergic — wake + REM active (Mena-Segovia 2017)
    # ------------------------------------------------------------------
    def _cholinergic_target(self, sleep_wake: str, arousal: float,
                              ldt: float, gpi: float) -> float:
        """Ch5 cholinergic firing — wake- and REM-active.

        Suppressed by NREM, by strong basal ganglia GPi inhibition (PD analog),
        and amplified by LDT (mesopontine cross-coupling).
        """
        target = self.BASELINE_CHOL + max(0.0, arousal - 0.30) * 0.45
        target += ldt * 0.20

        if sleep_wake == "REM":
            target = max(target, 0.40)  # REM-active baseline
        elif sleep_wake == "NREM":
            target *= 0.40
        elif sleep_wake == "WAKE":
            target += 0.10

        target -= max(0.0, gpi - 0.30) * 0.40
        return max(0.0, min(1.0, target))

    # ------------------------------------------------------------------
    # Glutamatergic — wake-active locomotor command (Roseberry 2016)
    # ------------------------------------------------------------------
    def _glutamate_target(self, sleep_wake: str, locomotor_demand: float,
                            cnf: float, gpi: float, arousal: float) -> float:
        """MLR glutamatergic firing — wake-active, locomotor-encoding.

        Drives gait initiation. Speed-encoding: firing rate proportional to
        locomotor speed. Suppressed by GPi inhibition (parkinsonian gait
        freezing), gated by CnF drive (parallel MLR).
        """
        if sleep_wake in ("REM", "NREM"):
            return self.BASELINE_GLU * 0.5  # Sleep — glutamate near silent

        target = self.BASELINE_GLU + locomotor_demand * 0.55
        target += cnf * 0.30
        target += max(0.0, arousal - 0.40) * 0.15

        # Direct-pathway-style facilitation removed by GPi inhibition
        target -= max(0.0, gpi - 0.20) * 0.55
        # Severe GPi inhibition = parkinsonian freeze (hard cap)
        if gpi > 0.65:
            target = min(target, 0.25)
        return max(0.0, min(1.0, target))

    # ------------------------------------------------------------------
    # GABAergic — local + projection inhibitory gate
    # ------------------------------------------------------------------
    def _gaba_target(self, sleep_wake: str, gpi: float) -> float:
        """GABAergic local + projection — suppresses REM-on cholinergic during
        wake-locomotor states, biases NREM during sleep."""
        if sleep_wake == "NREM":
            return self.BASELINE_GABA + 0.30  # NREM-on gating
        if sleep_wake == "REM":
            return self.BASELINE_GABA * 0.5
        return self.BASELINE_GABA + gpi * 0.30

    # ------------------------------------------------------------------
    # Thalamic activation — cholinergic→thalamus relay-mode shift
    # ------------------------------------------------------------------
    def _thalamic_activation(self, cholinergic: float, gaba: float) -> float:
        """Steriade 1990: cholinergic→thalamic-relay shift from burst→tonic
        mode enables active cortical states. GABAergic locally suppresses
        cholinergic output.
        """
        return min(1.0, max(0.0, cholinergic * 0.85 - gaba * 0.20))

    # ------------------------------------------------------------------
    # Gait initiation — glutamate exceeding threshold drives reticulospinal
    # ------------------------------------------------------------------
    def _gait_initiation(self, glutamate: float, gpi: float) -> float:
        """Roseberry 2016: glutamatergic firing > threshold → gait command.
        Strong GPi inhibition produces parkinsonian freeze (suppresses
        gait command despite locomotor demand)."""
        if gpi > self.GPI_FREEZE_THRESHOLD:
            return 0.0  # Freeze — gait command blocked
        if glutamate < self.LOCOMOTOR_THRESHOLD:
            return 0.0
        return min(1.0, (glutamate - self.LOCOMOTOR_THRESHOLD) * 1.6)

    # ------------------------------------------------------------------
    # Gait speed encoding — proportional firing rate (Roseberry 2016)
    # ------------------------------------------------------------------
    def _gait_speed(self, glutamate: float, gait_command: float) -> float:
        """MLR glutamatergic firing rate encodes locomotor speed."""
        if gait_command < 0.10:
            return 0.0
        return min(1.0, glutamate * 0.8 + gait_command * 0.2)

    # ------------------------------------------------------------------
    # VTA dopamine burst facilitation (cholinergic→VTA)
    # ------------------------------------------------------------------
    def _vta_facilitation(self, cholinergic: float, sleep_wake: str) -> float:
        """PPN cholinergic→VTA promotes DA burst firing during wake + REM."""
        if sleep_wake == "NREM":
            return cholinergic * 0.20
        return min(1.0, cholinergic * 0.65)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, cholinergic: float, glutamate: float,
                          gait_cmd: float, gpi: float, sleep_wake: str,
                          freeze_streak: int) -> str:
        """Classify PPN operating mode."""
        if gpi > self.GPI_FREEZE_THRESHOLD and freeze_streak > 5:
            return "freeze"
        if sleep_wake == "REM" and cholinergic > 0.35:
            return "rem_active"
        if gait_cmd > 0.30:
            return "wake_locomotor"
        if cholinergic > 0.30 or glutamate > 0.20:
            return "wake_quiet"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick — main per-step computation
    # ==================================================================
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Basal ganglia GPi inhibition — proxy or direct
        bg = prior.get("BasalGangliaDirectIndirect", {})
        gpi = float(bg.get("gpi_inhibition", 0.0))
        if gpi == 0.0:
            gpi_proxy = prior.get("GPi", {})
            gpi = float(gpi_proxy.get("inhibitory_drive", 0.0))

        cnf_data = prior.get("CuneiformLocomotorRegion", {})
        cnf = float(cnf_data.get("cnf_drive", 0.0))

        ldt_data = prior.get("LaterodorsalTegmentalNucleus", {})
        ldt = float(ldt_data.get("ldt_cholinergic_drive", 0.0))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_wake = swff.get("sleep_wake_state", "WAKE")

        loco = prior.get("LocomotionProxy", {})
        locomotor_demand = float(loco.get("locomotion_demand",
                                  loco.get("locomotion_speed", 0.0)))

        # --- Cholinergic ---
        chol_target = self._cholinergic_target(sleep_wake, arousal, ldt, gpi)
        prev_chol = float(self.state.get("ppn_cholinergic_drive",
                                          self.BASELINE_CHOL))
        new_chol = self._smooth(prev_chol, chol_target)

        # --- Glutamatergic ---
        glu_target = self._glutamate_target(sleep_wake, locomotor_demand,
                                            cnf, gpi, arousal)
        prev_glu = float(self.state.get("ppn_glutamate_drive",
                                         self.BASELINE_GLU))
        new_glu = self._smooth(prev_glu, glu_target)

        # --- GABAergic ---
        gaba_target = self._gaba_target(sleep_wake, gpi)
        prev_gaba = float(self.state.get("ppn_gaba_drive", self.BASELINE_GABA))
        new_gaba = self._smooth(prev_gaba, gaba_target)

        # --- Outputs ---
        thalamic = self._thalamic_activation(new_chol, new_gaba)
        gait_cmd = self._gait_initiation(new_glu, gpi)
        gait_speed = self._gait_speed(new_glu, gait_cmd)
        vta_facil = self._vta_facilitation(new_chol, sleep_wake)

        # --- Freeze streak tracking ---
        prev_freeze_streak = int(self.state.get("freeze_streak", 0))
        if gpi > self.GPI_FREEZE_THRESHOLD and locomotor_demand > 0.10:
            freeze_streak = prev_freeze_streak + 1
        else:
            freeze_streak = max(0, prev_freeze_streak - 2)

        state = self._classify_state(new_chol, new_glu, gait_cmd, gpi,
                                      sleep_wake, freeze_streak)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ppn_cholinergic_drive"] = round(new_chol, 4)
        self.state["ppn_glutamate_drive"] = round(new_glu, 4)
        self.state["ppn_gaba_drive"] = round(new_gaba, 4)
        self.state["thalamic_activation_signal"] = round(thalamic, 4)
        self.state["gait_initiation_command"] = round(gait_cmd, 4)
        self.state["gait_speed_signal"] = round(gait_speed, 4)
        self.state["vta_burst_facilitation"] = round(vta_facil, 4)
        self.state["ppn_state"] = state
        self.state["freeze_streak"] = freeze_streak
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ppn_cholinergic_drive": round(new_chol, 4),
            "ppn_glutamate_drive": round(new_glu, 4),
            "ppn_gaba_drive": round(new_gaba, 4),
            "thalamic_activation_signal": round(thalamic, 4),
            "gait_initiation_command": round(gait_cmd, 4),
            "gait_speed_signal": round(gait_speed, 4),
            "vta_burst_facilitation": round(vta_facil, 4),
            "ppn_state": state,
        }
