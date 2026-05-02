"""
BNSTOval -- BNST-Ov / CRH-Rich Stress-Integration Subdivision

NEURAL SUBSTRATE
================
The oval nucleus of BNST (BNST-Ov) is a CRH+ enriched subdivision in the
dorsolateral BNST. Highest density of CRH+ neurons in the brain. Distinct
from anterolateral BNST (anxiety hub) -- Ov is the principal stress-CRH
integrator providing CRH peptide release to extended amygdala targets.

Anatomical features: small, oval-shaped (origin of name), GABAergic
projections, CRH co-release. Strong projections to VTA, RVLM, and
brainstem aminergic nuclei.

KEY FINDINGS
============
1. BNST-Ov contains highest density of CRH+ neurons in the brain;
   stress-activated subset -- [Ju 1989, J Comp Neurol 280:587,
   PMID 2466957]
2. CRH from BNST-Ov drives chronic stress-induced anxiety; CRH-R1
   antagonism in BNST is anxiolytic -- [Sahuque 2006, Psychopharmacology
   186:122, PMID 16550388]
3. BNST-Ov→VTA pathway gates dopamine response to stressors;
   distinct from medial BNST → VTA -- [Crestani 2013, Curr Top Behav
   Neurosci 13:189, PMID 21796462]
4. Optogenetic activation of BNST-Ov CRH+ neurons produces sustained
   freezing + anxiogenic behavior -- [Daniel 2014, Nat Neurosci
   17:1644, PMID 25344631]
5. BNST-Ov hyperactivity in chronic stress + PTSD models; drives
   chronic-state HPA dysregulation -- [Lebow 2016, Mol Psychiatry
   21:450, doi:10.1038/mp.2016.1]

INPUTS
======
- CRHStressDispatcher.crh_release
- ParaventricularAutonomic.pvn_stress_drive
- BasalAmygdala.cea_drive_command
- ValenceTagger.aversive_signal, .valence_intensity
- ArousalRegulator.tonic_level

OUTPUTS
=======
- bnst_ov_drive (0-1)
- crh_peptide_release (0-1)
- vta_stress_modulation (0-1)
- chronic_stress_signal (0-1)
- bnst_ov_state (str): "stress_active" | "chronic_hpa_dysreg" |
  "anxiogenic" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class BNSTOval(BrainMechanism):
    """BNST-Ov -- CRH-rich subdivision driving chronic stress signals."""

    BASELINE = 0.10
    SMOOTH = 0.15
    STRESS_THRESHOLD = 0.40
    CHRONIC_THRESHOLD = 60

    def __init__(self):
        super().__init__(
            name="BNSTOval",
            human_analog="BNST oval nucleus (CRH-rich stress hub)",
            layer="limbic",
        )
        self.state.setdefault("bnst_ov_drive", self.BASELINE)
        self.state.setdefault("crh_peptide_release", 0.0)
        self.state.setdefault("vta_stress_modulation", 0.0)
        self.state.setdefault("chronic_stress_signal", 0.0)
        self.state.setdefault("bnst_ov_state", "quiet")
        self.state.setdefault("stress_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, crh: float, pvn: float, bla: float,
                       aversive: float, arousal: float) -> float:
        """BNST-Ov firing -- CRH-driven primary, stress-coupled."""
        target = self.BASELINE + crh * 0.45 + pvn * 0.20 + bla * 0.15
        target += aversive * 0.20
        target += max(0.0, arousal - 0.40) * 0.10
        return min(1.0, target)

    def _crh_release_compute(self, drive: float) -> float:
        """CRH peptide release scales nonlinearly with drive (Daniel 2014).
        CRH+ neurons release more peptide at sustained high firing."""
        if drive < 0.20:
            return drive * 0.5
        return min(1.0, drive * 0.95)

    def _vta_modulation(self, drive: float, crh: float) -> float:
        """BNST-Ov→VTA stress-modulation of DA neurons (Crestani 2013)."""
        return min(1.0, drive * 0.5 + crh * 0.5)

    def _chronic_stress(self, drive: float, stress_streak: int) -> float:
        """Chronic stress signal -- accumulates with sustained drive
        (Lebow 2016 PTSD models)."""
        if stress_streak < self.CHRONIC_THRESHOLD:
            streak_factor = stress_streak / self.CHRONIC_THRESHOLD
        else:
            streak_factor = 1.0
        return min(1.0, drive * (0.5 + streak_factor * 0.5))

    def _classify_state(self, drive: float, chronic: float,
                          stress_streak: int) -> str:
        if stress_streak > self.CHRONIC_THRESHOLD and chronic > 0.40:
            return "chronic_hpa_dysreg"
        if drive > self.STRESS_THRESHOLD:
            return "stress_active"
        if drive > 0.25:
            return "anxiogenic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        crh_data = prior.get("CRHStressDispatcher", {})
        crh = float(crh_data.get("crh_release", 0.0))

        pvn_data = prior.get("ParaventricularAutonomic", {})
        pvn = float(pvn_data.get("pvn_stress_drive", 0.0))

        bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("cea_drive_command",
                        bla_data.get("ba_fear_neurons", 0.0)))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        target = self._drive_target(crh, pvn, bla, aversive, arousal)
        prev_drive = float(self.state.get("bnst_ov_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        prev_streak = int(self.state.get("stress_streak", 0))
        if new_drive > 0.30:
            stress_streak = prev_streak + 1
        else:
            stress_streak = max(0, prev_streak - 2)

        crh_out = self._crh_release_compute(new_drive)
        vta_mod = self._vta_modulation(new_drive, crh_out)
        chronic = self._chronic_stress(new_drive, stress_streak)

        state = self._classify_state(new_drive, chronic, stress_streak)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["bnst_ov_drive"] = round(new_drive, 4)
        self.state["crh_peptide_release"] = round(crh_out, 4)
        self.state["vta_stress_modulation"] = round(vta_mod, 4)
        self.state["chronic_stress_signal"] = round(chronic, 4)
        self.state["bnst_ov_state"] = state
        self.state["stress_streak"] = stress_streak
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "bnst_ov_drive": round(new_drive, 4),
            "crh_peptide_release": round(crh_out, 4),
            "vta_stress_modulation": round(vta_mod, 4),
            "chronic_stress_signal": round(chronic, 4),
            "bnst_ov_state": state,
        }

    def _hpa_axis_dysregulation_index(self, recent_states: list) -> float:
        """Chronic HPA dysregulation -- proportion of chronic_hpa_dysreg
        in recent window (Lebow 2016 PTSD analog)."""
        if not recent_states:
            return 0.0
        chronic_count = sum(1 for s in recent_states[-100:]
                              if s == "chronic_hpa_dysreg")
        return chronic_count / max(1, len(recent_states[-100:]))

    def _crh_cortisol_feedback_strength(self, crh: float,
                                         arousal: float) -> float:
        """CRH-cortisol feedback gain -- how strongly does CRH drive
        arousal vs being damped by feedback?

        Sahuque 2006: CRH-R1 antagonism in BNST-Ov is anxiolytic,
        suggesting CRH acts synergistically with arousal to drive
        sustained stress activation. This computes a feedback gain factor.
        """
        if crh < 0.20:
            return 0.0
        return min(1.0, crh * arousal * 1.2 + crh * 0.2)

    def _anxiety_trait_proxy(self, stress_streak: int,
                               chronic_signal: float) -> float:
        """Trait anxiety proxy -- slow-moving anxiety baseline.

        Unlike state anxiety (tick-to-tick), trait anxiety is a stable
        individual difference. Approximated here as the relationship
        between stress_streak accumulation rate and chronic signal.
        High trait proxy = predisposition to sustained anxiety.
        """
        streak_rate = stress_streak / max(1, 200)
        return min(1.0, streak_rate * 0.5 + chronic_signal * 0.5)

    def _gabaergic_modulation_strength(self, drive: float,
                                        stress_streak: int) -> float:
        """GABAergic modulation of BNST-Ov output.

        BNST-Ov is GABAergic; its output represents disinhibition of
        downstream stress targets. Higher drive = less GABAergic
        inhibition of stress circuits.
        """
        if stress_streak > self.CHRONIC_THRESHOLD:
            # Chronic stress weakens GABAergic control
            return max(0.0, 0.3 - (stress_streak - self.CHRONIC_THRESHOLD) * 0.005)
        return min(1.0, 1.0 - drive * 0.5)

    def _sexual_dimorphism_index(self, drive: float,
                                  stress_streak: int) -> float:
        """Sexual dimorphism in BNST-Ov stress response.

        BNST itself shows marked sexual dimorphism. BNST-Ov CRH+
        neurons are more responsive in females under chronic stress
        conditions. This returns a dimorphism factor based on
        sustained stress activation.
        """
        if stress_streak < 10:
            return 0.5  # baseline dimorphism
        # Females show higher sustained activation under chronic stress
        return min(1.0, 0.5 + stress_streak * 0.003)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("bnst_ov_drive", 0.0),
            "crh": self.state.get("crh_peptide_release", 0.0),
            "chronic": self.state.get("chronic_stress_signal", 0.0),
            "state": self.state.get("bnst_ov_state", "quiet"),
        }
