"""
BNSTAnterolateral -- BNST-AL / Sustained Fear / Anxiety Hub

NEURAL SUBSTRATE
================
Anterolateral bed nucleus of stria terminalis (BNST-AL) is part of the
"extended amygdala" -- anatomically continuous with central amygdala but
functionally distinct. Walker & Davis 1997 demonstrated double dissociation:
CeA mediates phasic conditioned fear, BNST mediates SUSTAINED unconditioned
anxiety (long-duration responses to diffuse threats: bright light, predator
contexts, CRH infusion).

BNST-AL contains diverse glutamatergic + GABAergic populations including
CRH+, somatostatin+, neuropeptide Y+ neurons. Outputs: hypothalamus
(autonomic), brainstem (PAG), VTA (motivation), CeA (fear coupling).

Inputs: BLA, vSub (ventral hippocampus), mPFC, paraventricular
thalamus, central amygdala, brainstem aminergic.

KEY FINDINGS
============
1. BNST mediates sustained unconditioned anxiety; CeA mediates phasic
   conditioned fear -- double dissociation -- [Walker 1997, Ann NY Acad
   Sci 821:198, doi:10.1111/j.1749-6632.1997.tb48289.x]
2. CRH infusion into BNST produces sustained anxiety; CRH from CeA
   recruits BNST CRH+ neurons -- [Lee 1997, Brain Res 757:25, PMID 9200488]
3. Optogenetic activation of BLA→BNST pathway is anxiogenic; distinct
   subpathways anxiogenic vs anxiolytic -- [Kim 2013, Nature 496:219,
   doi:10.1038/nature12018]
4. BNST CRH+ neurons drive avoidance behavior; ablation reduces
   anxiety in chronic stress models -- [Pleil 2015, Nat Neurosci
   18:545, PMID 25751533]
5. BNST→VTA pathway gates fear-induced disengagement from reward;
   bidirectional anxiogenic vs anxiolytic populations --
   [Jennings 2013, Nature 496:224, doi:10.1038/nature12041]

INPUTS
======
- BasolateralAmygdala.bla_drive (or BasalAmygdala)
- HippocampalCA1Output.ca1_drive (ventral hipp context)
- CRHStressDispatcher.crh_release
- ParaventricularThalamus.pvt_drive (aversive arousal)
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- bnst_al_drive (0-1)
- sustained_anxiety_signal (0-1)
- crh_release (0-1)
- pag_anxiety_command (0-1)
- vta_disengage_signal (0-1)
- bnst_al_state (str): "sustained_anxiety" | "chronic_stress" |
  "anxiogenic" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class BNSTAnterolateral(BrainMechanism):
    """BNST-AL -- sustained anxiety / unconditioned fear hub."""

    BASELINE = 0.10
    SMOOTH = 0.15  # Slow dynamics -- sustained anxiety is long-duration
    ANXIETY_THRESHOLD = 0.40
    CHRONIC_THRESHOLD = 50

    def __init__(self):
        super().__init__(
            name="BNSTAnterolateral",
            human_analog="BNST anterolateral (sustained anxiety)",
            layer="limbic",
        )
        self.state.setdefault("bnst_al_drive", self.BASELINE)
        self.state.setdefault("sustained_anxiety_signal", 0.0)
        self.state.setdefault("crh_release", 0.0)
        self.state.setdefault("pag_anxiety_command", 0.0)
        self.state.setdefault("vta_disengage_signal", 0.0)
        self.state.setdefault("bnst_al_state", "quiet")
        self.state.setdefault("anxiety_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, bla: float, ca1: float, crh: float, pvt: float,
                       valence_sign: int, intensity: float) -> float:
        """BNST-AL firing -- sustained-state integrator (slow)."""
        target = self.BASELINE + bla * 0.20 + ca1 * 0.20 + pvt * 0.20
        target += crh * 0.30
        if valence_sign < 0:
            target += intensity * 0.20
        return min(1.0, target)

    def _sustained_anxiety(self, drive: float, anxiety_streak: int) -> float:
        """Sustained anxiety signal -- accumulates over time (Walker 1997)."""
        if drive < 0.30:
            return drive * 0.5
        # Streak-based amplification (chronic anxiety builds slowly)
        streak_factor = min(1.0, anxiety_streak / 30.0)
        return min(1.0, drive * (0.7 + streak_factor * 0.5))

    def _crh_release_compute(self, drive: float, valence_sign: int) -> float:
        """CRH+ subset releases CRH (Pleil 2015)."""
        if valence_sign >= 0:
            return drive * 0.3
        return min(1.0, drive * 0.85)

    def _pag_anxiety(self, sustained: float) -> float:
        """BNST→PAG sustained-anxiety motor coupling."""
        return min(1.0, sustained * 0.85)

    def _vta_disengage(self, drive: float, sustained: float) -> float:
        """BNST→VTA fear-induced reward disengagement (Jennings 2013)."""
        return min(1.0, drive * 0.4 + sustained * 0.5)

    def _classify_state(self, sustained: float, drive: float,
                          anxiety_streak: int) -> str:
        if anxiety_streak > self.CHRONIC_THRESHOLD and sustained > 0.40:
            return "chronic_stress"
        if sustained > self.ANXIETY_THRESHOLD:
            return "sustained_anxiety"
        if drive > 0.30:
            return "anxiogenic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", bla_data.get("ba_fear_neurons", 0.0)))

        ca1_data = prior.get("HippocampalCA1Output", {})
        ca1 = float(ca1_data.get("ca1_drive", 0.0))

        crh_data = prior.get("CRHStressDispatcher", {})
        crh = float(crh_data.get("crh_release", 0.0))

        pvt_data = prior.get("ParaventricularThalamus", {})
        pvt = float(pvt_data.get("pvt_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        valence_sign = int(valence.get("valence_sign", 0))
        intensity = float(valence.get("valence_intensity", 0.0))

        target = self._drive_target(bla, ca1, crh, pvt, valence_sign, intensity)
        prev_drive = float(self.state.get("bnst_al_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        prev_streak = int(self.state.get("anxiety_streak", 0))
        if new_drive > 0.30:
            anxiety_streak = prev_streak + 1
        else:
            anxiety_streak = max(0, prev_streak - 2)

        sustained = self._sustained_anxiety(new_drive, anxiety_streak)
        crh_out = self._crh_release_compute(new_drive, valence_sign)
        pag_cmd = self._pag_anxiety(sustained)
        vta_dis = self._vta_disengage(new_drive, sustained)

        state = self._classify_state(sustained, new_drive, anxiety_streak)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["bnst_al_drive"] = round(new_drive, 4)
        self.state["sustained_anxiety_signal"] = round(sustained, 4)
        self.state["crh_release"] = round(crh_out, 4)
        self.state["pag_anxiety_command"] = round(pag_cmd, 4)
        self.state["vta_disengage_signal"] = round(vta_dis, 4)
        self.state["bnst_al_state"] = state
        self.state["anxiety_streak"] = anxiety_streak
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "bnst_al_drive": round(new_drive, 4),
            "sustained_anxiety_signal": round(sustained, 4),
            "crh_release": round(crh_out, 4),
            "pag_anxiety_command": round(pag_cmd, 4),
            "vta_disengage_signal": round(vta_dis, 4),
            "bnst_al_state": state,
            "anxiety_streak": anxiety_streak,
        }

    def _hyper_aroused_anxiety(self, recent_states: list) -> float:
        """Sustained anxiety_active or chronic_stress in window -- proxy for
        clinical anxiety disorder severity."""
        if not recent_states:
            return 0.0
        anxiety_count = sum(1 for s in recent_states[-50:]
                              if s in ("sustained_anxiety", "chronic_stress"))
        return anxiety_count / max(1, len(recent_states[-50:]))

    def _anxiety_recovery_rate(self, anxiety_streak: int,
                                 bnst_drive: float) -> float:
        """Anxiety recovery rate -- how fast does BNST-AL activity
        return to baseline after stress offset? High streak =
        slow recovery (chronic anxiety pattern)."""
        if anxiety_streak < 5:
            return 1.0
        return max(0.0, 1.0 - anxiety_streak / 150.0)

    def _sustained_negative_affect_proxy(self, sustained: float,
                                          anxiety_streak: int) -> float:
        """Sustained negative affect proxy -- chronic BNST-AL
        activation underlies negative emotional states. Returns
        negative affect intensity (0-1)."""
        if sustained < 0.20:
            return 0.0
        return min(1.0, sustained * (1.0 + anxiety_streak / 200.0))

    def _cortisol_feedback_index(self, bnst_drive: float,
                                  sustained: float) -> float:
        """Cortisol feedback index -- BNST-AL activity drives
        HPA axis; cortisol feedback modulates drive. High drive
        + sustained = cortisol resistance pattern."""
        if bnst_drive < 0.20:
            return 0.0
        return min(1.0, bnst_drive * sustained * 1.3)

    def _anxiety_trait_vulnerability(self, anxiety_streak: int,
                                      sustained: float) -> float:
        """Anxiety trait vulnerability -- slow-moving baseline of
        anxiety proneness. High sustained activity over time
        increases trait anxiety, making future stress more
        likely to produce sustained anxiety responses."""
        if anxiety_streak < 10:
            return 0.0
        return min(1.0, sustained * (anxiety_streak / 100.0) * 0.5)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("bnst_al_drive", 0.0),
            "sustained": self.state.get("sustained_anxiety_signal", 0.0),
            "crh": self.state.get("crh_release", 0.0),
            "state": self.state.get("bnst_al_state", "quiet"),
        }
