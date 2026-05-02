"""
CingulateAnterior -- ACC / Conflict Monitoring + Pain Affect Hub

NEURAL SUBSTRATE
================
Anterior cingulate cortex (ACC, Brodmann 24/32) is the central node of
cognitive control + conflict monitoring. Distinct subdivisions:
- Dorsal ACC (cognitive subdivision) -- conflict monitoring, error
  detection
- Rostral ACC (emotional subdivision) -- pain affect, emotion regulation,
  default mode

Botvinick 2001 established conflict-monitoring hypothesis: ACC monitors
response conflict and signals need for cognitive control upregulation.
ACC error-related negativity (ERN) appears 50-150ms post-error.

Vogt 2005 mapped four cingulate subregions with distinct functions and
connectivity. ACC pain-affect role: lesions reduce pain unpleasantness
without changing intensity.

KEY FINDINGS
============
1. ACC is the central conflict-monitoring node; signals when response
   conflict requires cognitive control upregulation --
   [Botvinick 2001, Psychol Rev 108:624, doi:10.1037/0033-295X.108.3.624]
2. Cingulate cortex four-region map: subgenual ACC (sgACC, emotion),
   pregenual ACC (pgACC, default mode), midcingulate (cognitive), PCC
   (autobiographical) -- distinct functions --
   [Vogt 2005, Nat Rev Neurosci 6:533, doi:10.1038/nrn1704]
3. ACC error-related negativity (ERN) -- 50-150ms post-error EEG
   signature originating in dACC -- [Holroyd 2002, Psychol Rev 109:679,
   doi:10.1037/0033-295X.109.4.679]
4. ACC lesion reduces pain unpleasantness without changing intensity;
   pain affect substrate distinct from sensory pain --
   [Rainville 1997, Science 277:968, PMID 9252330]
5. ACC neurons encode reward expectation + reward prediction error;
   distinct from VTA dopamine -- [Bush 2002, Proc Natl Acad Sci
   99:523, PMID 11756669]

INPUTS
======
- PrelimbicCortex.conflict_monitoring_signal
- PredictionErrorDrift.rpe_signal
- InsulaAnterior.aic_drive (interoceptive integration)
- ValenceTagger.aversive_signal, .pain_signal
- LocusCoeruleusCore.lc_phasic_burst (error detection)

OUTPUTS
=======
- acc_drive (0-1)
- conflict_signal (0-1)
- error_signal (0-1) -- ERN proxy
- pain_affect_signal (0-1)
- control_upregulation_command (0-1)
- acc_state (str): "conflict" | "error_detected" |
  "pain_affect" | "control_active" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class CingulateAnterior(BrainMechanism):
    """ACC -- conflict monitoring + pain affect + error detection."""

    BASELINE = 0.10
    SMOOTH = 0.20
    CONFLICT_THRESHOLD = 0.40
    ERROR_THRESHOLD = 0.45
    PAIN_AFFECT_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="CingulateAnterior",
            human_analog="Anterior cingulate (conflict + pain affect + error)",
            layer="limbic",
        )
        self.state.setdefault("acc_drive", self.BASELINE)
        self.state.setdefault("conflict_signal", 0.0)
        self.state.setdefault("error_signal", 0.0)
        self.state.setdefault("pain_affect_signal", 0.0)
        self.state.setdefault("control_upregulation_command", 0.0)
        self.state.setdefault("acc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, pl_conflict: float, rpe: float, aic: float,
                       aversive: float, lc_phasic: float) -> float:
        """ACC firing -- conflict + RPE + interoceptive convergence."""
        # ACC fires on negative RPE (errors) more than positive
        target = self.BASELINE + pl_conflict * 0.30
        target += abs(rpe) * 0.25
        target += aic * 0.20 + aversive * 0.15
        target += lc_phasic * 0.15
        return min(1.0, target)

    def _conflict_signal(self, pl_conflict: float, drive: float) -> float:
        """Conflict-monitoring signal (Botvinick 2001)."""
        return min(1.0, pl_conflict * 0.6 + drive * 0.4)

    def _error_signal(self, rpe: float, lc_phasic: float, drive: float) -> float:
        """Error-related signal -- ERN proxy (Holroyd 2002).
        Strong on negative RPE + LC phasic burst.
        """
        if rpe >= 0:
            return 0.0  # No error if RPE positive
        return min(1.0, abs(rpe) * 0.5 + lc_phasic * 0.3 + drive * 0.2)

    def _pain_affect(self, aversive: float, drive: float) -> float:
        """Pain affect (unpleasantness) signal (Rainville 1997)."""
        if aversive < 0.30:
            return 0.0
        return min(1.0, aversive * 0.7 + drive * 0.3)

    def _control_upregulation(self, conflict: float, error: float) -> float:
        """Cognitive control upregulation command (Botvinick 2001).
        Triggered by sustained conflict OR error detection.
        """
        return min(1.0, conflict * 0.5 + error * 0.5)

    def _classify_state(self, conflict: float, error: float,
                          pain: float, control: float) -> str:
        if error > self.ERROR_THRESHOLD:
            return "error_detected"
        if pain > self.PAIN_AFFECT_THRESHOLD:
            return "pain_affect"
        if conflict > self.CONFLICT_THRESHOLD:
            return "conflict"
        if control > 0.30:
            return "control_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pl_data = prior.get("PrelimbicCortex", {})
        pl_conflict = float(pl_data.get("conflict_monitoring_signal", 0.0))

        rpe_data = prior.get("PredictionErrorDrift", {})
        rpe = float(rpe_data.get("rpe_signal", 0.0))

        aic_data = prior.get("InsulaAnterior", {})
        aic = float(aic_data.get("aic_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal",
                            valence.get("pain_signal", 0.0)))

        lc_data = prior.get("LocusCoeruleusCore", {})
        lc_phasic = float(lc_data.get("lc_phasic_burst", 0.0))

        target = self._drive_target(pl_conflict, rpe, aic, aversive, lc_phasic)
        prev_drive = float(self.state.get("acc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        conflict = self._conflict_signal(pl_conflict, new_drive)
        error = self._error_signal(rpe, lc_phasic, new_drive)
        pain = self._pain_affect(aversive, new_drive)
        control = self._control_upregulation(conflict, error)

        state = self._classify_state(conflict, error, pain, control)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["acc_drive"] = round(new_drive, 4)
        self.state["conflict_signal"] = round(conflict, 4)
        self.state["error_signal"] = round(error, 4)
        self.state["pain_affect_signal"] = round(pain, 4)
        self.state["control_upregulation_command"] = round(control, 4)
        self.state["acc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "acc_drive": round(new_drive, 4),
            "conflict_signal": round(conflict, 4),
            "error_signal": round(error, 4),
            "pain_affect_signal": round(pain, 4),
            "control_upregulation_command": round(control, 4),
            "acc_state": state,
        }

    def _ern_amplitude(self, error: float) -> float:
        """Error-related negativity amplitude (Holroyd 2002)."""
        return error * 0.85

    def _action_outcome_prediction(self, error_signal: float,
                                       conflict: float) -> float:
        """Action-outcome prediction strength -- ACC integrates
        outcome predictions with conflict signals. High error + low
        conflict = expected outcome; low error + high conflict =
        prediction error (surprise)."""
        if error_signal < 0.10:
            return 0.0
        return min(1.0, error_signal * (1.0 - conflict) + conflict * 0.3)

    def _autonomic_feedback_integration(self, error: float,
                                        conflict: float) -> float:
        """Autonomic feedback integration -- ACC receives cardiac/
        gastric interoceptive feedback and integrates it with
        cognitive conflict signals (Critchley 2004)."""
        if error < 0.20 and conflict < 0.20:
            return 0.0
        return min(1.0, (error + conflict) * 0.6)

    def _metabolic_cost_estimate(self, conflict: float,
                                  acc_drive: float) -> float:
        """Metabolic cost estimate -- high ACC activity is
        energetically costly. Returns estimated cognitive load."""
        if conflict < 0.20:
            return 0.0
        return min(1.0, conflict * acc_drive * 1.5)


    def _voluntary_control_strength(self, conflict: float,
                                     acc_drive: float) -> float:
        """Voluntary control strength -- ACC can volitionally
        downregulate emotional responses. High drive + moderate
        conflict = capacity for regulation."""
        if acc_drive < 0.20:
            return 0.0
        return min(1.0, acc_drive * (1.0 - conflict * 0.5))

    def _response_inhibition_strength(self, error: float,
                                      conflict: float) -> float:
        """Response inhibition strength -- ACC error signals
        trigger response inhibition. High error + conflict =
        strong stop signal."""
        if error < 0.20:
            return 0.0
        return min(1.0, error * (1.0 + conflict) * 0.6)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("acc_drive", 0.0),
            "conflict": self.state.get("conflict_signal", 0.0),
            "error": self.state.get("error_signal", 0.0),
            "state": self.state.get("acc_state", "quiet"),
        }
