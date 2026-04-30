"""
DorsomedialHypothalamus — DMH / Stress-Cardiovascular + Thermogenic Premotor

NEURAL SUBSTRATE
================
Compact nucleus in dorsal hypothalamus medial to fornix. Receives convergent
input from circadian (SCN→subparaventricular zone→DMH), preoptic
(MnPO→DMH), stress (PVN→DMH), amygdala (CeA→DMH) systems.

Outputs (glutamatergic + GABAergic):
- Raphe pallidus / parapyramidal area — premotor for BAT thermogenesis +
  cardiac sympathetic. THE primary brainstem premotor relay for stress-
  cardiovascular coupling.
- PVN — autonomic feedback, anticipatory food behavior
- Spinal IML (intermediolateral cell column) — direct sympathetic premotor
- VLPO + sleep-active areas — circadian arousal coordination

Critical for:
- Stress-induced cardiovascular activation (HR + BP rise during emotional
  stress) — DMH disinhibition by amygdala
- Cold-induced BAT thermogenesis — DMH→raphe pallidus drives BAT
- Circadian rhythms in body temperature, heart rate, corticosterone
- Anticipatory food activity (food-entrained oscillator candidate)

KEY FINDINGS
============
1. DMH→raphe pallidus glutamatergic projection drives BAT thermogenesis
   + cardiac sympathetic outflow — [Nakamura 2011, J Neurosci 31:11954,
   doi:10.1523/JNEUROSCI.2370-11.2011]
2. DMH lesion abolishes circadian rhythms in body temp + activity +
   corticosterone — [Chou 2003, J Neurosci 23:10691, PMC6741000]
3. DMH GABAergic neurons gate stress-induced cardiovascular response;
   amygdala disinhibition increases HR — [Fontes 2011, J Physiol 589:163,
   PMID 21115646]
4. SCN→subparaventricular zone→DMH is the canonical circadian relay
   path — [Saper 2005, Neuron 36:1069, PMID 12495622]
5. DMH drives food-anticipatory activity (food-entrained oscillator
   candidate) — [Acosta-Galvan 2011, Proc Natl Acad Sci 108:5813,
   doi:10.1073/pnas.1015551108]

INPUTS
======
- SuprachiasmaticOutput.circadian_drive (or CircadianTimer.circadian_phase)
- MedianPreopticNucleus.mnpo_warm_drive
- ParaventricularAutonomic.pvn_stress_drive
- CentralNucleusFearRouter.cea_drive
- FeedingStressIntegrator.fsi_drive

OUTPUTS
=======
- dmh_drive (0-1)
- raphe_pallidus_command (0-1) — premotor for BAT + cardiac
- iml_sympathetic_drive (0-1) — direct spinal sympathetic
- bat_thermogenic_command (0-1)
- cardiac_sympathetic_amplifier (0-1)
- dmh_state (str): "stress_cardiovascular" | "thermogenic" |
  "circadian_drive" | "food_anticipation" | "quiet"

brain_runner enrichment:
    dmh = all_results.get("DorsomedialHypothalamus", {})
    if dmh:
        enrichments["brain_dmh_drive"] = dmh.get("dmh_drive", 0.10)
        enrichments["brain_raphe_pallidus_cmd"] = dmh.get("raphe_pallidus_command", 0.0)
        enrichments["brain_bat_thermogenic"] = dmh.get("bat_thermogenic_command", 0.0)
        enrichments["brain_cardiac_sympathetic"] = dmh.get("cardiac_sympathetic_amplifier", 0.0)
        enrichments["brain_dmh_state"] = dmh.get("dmh_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class DorsomedialHypothalamus(BrainMechanism):
    """DMH — stress-cardiovascular + thermogenic premotor."""

    BASELINE = 0.15
    SMOOTH = 0.20
    STRESS_THRESHOLD = 0.40
    COLD_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="DorsomedialHypothalamus",
            human_analog="Dorsomedial hypothalamus (stress-cardio + BAT premotor)",
            layer="foundational",
        )
        self.state.setdefault("dmh_drive", self.BASELINE)
        self.state.setdefault("raphe_pallidus_command", 0.0)
        self.state.setdefault("iml_sympathetic_drive", 0.0)
        self.state.setdefault("bat_thermogenic_command", 0.0)
        self.state.setdefault("cardiac_sympathetic_amplifier", 0.0)
        self.state.setdefault("dmh_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # DMH drive — convergence of circadian + stress + thermal
    # ------------------------------------------------------------------
    def _dmh_target(self, circadian: float, mnpo_warm: float,
                      pvn_stress: float, cea: float, fsi: float) -> float:
        """DMH firing — multimodal convergence.

        Cold stress (low MnPO warm) drives thermogenic firing.
        Stress (PVN + CeA) drives cardiovascular firing.
        Circadian biases overall amplitude.
        """
        target = self.BASELINE
        # Cold-detection: warm-sensitive low → DMH fires for thermogenesis
        cold_signal = max(0.0, 0.40 - mnpo_warm) * 0.55
        target += cold_signal
        # Stress drive
        target += pvn_stress * 0.40
        target += cea * 0.30
        # Feeding-stress
        target += fsi * 0.15
        # Circadian — modest baseline modulation
        target += max(0.0, circadian - 0.50) * 0.15
        return min(1.0, max(0.0, target))

    # ------------------------------------------------------------------
    # Raphe pallidus command (Nakamura 2011)
    # ------------------------------------------------------------------
    def _raphe_pallidus(self, dmh_drive: float, cold_signal: float,
                          stress: float) -> float:
        """DMH→raphe pallidus — premotor for BAT + cardiac sympathetic."""
        return min(1.0, dmh_drive * 0.5 + cold_signal * 0.3 + stress * 0.3)

    # ------------------------------------------------------------------
    # IML sympathetic drive (direct spinal premotor)
    # ------------------------------------------------------------------
    def _iml(self, dmh_drive: float, stress: float) -> float:
        """Direct DMH → spinal IML sympathetic premotor command."""
        return min(1.0, dmh_drive * 0.5 + stress * 0.4)

    # ------------------------------------------------------------------
    # BAT thermogenic command (cold-driven only)
    # ------------------------------------------------------------------
    def _bat_command(self, raphe_pallidus: float, mnpo_warm: float,
                      circadian: float) -> float:
        """BAT thermogenesis active when raphe pallidus driven by cold,
        gated by circadian phase (BAT more active during awake phase).
        """
        if mnpo_warm > 0.50:
            return 0.0  # Warm — no BAT activation
        return min(1.0, raphe_pallidus * 0.7 + circadian * 0.15)

    # ------------------------------------------------------------------
    # Cardiac sympathetic amplifier (Fontes 2011)
    # ------------------------------------------------------------------
    def _cardiac_amplifier(self, dmh_drive: float, cea: float,
                              pvn_stress: float) -> float:
        """Cardiac sympathetic amplifier — engaged by emotional stress
        when CeA disinhibits DMH GABAergic gate."""
        if pvn_stress + cea < 0.30:
            return 0.0
        return min(1.0, dmh_drive * 0.5 + cea * 0.4 + pvn_stress * 0.3)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, stress_combined: float, mnpo_warm: float,
                          dmh_drive: float, fsi: float, circadian: float) -> str:
        """Classify DMH operating mode."""
        if stress_combined > self.STRESS_THRESHOLD and dmh_drive > 0.40:
            return "stress_cardiovascular"
        if mnpo_warm < self.COLD_THRESHOLD and dmh_drive > 0.30:
            return "thermogenic"
        if fsi > 0.40:
            return "food_anticipation"
        if dmh_drive > 0.30 and circadian > 0.60:
            return "circadian_drive"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick
    # ==================================================================
    def _circadian_phase_modulator(self, phase: float) -> float:
        """SCN→subPVN→DMH circadian phase — DMH amplitude varies
        across phase (Chou 2003 lesion abolishes circadian rhythms in
        body temp + activity + corticosterone).
        """
        import math
        return 0.5 + 0.5 * math.cos(2 * math.pi * (phase - 0.25))

    def _stress_amygdala_disinhibition(self, cea: float, gaba_baseline: float) -> float:
        """Amygdala disinhibits DMH GABAergic gate (Fontes 2011) — when CeA
        active, GABAergic DMH suppression lifts, allowing cardiovascular
        response to emerge.
        """
        if cea < 0.20:
            return gaba_baseline
        return max(0.0, gaba_baseline - cea * 0.55)

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "drive": self.state.get("dmh_drive", 0.0),
            "raphe_pallidus": self.state.get("raphe_pallidus_command", 0.0),
            "bat": self.state.get("bat_thermogenic_command", 0.0),
            "cardiac_amp": self.state.get("cardiac_sympathetic_amplifier", 0.0),
            "state": self.state.get("dmh_state", "quiet"),
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        scn = prior.get("SuprachiasmaticOutput", {})
        if not scn:
            scn = prior.get("CircadianTimer", {})
        circadian = float(scn.get("circadian_drive",
                            scn.get("circadian_phase", 0.5)))

        mnpo_data = prior.get("MedianPreopticNucleus", {})
        mnpo_warm = float(mnpo_data.get("mnpo_warm_drive", 0.30))

        pvn_data = prior.get("ParaventricularAutonomic", {})
        pvn_stress = float(pvn_data.get("pvn_stress_drive", 0.0))

        cea_data = prior.get("CentralNucleusFearRouter", {})
        cea = float(cea_data.get("cea_drive", 0.0))

        fsi_data = prior.get("FeedingStressIntegrator", {})
        fsi = float(fsi_data.get("fsi_drive", 0.0))

        # --- DMH drive ---
        dmh_target = self._dmh_target(circadian, mnpo_warm, pvn_stress, cea, fsi)
        prev_drive = float(self.state.get("dmh_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, dmh_target)

        # --- Outputs ---
        cold_signal = max(0.0, 0.40 - mnpo_warm)
        stress_combined = pvn_stress + cea * 0.7

        raphe_pallidus = self._raphe_pallidus(new_drive, cold_signal, stress_combined)
        iml = self._iml(new_drive, stress_combined)
        bat_cmd = self._bat_command(raphe_pallidus, mnpo_warm, circadian)
        cardiac_amp = self._cardiac_amplifier(new_drive, cea, pvn_stress)

        state = self._classify_state(stress_combined, mnpo_warm, new_drive,
                                      fsi, circadian)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["dmh_drive"] = round(new_drive, 4)
        self.state["raphe_pallidus_command"] = round(raphe_pallidus, 4)
        self.state["iml_sympathetic_drive"] = round(iml, 4)
        self.state["bat_thermogenic_command"] = round(bat_cmd, 4)
        self.state["cardiac_sympathetic_amplifier"] = round(cardiac_amp, 4)
        self.state["dmh_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "dmh_drive": round(new_drive, 4),
            "raphe_pallidus_command": round(raphe_pallidus, 4),
            "iml_sympathetic_drive": round(iml, 4),
            "bat_thermogenic_command": round(bat_cmd, 4),
            "cardiac_sympathetic_amplifier": round(cardiac_amp, 4),
            "dmh_state": state,
        }
