"""
NucleusAccumbensCore — NAcC / Instrumental Learning + Goal-Directed Action

NEURAL SUBSTRATE
================
The core subdivision of nucleus accumbens (NAcC) sits dorsolateral to the
shell, serving distinct function: instrumental Pavlovian-instrumental
transfer (PIT), goal-directed action selection, motivation for cue-driven
behavior. Distinct from NAc shell (hedonic) and lateral shell (aversive).

Inputs: BLA, dorsal PFC (pl/ACC), VTA, intralaminar thalamus.
Outputs: ventral pallidum (motor pathway), ventromedial striatum-pallido-
thalamo-cortical loop.

Cardinal 2002 demonstrated NAcC lesions impair appetitive Pavlovian-
instrumental transfer (cue-evoked approach + lever pressing) without
affecting basal hedonic responses. NAcC is the action-engine of reward
processing, distinct from "liking" hotspot in shell.

D1+ direct pathway / D2+ indirect pathway dichotomy applies here too.

KEY FINDINGS
============
1. NAcC lesions impair Pavlovian-instrumental transfer + goal-directed
   action selection without affecting hedonic responses —
   [Cardinal 2002, Neurosci Biobehav Rev 26:321, doi:10.1016/S0149-7634(02)00007-6]
2. NAcC neurons encode predicted reward value + motivational vigor;
   distinct from shell encoding —
   [Roitman 2005, Neuron 48:799, doi:10.1016/j.neuron.2005.10.013]
3. BLA→NAcC pathway is rewarding; cue-evoked motivation —
   [Stuber 2011, Nature 475:377, doi:10.1038/nature10194]
4. NAcC D1 vs D2 medium spiny neurons distinct functions: D1 promotes
   action, D2 inhibits — [Kravitz 2012, Nat Neurosci 15:816, doi:10.1038/nn.3100]
5. NAcC BOLD activity predicts motivated effort + expected reward in
   humans — [Knutson 2005, Trends Cogn Sci 9:557, doi:10.1016/j.tics.2005.10.011]

INPUTS
======
- BasolateralAmygdala.bla_drive
- VentralTegmentalDopamine.da_release, .da_burst
- PrelimbicCortex.pl_drive
- ParaventricularThalamus.pvt_drive
- ValenceTagger.valence_sign, .valence_intensity

OUTPUTS
=======
- nacc_drive (0-1)
- pit_signal (0-1) — Pavlovian-instrumental transfer
- goal_directed_action (0-1)
- vp_motor_command (0-1)
- d1_direct (0-1)
- d2_indirect (0-1)
- nacc_state (str): "pit_active" | "goal_action" |
  "motivation_high" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class NucleusAccumbensCore(BrainMechanism):
    """NAcC — instrumental learning + goal-directed motivation."""

    BASELINE = 0.10
    SMOOTH = 0.20
    PIT_THRESHOLD = 0.40
    ACTION_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="NucleusAccumbensCore",
            human_analog="Nucleus accumbens core (instrumental + goal action)",
            layer="limbic",
        )
        self.state.setdefault("nacc_drive", self.BASELINE)
        self.state.setdefault("pit_signal", 0.0)
        self.state.setdefault("goal_directed_action", 0.0)
        self.state.setdefault("vp_motor_command", 0.0)
        self.state.setdefault("d1_direct", 0.0)
        self.state.setdefault("d2_indirect", 0.0)
        self.state.setdefault("nacc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, bla: float, da: float, pl: float, pvt: float,
                       appetitive: float) -> float:
        """NAcC firing — driven by BLA cue + DA + PL goal-state."""
        target = self.BASELINE + bla * 0.30 + da * 0.30 + pl * 0.20 + pvt * 0.10
        target += appetitive * 0.15
        return min(1.0, target)

    def _pit_signal(self, bla: float, drive: float, appetitive: float) -> float:
        """Pavlovian-instrumental transfer (Cardinal 2002)."""
        if appetitive < 0.20:
            return 0.0
        return min(1.0, bla * 0.4 + drive * 0.3 + appetitive * 0.3)

    def _goal_directed(self, drive: float, pl: float) -> float:
        """Goal-directed action signal — requires PFC goal-state input."""
        if pl < 0.25:
            return 0.0
        return min(1.0, drive * 0.5 + pl * 0.5)

    def _vp_motor(self, drive: float, pit: float) -> float:
        """NAcC → ventral pallidum → motor pathway."""
        return min(1.0, drive * 0.5 + pit * 0.5)

    def _d1(self, drive: float, da: float) -> float:
        return min(1.0, drive * 0.5 + da * 0.5)

    def _d2(self, drive: float, da: float) -> float:
        if da > 0.50:
            return drive * 0.2
        return min(1.0, drive * 0.5 + (1.0 - da) * 0.4)

    def _classify_state(self, pit: float, goal: float, drive: float) -> str:
        if pit > self.PIT_THRESHOLD:
            return "pit_active"
        if goal > self.ACTION_THRESHOLD:
            return "goal_action"
        if drive > 0.30:
            return "motivation_high"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", bla_data.get("nac_drive_command", 0.0)))

        vta_data = prior.get("VentralTegmentalDopamine", {})
        da = float(vta_data.get("da_release", vta_data.get("da_burst", 0.0)))

        pl_data = prior.get("PrelimbicCortex", {})
        pl = float(pl_data.get("pl_drive", 0.0))

        pvt_data = prior.get("ParaventricularThalamus", {})
        pvt = float(pvt_data.get("pvt_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        sign = int(valence.get("valence_sign", 0))
        intensity = float(valence.get("valence_intensity", 0.0))
        appetitive = max(0.0, sign * intensity)

        target = self._drive_target(bla, da, pl, pvt, appetitive)
        prev_drive = float(self.state.get("nacc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        pit = self._pit_signal(bla, new_drive, appetitive)
        goal = self._goal_directed(new_drive, pl)
        vp = self._vp_motor(new_drive, pit)
        d1 = self._d1(new_drive, da)
        d2 = self._d2(new_drive, da)

        state = self._classify_state(pit, goal, new_drive)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["nacc_drive"] = round(new_drive, 4)
        self.state["pit_signal"] = round(pit, 4)
        self.state["goal_directed_action"] = round(goal, 4)
        self.state["vp_motor_command"] = round(vp, 4)
        self.state["d1_direct"] = round(d1, 4)
        self.state["d2_indirect"] = round(d2, 4)
        self.state["nacc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "nacc_drive": round(new_drive, 4),
            "pit_signal": round(pit, 4),
            "goal_directed_action": round(goal, 4),
            "vp_motor_command": round(vp, 4),
            "d1_direct": round(d1, 4),
            "d2_indirect": round(d2, 4),
            "nacc_state": state,
        }

    def _motivational_vigor(self, drive: float, da: float) -> float:
        """Effort-based motivation (Knutson 2005)."""
        return min(1.0, drive * 0.5 + da * 0.5)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("nacc_drive", 0.0),
            "pit": self.state.get("pit_signal", 0.0),
            "goal": self.state.get("goal_directed_action", 0.0),
            "state": self.state.get("nacc_state", "quiet"),
        }
