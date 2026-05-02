"""
MedialHabenula — MHb / Cholinergic + Substance-P / Aversion-Anxiety Hub

NEURAL SUBSTRATE
================
Adjacent to but anatomically + functionally distinct from LHb. The medial
habenula (MHb) sits medial in the epithalamus along the third ventricle.
Two principal subdivisions with distinct neurochemistry:

- **Dorsal MHb** — substance-P expressing neurons projecting to lateral
  IPN. Anxiety + aversive learning role.
- **Ventral MHb** — cholinergic + glutamatergic neurons co-releasing ACh
  + glutamate to the central + medial IPN. Mediates nicotine sensitivity
  and withdrawal aversion via α5β4 nicotinic receptors.

Inputs: triangular septal nucleus + diagonal band + medial septum
glutamatergic. The septum-MHb-IPN-raphe pathway is the dorsal diencephalic
conduction system, an evolutionarily conserved aversion circuit.

Outputs: nearly exclusive projection to interpeduncular nucleus (IPN) via
fasciculus retroflexus. IPN in turn projects to dorsal raphe + median raphe
+ dorsal tegmental nucleus, modulating serotonin + REM circuits.

MHb fires tonically at low rates (~1-5 Hz) — distinct from LHb's burst
patterns. Tonic activity supports baseline aversion-axis tone.

Clinical: MHb α5 subunit knockout abolishes nicotine withdrawal aversion;
α5 polymorphisms predict heavy smoking. MHb degeneration in late-stage
Alzheimer's correlates with anxiety symptoms.

In the agent's substrate this provides the cholinergic + substance-P aversion
modulator, distinct from LHb's burst-firing anti-reward signal.

KEY FINDINGS
============
1. MHb cholinergic→IPN drives nicotine withdrawal aversion; α5 nicotinic
   subunit knockout eliminates withdrawal-induced aversion —
   [Salas 2009, J Neurosci 29:3014, PMC2695187]
2. MHb-IPN substance-P signaling regulates anxiety; selective MHb
   substance-P lesions are anxiolytic in mouse — [Yamaguchi 2013,
   Nat Commun 4:2727, doi:10.1038/ncomms3727]
3. MHb tonic firing rate ~1-5 Hz, distinct from LHb burst patterns;
   spontaneous activity drives baseline IPN tone — [Gorlich 2013,
   Proc Natl Acad Sci 110:17077, PMC3791720]
4. IPN α5β4 nicotinic receptors mediate nicotine sensitivity threshold —
   [Frahm 2011, Neuron 70:522, doi:10.1016/j.neuron.2011.04.013]
5. IPN α5 KO alters aversion-reward valence shift in nicotine-taking
   behavior — [Fowler 2011, Nature 471:597, doi:10.1038/nature09797]

INPUTS (from prior_results)
============================
- TriangularSeptal.ts_drive (or proxy SeptalProxy.septal_glutamate)
- DiagonalBandBroca.dbb_drive
- ValenceTagger.anxiety_intensity, .aversive_signal
- ArousalRegulator.tonic_level
- NicotineWithdrawalProxy.craving_signal (default 0)

OUTPUTS (to brain_runner enrichment)
=====================================
- mhb_cholinergic_drive (0-1)
- mhb_substance_p_drive (0-1)
- mhb_glutamate_drive (0-1)
- ipn_drive_command (0-1): aggregate signal to IPN
- mhb_state (str): "anxiety_active" | "withdrawal_active" |
  "tonic_baseline" | "quiet"

brain_runner enrichment:
    mhb = all_results.get("MedialHabenula", {})
    if mhb:
        enrichments["brain_mhb_chol"] = mhb.get("mhb_cholinergic_drive", 0.10)
        enrichments["brain_mhb_subP"] = mhb.get("mhb_substance_p_drive", 0.0)
        enrichments["brain_ipn_command"] = mhb.get("ipn_drive_command", 0.0)
        enrichments["brain_mhb_state"] = mhb.get("mhb_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class MedialHabenula(BrainMechanism):
    """MHb — cholinergic + substance-P aversion modulator."""

    BASELINE_TONIC = 0.10
    SMOOTH = 0.20
    ANXIETY_THRESHOLD = 0.45
    WITHDRAWAL_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="MedialHabenula_MedialHabenula",
            human_analog="Medial habenula (cholinergic + substance-P aversion)",
            layer="foundational",
        )
        self.state.setdefault("mhb_cholinergic_drive", self.BASELINE_TONIC)
        self.state.setdefault("mhb_substance_p_drive", 0.0)
        self.state.setdefault("mhb_glutamate_drive", self.BASELINE_TONIC)
        self.state.setdefault("ipn_drive_command", 0.0)
        self.state.setdefault("mhb_state", "tonic_baseline")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # Cholinergic ventral MHb — α5β4 nicotinic, withdrawal-driven (Salas 2009)
    # ------------------------------------------------------------------
    def _cholinergic_target(self, septal: float, dbb: float, craving: float,
                              arousal: float) -> float:
        """Ventral MHb cholinergic firing.

        Tonic baseline always > 0 (Gorlich 2013). Boosted by septal
        glutamate, DBB input, nicotine withdrawal craving signal.
        """
        target = self.BASELINE_TONIC + septal * 0.30 + dbb * 0.10
        target += craving * 0.45
        target += max(0.0, arousal - 0.40) * 0.10
        return min(1.0, max(0.0, target))

    # ------------------------------------------------------------------
    # Dorsal MHb substance-P — anxiety-driven (Yamaguchi 2013)
    # ------------------------------------------------------------------
    def _substance_p_target(self, anxiety: float, aversive: float,
                              septal: float, craving: float) -> float:
        """Dorsal MHb substance-P firing.

        Driven by anxiety + aversive valence + septal input.
        Withdrawal also recruits substance-P pathway.
        """
        target = anxiety * 0.50 + aversive * 0.25 + septal * 0.10
        target += craving * 0.20
        return min(1.0, max(0.0, target))

    # ------------------------------------------------------------------
    # Glutamate co-release with cholinergic
    # ------------------------------------------------------------------
    def _glutamate_target(self, cholinergic: float, septal: float) -> float:
        """Co-released glutamate scales with cholinergic + septal drive."""
        return min(1.0, cholinergic * 0.7 + septal * 0.20)

    # ------------------------------------------------------------------
    # IPN command — aggregate signal to interpeduncular nucleus
    # ------------------------------------------------------------------
    def _ipn_command(self, cholinergic: float, substance_p: float,
                       glutamate: float) -> float:
        """Combined drive to IPN."""
        return min(1.0, cholinergic * 0.4 + substance_p * 0.35 + glutamate * 0.25)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, anxiety: float, craving: float,
                          cholinergic: float, substance_p: float) -> str:
        """Classify MHb operating mode."""
        if anxiety > self.ANXIETY_THRESHOLD and substance_p > 0.30:
            return "anxiety_active"
        if craving > self.WITHDRAWAL_THRESHOLD and cholinergic > 0.30:
            return "withdrawal_active"
        if cholinergic > 0.10:
            return "tonic_baseline"  # MHb always tonically active
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick
    # ==================================================================
    def _tonic_baseline_floor(self, septal: float) -> float:
        """Always-present tonic floor (Gorlich 2013).
        MHb fires at 1-5 Hz baseline even without explicit input. Septal
        glutamate input scales the floor upward.
        """
        return min(0.30, self.BASELINE_TONIC + septal * 0.10)

    def _septal_corelease_balance(self, glu: float, chol: float) -> float:
        """Balance between glutamate co-release and ACh signal —
        differential corticostriatal vs IPN-targeted output.
        """
        if (glu + chol) < 0.05:
            return 0.0
        return min(1.0, glu / (glu + chol + 0.001))

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "mhb_chol": self.state.get("mhb_cholinergic_drive", 0.0),
            "mhb_subP": self.state.get("mhb_substance_p_drive", 0.0),
            "mhb_glu": self.state.get("mhb_glutamate_drive", 0.0),
            "ipn_cmd": self.state.get("ipn_drive_command", 0.0),
            "state": self.state.get("mhb_state", "quiet"),
        }
    def _ipn_target_split_by_subdivision(self, chol: float, subp: float) -> dict:
        """MHb dorsal vs ventral subdivision targeting (Aizawa 2012).
        Dorsal MHb (substance-P) → lateral IPN.
        Ventral MHb (cholinergic) → central IPN.
        """
        return {
            "lateral_ipn": min(1.0, subp * 0.85),
            "central_ipn": min(1.0, chol * 0.85),
        }

    def _withdrawal_amplification_streak(self, recent_states: list) -> int:
        """Count recent ticks of sustained withdrawal_active state.
        Models nicotine-withdrawal aversion buildup over minutes."""
        if not recent_states:
            return 0
        return sum(1 for s in recent_states[-30:] if s == "withdrawal_active")


    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ts = prior.get("TriangularSeptal", {})
        if not ts:
            ts = prior.get("SeptalProxy", {})
        septal = float(ts.get("ts_drive", ts.get("septal_glutamate", 0.20)))

        dbb_data = prior.get("DiagonalBandBroca", {})
        dbb = float(dbb_data.get("dbb_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        anxiety = float(valence.get("anxiety_intensity",
                            valence.get("valence_intensity", 0.0)))
        aversive = float(valence.get("aversive_signal", 0.0))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        nic = prior.get("NicotineWithdrawalProxy", {})
        craving = float(nic.get("craving_signal", 0.0))

        # --- Cholinergic ---
        chol_target = self._cholinergic_target(septal, dbb, craving, arousal)
        prev_chol = float(self.state.get("mhb_cholinergic_drive",
                                          self.BASELINE_TONIC))
        new_chol = self._smooth(prev_chol, chol_target)

        # --- Substance-P ---
        subp_target = self._substance_p_target(anxiety, aversive, septal, craving)
        prev_subp = float(self.state.get("mhb_substance_p_drive", 0.0))
        new_subp = self._smooth(prev_subp, subp_target)

        # --- Glutamate ---
        glu_target = self._glutamate_target(new_chol, septal)
        prev_glu = float(self.state.get("mhb_glutamate_drive",
                                         self.BASELINE_TONIC))
        new_glu = self._smooth(prev_glu, glu_target)

        # --- IPN command ---
        ipn_cmd = self._ipn_command(new_chol, new_subp, new_glu)

        state = self._classify_state(anxiety, craving, new_chol, new_subp)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mhb_cholinergic_drive"] = round(new_chol, 4)
        self.state["mhb_substance_p_drive"] = round(new_subp, 4)
        self.state["mhb_glutamate_drive"] = round(new_glu, 4)
        self.state["ipn_drive_command"] = round(ipn_cmd, 4)
        self.state["mhb_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mhb_cholinergic_drive": round(new_chol, 4),
            "mhb_substance_p_drive": round(new_subp, 4),
            "mhb_glutamate_drive": round(new_glu, 4),
            "ipn_drive_command": round(ipn_cmd, 4),
            "mhb_state": state,
        }
