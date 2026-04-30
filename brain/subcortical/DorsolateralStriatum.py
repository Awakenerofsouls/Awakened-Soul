"""
DorsolateralStriatum — DLS / Habit / Sensorimotor Striatum

NEURAL SUBSTRATE
================
The dorsolateral striatum (DLS, putamen analog in primates) is the
sensorimotor subdivision of dorsal striatum. DLS receives M1 + S1
cortical input plus intralaminar thalamic input (CMPf), and is
selectively engaged in stimulus-response (S-R) habit learning.
Distinct from DMS (goal-directed action-outcome), DLS encodes the
overlearned sensorimotor mappings that become habits with extended
training.

Yin & Knowlton 2006 review distilled the dorsal striatum dichotomy:
DMS for action-outcome (goal-directed) learning early in training,
DLS for stimulus-response (habit) learning after extended training.
The transition from goal-directed to habitual control is mediated by
DA-dependent plasticity at corticostriatal synapses, with SNc DA
preferentially gating DLS plasticity.

Cell architecture: ~95% medium spiny neurons (MSNs), ~5% interneurons.
MSNs split ~50/50 into D1+ direct-pathway (action-promoting) and D2+
indirect-pathway (action-suppressing). Both pathways must be balanced
for normal action selection (Kravitz 2010). Cholinergic interneurons
(TANs) provide a "reset" signal that pauses pathway selection.

Graybiel 2008 showed DLS forms "task brackets" — neurons fire at the
beginning and end of a habit sequence, framing the entire sequence as
a single executable unit. This chunking is the neural correlate of
automaticity.

KEY FINDINGS
============
1. Dorsal striatum dichotomy: DMS for action-outcome (goal-directed), DLS for stimulus-response (habit) — [Yin HH 2006, Nat Rev Neurosci 7:464, doi:10.1038/nrn1919]
2. Habit formation requires DLS; lesion before extended training prevents habit transition — [Yin HH 2004, Eur J Neurosci 19:181, doi:10.1111/j.1460-9568.2004.03095.x]
3. DLS forms "task bracket" neural patterns marking habit sequence start/end; chunking signature — [Graybiel AM 2008, Annu Rev Neurosci 31:359, doi:10.1146/annurev.neuro.29.051605.112851]
4. D1 direct vs D2 indirect MSN pathways have opposing effects on action; balanced for normal selection — [Kravitz AV 2010, Nature 466:622, doi:10.1038/nature09159]
5. SNc DA preferentially gates DLS plasticity; DA-dependent corticostriatal LTP/LTD — [Smith Y 2013, Trends Neurosci 36:711, doi:10.1016/j.tins.2013.09.003]

INPUTS
======
- PrimaryMotorCortex.m1_drive (or its proxy)
- PrimarySomatosensoryCortex.s1_drive
- CentromedianParafascicular.cmpf_drive — intralaminar thalamic
- SubstantiaNigraCompacta.da_release_dls
- ValenceTagger.valence_intensity (outcome signal for plasticity)

OUTPUTS
=======
- dls_drive (0-1)
- d1_direct (0-1) — action-promoting pathway
- d2_indirect (0-1) — action-suppressing pathway
- habit_strength_signal (0-1) — slow accumulator
- gpi_drive (0-1) — direct pathway → GPi (D1 inhibits)
- task_bracket_signal (0-1) — sequence start/end marker
- dls_state (str): "habit_executing" | "S-R_active" | "exploring" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class DorsolateralStriatum(BrainMechanism):
    """DLS — sensorimotor striatum / habit substrate."""

    BASELINE = 0.10
    SMOOTH = 0.20
    HABIT_THRESHOLD = 0.40
    HABIT_LEARN_RATE = 0.008  # slow accumulation across many trials

    def __init__(self):
        super().__init__(
            name="DorsolateralStriatum",
            human_analog="Dorsolateral striatum (habit/sensorimotor)",
            layer="subcortical",
        )
        self.state.setdefault("dls_drive", self.BASELINE)
        self.state.setdefault("d1_direct", 0.0)
        self.state.setdefault("d2_indirect", 0.0)
        self.state.setdefault("habit_strength_signal", 0.0)
        self.state.setdefault("gpi_drive", 0.0)
        self.state.setdefault("task_bracket_signal", 0.0)
        self.state.setdefault("dls_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("prev_drive", self.BASELINE)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, m1: float, s1: float, cmpf: float,
                       da: float) -> float:
        """DLS drive — sensorimotor cortex pooled with intralaminar."""
        target = (self.BASELINE + m1 * 0.35 + s1 * 0.25
                    + cmpf * 0.15 + da * 0.10)
        return min(1.0, target)

    def _d1_direct(self, drive: float, da: float) -> float:
        """D1+ MSNs — action-promoting; DA boosts firing (Kravitz 2010)."""
        return min(1.0, drive * 0.5 + da * 0.5)

    def _d2_indirect(self, drive: float, da: float) -> float:
        """D2+ MSNs — action-suppressing; DA suppresses firing (Kravitz 2010)."""
        # High DA → D2 suppressed; low DA → D2 active
        return min(1.0, drive * 0.5 + max(0.0, 0.5 - da) * 0.6)

    def _habit_strength(self, prev: float, drive: float,
                          intensity: float) -> float:
        """Habit accumulator — grows slowly with sustained drive +
        outcome (Yin 2004 extended training requirement)."""
        if drive < 0.30:
            return prev * 0.999  # very slow decay (habits are sticky)
        learn_step = self.HABIT_LEARN_RATE * (drive + intensity * 0.5)
        return min(1.0, prev + learn_step)

    def _gpi_drive(self, d1: float) -> float:
        """D1 direct pathway → GPi inhibition (gates thalamus)."""
        return min(1.0, d1 * 0.85)

    def _task_bracket(self, drive: float, prev_drive: float,
                       habit: float) -> float:
        """Task-bracket marker — fires at sequence transitions
        (Graybiel 2008). Detected as drive change + high habit strength."""
        delta = abs(drive - prev_drive)
        if habit < 0.20:
            return 0.0
        return min(1.0, delta * 1.5 * habit)

    def _classify_state(self, drive: float, habit: float,
                          bracket: float) -> str:
        if drive < 0.20:
            return "quiet"
        if habit > self.HABIT_THRESHOLD and bracket > 0.20:
            return "habit_executing"
        if habit > self.HABIT_THRESHOLD:
            return "S-R_active"
        return "exploring"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        m1_data = prior.get("PrimaryMotorCortex", {})
        m1 = float(m1_data.get("m1_drive",
                          m1_data.get("motor_drive", 0.0)))

        s1_data = prior.get("PrimarySomatosensoryCortex", {})
        s1 = float(s1_data.get("s1_drive",
                          s1_data.get("somatosensory_drive", 0.0)))

        cmpf_data = prior.get("CentromedianParafascicular", {})
        cmpf = float(cmpf_data.get("cmpf_drive",
                            cmpf_data.get("intralaminar_drive", 0.0)))

        snc_data = prior.get("SubstantiaNigraCompacta", {})
        da = float(snc_data.get("da_release_dls",
                          snc_data.get("snc_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))

        target = self._drive_target(m1, s1, cmpf, da)
        prev_drive = float(self.state.get("dls_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        d1 = self._d1_direct(new_drive, da)
        d2 = self._d2_indirect(new_drive, da)
        prev_habit = float(self.state.get("habit_strength_signal", 0.0))
        habit = self._habit_strength(prev_habit, new_drive, intensity)
        gpi = self._gpi_drive(d1)
        bracket = self._task_bracket(new_drive, prev_drive, habit)

        state = self._classify_state(new_drive, habit, bracket)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["dls_drive"] = round(new_drive, 4)
        self.state["d1_direct"] = round(d1, 4)
        self.state["d2_indirect"] = round(d2, 4)
        self.state["habit_strength_signal"] = round(habit, 4)
        self.state["gpi_drive"] = round(gpi, 4)
        self.state["task_bracket_signal"] = round(bracket, 4)
        self.state["dls_state"] = state
        self.state["recent_states"] = recent
        self.state["prev_drive"] = round(new_drive, 4)
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "dls_drive": round(new_drive, 4),
            "d1_direct": round(d1, 4),
            "d2_indirect": round(d2, 4),
            "habit_strength_signal": round(habit, 4),
            "gpi_drive": round(gpi, 4),
            "task_bracket_signal": round(bracket, 4),
            "dls_state": state,
        }

    def _automaticity_index(self) -> float:
        """How automated current behavior is (Graybiel 2008)."""
        return float(self.state.get("habit_strength_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("dls_drive", 0.0),
            "habit": self.state.get("habit_strength_signal", 0.0),
            "d1": self.state.get("d1_direct", 0.0),
            "d2": self.state.get("d2_indirect", 0.0),
            "state": self.state.get("dls_state", "quiet"),
        }
