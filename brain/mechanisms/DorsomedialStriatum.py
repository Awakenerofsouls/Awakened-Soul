"""
DorsomedialStriatum — DMS / Goal-Directed / Associative Striatum

NEURAL SUBSTRATE
================
The dorsomedial striatum (DMS, caudate analog in primates) is the
associative subdivision of dorsal striatum, dedicated to goal-directed
action-outcome (A-O) learning. DMS receives mPFC + OFC + MD-thalamus
input and is engaged early in instrumental learning when actions are
explicitly tied to specific outcomes. As training extends and outcomes
become predictable, control transitions from DMS (goal-directed) to
DLS (habitual) — Yin 2005 dichotomy.

Selective DMS lesion converts goal-directed behavior into habitual:
animals continue working for an outcome they've been satiated on,
ignoring the contingency change (Balleine 2010 reversal-learning logic).

Functional architecture mirrors DLS — D1+ direct + D2+ indirect
medium-spiny neuron split — but inputs and learning rules differ. DMS
plasticity is gated by DA release that tracks action-outcome value
specifically (Hart 2014), distinguishing DMS from DLS where DA tracks
sensorimotor reinforcement.

Gremel & Costa 2013 demonstrated single-cell DMS recordings during
goal-directed-vs-habitual choice transitions — DMS firing is high
during goal-directed control and decreases as behavior becomes
habitual, with reciprocal increase in DLS.

KEY FINDINGS
============
1. DMS lesion converts goal-directed behavior to habitual; required for action-outcome learning — [Yin HH 2005, Eur J Neurosci 22:513, doi:10.1111/j.1460-9568.2005.04218.x]
2. DMS-DLS arbitration: DMS for goal-directed (A-O), DLS for habitual (S-R); extended-training transition — [Balleine BW 2010, Behav Brain Res 199:43, doi:10.1016/j.bbr.2008.10.034]
3. DMS DA release tracks action-outcome value during goal-directed choice; distinguishes from DLS DA — [Hart G 2014, J Neurosci 34:698, doi:10.1523/JNEUROSCI.4080-13.2014]
4. Single-cell DMS firing high during goal-directed, decreases as behavior becomes habitual; reciprocal with DLS — [Gremel CM 2013, Nat Commun 4:2264, doi:10.1038/ncomms3264]
5. DMS receives convergent mPFC + OFC + MD thalamic input; associative striatum substrate — [Voorn P 2004, Trends Neurosci 27:468, doi:10.1016/j.tins.2004.06.006]

INPUTS
======
- PrelimbicCortex.pl_drive (mPFC goal state)
- OrbitofrontalCortexLateral.lofc_drive (outcome identity)
- MediodorsalThalamus.md_drive — associative thalamic input
- SubstantiaNigraCompacta.da_release_dms
- DorsolateralStriatum.habit_strength_signal — competitor for control
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- dms_drive (0-1)
- d1_direct (0-1)
- d2_indirect (0-1)
- goal_directed_signal (0-1) — A-O contingency tracking
- action_outcome_value (0-1)
- gpi_drive (0-1)
- arbitration_with_dls (0-1) — relative weight DMS vs DLS for current control
- dms_state (str): "goal_directed" | "outcome_evaluating" |
  "ceding_to_habit" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class DorsomedialStriatum(BrainMechanism):
    """DMS — goal-directed associative striatum."""

    BASELINE = 0.10
    SMOOTH = 0.20
    GOAL_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="DorsomedialStriatum",
            human_analog="Dorsomedial striatum (goal-directed/associative)",
            layer="subcortical",
        )
        self.state.setdefault("dms_drive", self.BASELINE)
        self.state.setdefault("d1_direct", 0.0)
        self.state.setdefault("d2_indirect", 0.0)
        self.state.setdefault("goal_directed_signal", 0.0)
        self.state.setdefault("action_outcome_value", 0.0)
        self.state.setdefault("gpi_drive", 0.0)
        self.state.setdefault("arbitration_with_dls", 1.0)  # default = DMS in control
        self.state.setdefault("dms_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, pl: float, lofc: float, md: float,
                       da: float) -> float:
        """DMS drive — mPFC goal + OFC outcome-identity + MD associative."""
        target = (self.BASELINE + pl * 0.30 + lofc * 0.25
                    + md * 0.20 + da * 0.10)
        return min(1.0, target)

    def _d1_direct(self, drive: float, da: float) -> float:
        return min(1.0, drive * 0.5 + da * 0.5)

    def _d2_indirect(self, drive: float, da: float) -> float:
        return min(1.0, drive * 0.5 + max(0.0, 0.5 - da) * 0.6)

    def _goal_directed(self, drive: float, pl: float, lofc: float) -> float:
        """Goal-directed control signal — requires PFC goal + OFC outcome
        (Gremel 2013)."""
        if pl < 0.20 or lofc < 0.20:
            return drive * 0.30
        return min(1.0, drive * 0.4 + pl * 0.3 + lofc * 0.3)

    def _action_outcome_value(self, lofc: float, intensity: float,
                                sign: int) -> float:
        """A-O value — pulled from OFC outcome-identity + valence (Hart 2014)."""
        if lofc < 0.15:
            return 0.0
        return min(1.0, lofc * 0.5 + max(0.0, sign * intensity) * 0.5)

    def _gpi_drive(self, d1: float) -> float:
        return min(1.0, d1 * 0.85)

    def _arbitration(self, dms_drive: float, dls_habit: float) -> float:
        """DMS-vs-DLS arbitration (Balleine 2010 / Gremel 2013).

        High DLS habit = ceding control to DLS. Returns proportion of
        control DMS retains: 1.0 = DMS in control, 0.0 = DLS habit dominates.
        """
        if dls_habit < 0.20:
            return min(1.0, dms_drive * 1.5)
        # Habit pressure cedes control proportionally
        retention = dms_drive / max(0.001, dms_drive + dls_habit)
        return max(0.0, min(1.0, retention))

    def _classify_state(self, drive: float, goal: float,
                         arbitration: float) -> str:
        if drive < 0.20:
            return "quiet"
        if arbitration < 0.30:
            return "ceding_to_habit"
        if goal > self.GOAL_THRESHOLD:
            return "goal_directed"
        return "outcome_evaluating"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pl_data = prior.get("PrelimbicCortex", {})
        if not pl_data:
            pl_data = prior.get("MedialPrefrontalCortex", {})
        pl = float(pl_data.get("pl_drive",
                          pl_data.get("pfc_drive", 0.0)))

        lofc_data = prior.get("OrbitofrontalCortexLateral", {})
        if not lofc_data:
            lofc_data = prior.get("LateralOrbitofrontal", {})
        lofc = float(lofc_data.get("lofc_drive",
                            lofc_data.get("outcome_identity_signal", 0.0)))

        md_data = prior.get("MediodorsalThalamus", {})
        md = float(md_data.get("md_drive",
                          md_data.get("working_memory_signal", 0.0)))

        snc_data = prior.get("SubstantiaNigraCompacta", {})
        da = float(snc_data.get("da_release_dms",
                          snc_data.get("snc_drive", 0.0)))

        dls_data = prior.get("DorsolateralStriatum", {})
        dls_habit = float(dls_data.get("habit_strength_signal", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        target = self._drive_target(pl, lofc, md, da)
        prev_drive = float(self.state.get("dms_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        d1 = self._d1_direct(new_drive, da)
        d2 = self._d2_indirect(new_drive, da)
        goal = self._goal_directed(new_drive, pl, lofc)
        ao_value = self._action_outcome_value(lofc, intensity, sign)
        gpi = self._gpi_drive(d1)
        arbitration = self._arbitration(new_drive, dls_habit)

        state = self._classify_state(new_drive, goal, arbitration)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["dms_drive"] = round(new_drive, 4)
        self.state["d1_direct"] = round(d1, 4)
        self.state["d2_indirect"] = round(d2, 4)
        self.state["goal_directed_signal"] = round(goal, 4)
        self.state["action_outcome_value"] = round(ao_value, 4)
        self.state["gpi_drive"] = round(gpi, 4)
        self.state["arbitration_with_dls"] = round(arbitration, 4)
        self.state["dms_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('dms_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('dms_state', "quiet") if 'dms_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "dms_drive": round(new_drive, 4),
            "d1_direct": round(d1, 4),
            "d2_indirect": round(d2, 4),
            "goal_directed_signal": round(goal, 4),
            "action_outcome_value": round(ao_value, 4),
            "gpi_drive": round(gpi, 4),
            "arbitration_with_dls": round(arbitration, 4),
            "dms_state": state,
        }

    def _flexibility_index(self) -> float:
        """How much DMS retains flexible control (Yin 2005)."""
        return float(self.state.get("arbitration_with_dls", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("dms_drive", 0.0),
            "goal": self.state.get("goal_directed_signal", 0.0),
            "ao_value": self.state.get("action_outcome_value", 0.0),
            "arbitration": self.state.get("arbitration_with_dls", 0.0),
            "state": self.state.get("dms_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent:
            return self.state.get('dms_state', "quiet") if 'dms_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('dms_drive', 0.0)) if 'dms_drive' else 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "drive": self.state.get('dms_drive', 0.0) if 'dms_drive' else 0.0,
            "state": self.state.get('dms_state', "quiet") if 'dms_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

