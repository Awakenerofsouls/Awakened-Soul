"""
NucleusAccumbensLateralShell -- NAc-LS / Aversive Motivational Subset

NEURAL SUBSTRATE
================
Lateral shell of nucleus accumbens (NAc-LS) is a topographically distinct
subdivision of NAc shell with distinct opioid keyboard mapping (Reynolds &
Berridge 2002). Whereas the medial shell rostrodorsal subregion is the
hedonic hotspot for "liking", the caudal lateral shell is the AVERSIVE
keyboard -- DAMGO injection here produces fear/disgust expression.

Inputs: BLA, vSub, mPFC, VTA dopamine. Outputs: ventral pallidum, lateral
hypothalamus, VTA, midbrain.

The NAc-LS contributes to defensive motivation, aversive salience encoding,
and stress-induced behaviors. Distinct neuronal populations encode
appetitive vs aversive valence signals at single-cell resolution.

KEY FINDINGS
============
1. NAc shell exhibits topographic opioid keyboard -- mu-opioid in
   rostrodorsal medial shell enhances "liking", in caudal lateral
   shell produces aversion + fear -- [Reynolds 2002, J Neurosci
   22:7308, PMID 12177226]
2. NAc-LS GABAergic projection neurons drive aversive motivation via
   ventral pallidum + lateral hypothalamus targets -- [Faure 2008,
   J Neurosci 28:7184, PMID 18614688]
3. BLA→NAc-LS pathway is anxiogenic; distinct from BLA→NAc-medial
   reward pathway -- [Stuber 2011, Nature 475:377, doi:10.1038/nature10194]
4. Stress-induced motivation deficits map to NAc-LS hyperactivity;
   chronic stress shifts dopamine response -- [Russo 2013, Nat Rev
   Neurosci 14:609, doi:10.1038/nrn3381]
5. NAc shell direct vs indirect pathway D1 vs D2 differential
   contribution to motivation -- [Kravitz 2012, Nat Neurosci 15:816,
   doi:10.1038/nn.3100]

INPUTS
======
- BasolateralAmygdala.bla_drive
- HippocampalCA1Output.ca1_drive
- VentralTegmentalDopamine.da_release
- ValenceTagger.aversive_signal, .valence_intensity
- LateralHabenula.anti_reward_signal

OUTPUTS
=======
- nac_ls_drive (0-1)
- aversive_motivation_signal (0-1)
- defensive_command (0-1)
- vp_aversive_drive (0-1)
- lh_drive_command (0-1)
- nac_ls_state (str): "aversive_motivation" | "stress_signal" |
  "defensive" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class NucleusAccumbensLateralShell(BrainMechanism):
    """NAc-LS -- aversive subdivision, defensive motivation."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AVERSIVE_THRESHOLD = 0.40
    DEFENSIVE_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="NucleusAccumbensLateralShell",
            human_analog="Nucleus accumbens lateral shell (aversive)",
            layer="limbic",
        )
        self.state.setdefault("nac_ls_drive", self.BASELINE)
        self.state.setdefault("aversive_motivation_signal", 0.0)
        self.state.setdefault("defensive_command", 0.0)
        self.state.setdefault("vp_aversive_drive", 0.0)
        self.state.setdefault("lh_drive_command", 0.0)
        self.state.setdefault("nac_ls_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, bla: float, ca1: float, da: float,
                       aversive: float, lhb: float) -> float:
        """NAc-LS firing -- driven by BLA aversive + DA + LHb anti-reward."""
        target = self.BASELINE + bla * 0.30 + ca1 * 0.15 + aversive * 0.30
        target += lhb * 0.20
        # DA modulation: stress-shifted DA also recruits LS (Russo 2013)
        target += da * 0.10
        return min(1.0, target)

    def _aversive_motivation(self, drive: float, aversive: float,
                               lhb: float) -> float:
        """Aversive motivation signal -- combined drive + aversive + LHb."""
        if aversive < 0.20 and lhb < 0.20:
            return 0.0
        return min(1.0, drive * 0.5 + aversive * 0.3 + lhb * 0.2)

    def _defensive_command(self, drive: float, aversive: float,
                             intensity: float) -> float:
        """Defensive motor command via VP→LH (Faure 2008)."""
        if drive < self.DEFENSIVE_THRESHOLD or aversive < 0.30:
            return 0.0
        return min(1.0, drive * intensity * 1.2)

    def _vp_aversive(self, drive: float) -> float:
        """NAc-LS→VP aversive output."""
        return min(1.0, drive * 0.85)

    def _lh_drive(self, drive: float, defensive: float) -> float:
        """NAc-LS→LH drives feeding inhibition + defense (Stuber 2011)."""
        return min(1.0, drive * 0.5 + defensive * 0.5)

    def _classify_state(self, drive: float, aversive_motivation: float,
                          defensive: float) -> str:
        if defensive > 0.30:
            return "defensive"
        if aversive_motivation > self.AVERSIVE_THRESHOLD:
            return "aversive_motivation"
        if drive > 0.30:
            return "stress_signal"
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

        vta_data = prior.get("VentralTegmentalDopamine", {})
        da = float(vta_data.get("da_release", vta_data.get("da_burst", 0.0)))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))
        intensity = float(valence.get("valence_intensity", 0.0))

        lhb_data = prior.get("LateralHabenula", {})
        lhb = float(lhb_data.get("anti_reward_signal", 0.0))

        target = self._drive_target(bla, ca1, da, aversive, lhb)
        prev_drive = float(self.state.get("nac_ls_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        aversive_mot = self._aversive_motivation(new_drive, aversive, lhb)
        defensive = self._defensive_command(new_drive, aversive, intensity)
        vp_av = self._vp_aversive(new_drive)
        lh_cmd = self._lh_drive(new_drive, defensive)

        state = self._classify_state(new_drive, aversive_mot, defensive)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["nac_ls_drive"] = round(new_drive, 4)
        self.state["aversive_motivation_signal"] = round(aversive_mot, 4)
        self.state["defensive_command"] = round(defensive, 4)
        self.state["vp_aversive_drive"] = round(vp_av, 4)
        self.state["lh_drive_command"] = round(lh_cmd, 4)
        self.state["nac_ls_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "nac_ls_drive": round(new_drive, 4),
            "aversive_motivation_signal": round(aversive_mot, 4),
            "defensive_command": round(defensive, 4),
            "vp_aversive_drive": round(vp_av, 4),
            "lh_drive_command": round(lh_cmd, 4),
            "nac_ls_state": state,
        }

    def _opioid_keyboard_position(self) -> str:
        """Indicator: NAc-LS represents the AVERSIVE position on opioid
        keyboard (Reynolds 2002). Always returns aversive label."""
        return "aversive_keyboard"

    def _aversion_prediction_error(self, aversive_mot: float,
                                        prev_aversive_mot: float) -> float:
        """Aversive prediction error -- difference between expected and
        received aversive signals. Positive = aversive worse than expected.
        Modulates learning in lateral shell circuits."""
        rpe = aversive_mot - prev_aversive_mot
        return max(-1.0, min(1.0, rpe))

    def _habit_threshold_detection(self, lh_drive: float,
                                   aversive_mot: float) -> float:
        """Habit formation threshold -- Stuber 2011 showed NAc-LS
        transitions from goal-directed to habitual with repeated
        aversive conditioning. Returns habit-cue strength (0-1)."""
        if aversive_mot < 0.30:
            return 0.0
        return min(1.0, lh_drive * aversive_mot * 0.8)

    def _goal_directed_residual(self, drive: float,
                                  habit_strength: float) -> float:
        """Goal-directed residual -- NAc-LS can retain goal-directed
        signals even when habit is engaged. Distinct from habit circuit."""
        if drive < 0.20:
            return 0.0
        return max(0.0, drive - habit_strength * 0.5)

    def _compulsive_checking_proxy(self, aversive_mot: float,
                                    lh_drive: float,
                                    drive: float) -> float:
        """Compulsive checking proxy -- model of OCD-like compulsions.
        High aversive motivation + high LH drive + low goal-directed
        residual suggests compulsive checking behavior."""
        if aversive_mot < 0.30 or lh_drive < 0.20:
            return 0.0
        residual = max(0.0, drive - lh_drive * aversive_mot * 0.8)
        return max(0.0, aversive_mot * lh_drive - residual * 0.3)


    def _avoidance_habit_strength(self, lh_drive: float,
                                  aversive_mot: float) -> float:
        """Avoidance habit strength -- Stuber 2011: repeated
        avoidance training shifts NAc-LS from goal-directed
        to habitual. Returns habit dominance (0=goal, 1=habit)."""
        if aversive_mot < 0.20:
            return 0.0
        return min(1.0, lh_drive * aversive_mot * 0.9)

    def _frustration_signal(self, aversive_mot: float,
                           prev_aversive_mot: float) -> float:
        """Frustration signal -- unexpected lack of reward or
        unexpected aversive outcome generates frustration.
        NAc-LS tracks aversive contrast (Reynolds 2002)."""
        contrast = aversive_mot - prev_aversive_mot
        if contrast < 0:
            return max(0.0, -contrast * 0.5)
        return 0.0

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("nac_ls_drive", 0.0),
            "aversive": self.state.get("aversive_motivation_signal", 0.0),
            "defensive": self.state.get("defensive_command", 0.0),
            "state": self.state.get("nac_ls_state", "quiet"),
        }
