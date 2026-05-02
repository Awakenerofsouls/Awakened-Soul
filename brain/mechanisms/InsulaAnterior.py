"""
InsulaAnterior -- AIC / Interoception + Salience + Emotional Awareness

NEURAL SUBSTRATE
================
Anterior insular cortex (AIC) is the principal substrate for interoceptive
awareness -- Craig 2002 framework "the sense of the physiological condition
of the body". AIC integrates visceral/autonomic signals from posterior
insula (PIC) into conscious feelings and emotional awareness.

Three-tier interoceptive hierarchy (Craig 2009):
1. Posterior insula -- primary interoceptive cortex (raw visceral)
2. Mid-insula -- re-representation
3. Anterior insula -- meta-representation, conscious awareness

AIC is part of the salience network (with dACC). Activates during
emotional events, uncertainty, novelty, salience detection.

Critchley 2004 demonstrated AIC activation correlates with heartbeat
detection accuracy -- direct interoceptive accuracy proxy.

KEY FINDINGS
============
1. Interoception is the "sense of the physiological condition of the
   body" represented in insular cortex; AIC = meta-representation --
   [Craig 2002, Nat Rev Neurosci 3:655, doi:10.1038/nrn894]
2. Anterior insula re-represents interoception for conscious awareness;
   foundation for subjective feelings + self-awareness --
   [Craig 2009, Nat Rev Neurosci 10:59, doi:10.1038/nrn2555]
3. AIC activation correlates with heartbeat detection accuracy --
   direct interoceptive-accuracy substrate -- [Critchley 2004,
   Nat Neurosci 7:189, doi:10.1038/nn1176]
4. AIC + dACC form the salience network; reorienting to behaviorally
   relevant stimuli -- [Seeley 2007, J Neurosci 27:2349,
   doi:10.1523/JNEUROSCI.5587-06.2007]
5. AIC encodes uncertainty + risk; activates for ambiguous outcomes --
   [Singer 2009, Trends Cogn Sci 13:334, doi:10.1016/j.tics.2009.05.001]

INPUTS
======
- InsulaPosterior.pic_drive (interoceptive raw)
- ParabrachialTasteVisceral.parabrachial_signal (visceral relay)
- ValenceTagger.valence_intensity, .valence_sign
- CingulateAnterior.acc_drive (salience network co-activation)
- LocusCoeruleusCore.lc_phasic_burst (salience/uncertainty)

OUTPUTS
=======
- aic_drive (0-1)
- interoceptive_awareness (0-1)
- emotional_awareness (0-1)
- salience_signal (0-1)
- uncertainty_signal (0-1)
- aic_state (str): "interoceptive_aware" | "emotional_aware" |
  "salience_active" | "uncertainty" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class InsulaAnterior(BrainMechanism):
    """AIC -- interoception + salience + emotional awareness hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AWARENESS_THRESHOLD = 0.40
    SALIENCE_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="InsulaAnterior",
            human_analog="Anterior insula (interoception + salience)",
            layer="limbic",
        )
        self.state.setdefault("aic_drive", self.BASELINE)
        self.state.setdefault("interoceptive_awareness", 0.0)
        self.state.setdefault("emotional_awareness", 0.0)
        self.state.setdefault("salience_signal", 0.0)
        self.state.setdefault("uncertainty_signal", 0.0)
        self.state.setdefault("aic_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, pic: float, parabrachial: float, valence: float,
                       acc: float, lc_phasic: float) -> float:
        """AIC firing -- re-represents PIC interoception with salience+arousal."""
        target = self.BASELINE + pic * 0.30 + parabrachial * 0.20
        target += valence * 0.20 + acc * 0.15 + lc_phasic * 0.15
        return min(1.0, target)

    def _interoceptive_awareness(self, pic: float, drive: float) -> float:
        """Interoceptive awareness -- AIC re-representation (Craig 2009)."""
        if pic < 0.10:
            return 0.0
        return min(1.0, drive * 0.5 + pic * 0.5)

    def _emotional_awareness(self, valence_intensity: float, drive: float) -> float:
        """Emotional awareness -- conscious recognition of emotion (Craig 2002)."""
        if valence_intensity < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + valence_intensity * 0.6)

    def _salience_signal(self, drive: float, acc: float,
                          lc_phasic: float) -> float:
        """Salience network signal (Seeley 2007)."""
        return min(1.0, drive * 0.4 + acc * 0.3 + lc_phasic * 0.3)

    def _uncertainty_signal(self, valence_intensity: float, valence_sign: int,
                              drive: float) -> float:
        """Uncertainty signal -- high when valence ambiguous (Singer 2009)."""
        # Ambiguous when intensity is moderate but sign is 0 (mixed)
        if valence_sign != 0:
            return 0.0
        if valence_intensity < 0.30:
            return 0.0
        return min(1.0, drive * 0.5 + valence_intensity * 0.5)

    def _classify_state(self, intero: float, emotional: float, salience: float,
                          uncertainty: float) -> str:
        if uncertainty > 0.30:
            return "uncertainty"
        if salience > self.SALIENCE_THRESHOLD:
            return "salience_active"
        if emotional > self.AWARENESS_THRESHOLD:
            return "emotional_aware"
        if intero > self.AWARENESS_THRESHOLD:
            return "interoceptive_aware"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pic_data = prior.get("InsulaPosterior", {})
        pic = float(pic_data.get("pic_drive", 0.0))

        pb_data = prior.get("ParabrachialTasteVisceral", {})
        parabrachial = float(pb_data.get("parabrachial_signal",
                                pb_data.get("pb_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        valence_sign = int(valence.get("valence_sign", 0))

        acc_data = prior.get("CingulateAnterior", {})
        acc = float(acc_data.get("acc_drive", 0.0))

        lc_data = prior.get("LocusCoeruleusCore", {})
        lc_phasic = float(lc_data.get("lc_phasic_burst", 0.0))

        target = self._drive_target(pic, parabrachial, valence_intensity,
                                     acc, lc_phasic)
        prev_drive = float(self.state.get("aic_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        intero = self._interoceptive_awareness(pic, new_drive)
        emotional = self._emotional_awareness(valence_intensity, new_drive)
        salience = self._salience_signal(new_drive, acc, lc_phasic)
        uncertainty = self._uncertainty_signal(valence_intensity, valence_sign,
                                                  new_drive)

        state = self._classify_state(intero, emotional, salience, uncertainty)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["aic_drive"] = round(new_drive, 4)
        self.state["interoceptive_awareness"] = round(intero, 4)
        self.state["emotional_awareness"] = round(emotional, 4)
        self.state["salience_signal"] = round(salience, 4)
        self.state["uncertainty_signal"] = round(uncertainty, 4)
        self.state["aic_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "aic_drive": round(new_drive, 4),
            "interoceptive_awareness": round(intero, 4),
            "emotional_awareness": round(emotional, 4),
            "salience_signal": round(salience, 4),
            "uncertainty_signal": round(uncertainty, 4),
            "aic_state": state,
        }

    def _heartbeat_detection_proxy(self, pic: float, drive: float) -> float:
        """Critchley 2004: AIC activation correlates with heartbeat detection."""
        return min(1.0, pic * 0.5 + drive * 0.5)

    def _gastric_signal_integration(self, pic: float,
                                        intero: float,
                                        emotional: float) -> float:
        """Gastric signal integration -- AIC integrates gut-level
        interoceptive signals with emotional awareness. High
        stomach activity + emotional awareness = gut feeling signal."""
        if pic < 0.20 or intero < 0.20:
            return 0.0
        return min(1.0, pic * intero * 0.8 + emotional * 0.2)

    def _empathy_prediction(self, emotional: float,
                            intero: float) -> float:
        """Empathy prediction -- AIC activity during observation
        of others' emotional states (Singer 2009 fMRI studies).
        Returns simulated interoceptive prediction strength."""
        if emotional < 0.20:
            return 0.0
        return min(1.0, emotional * intero * 1.2)

    def _decision_confidence(self, intero: float,
                             uncertainty: float) -> float:
        """Decision confidence -- AIC uncertainty signal modulates
        confidence in interoceptive decisions. High uncertainty
        reduces confidence even with strong interoceptive signal."""
        if intero < 0.20:
            return 0.0
        confidence = intero * (1.0 - uncertainty)
        return max(0.0, min(1.0, confidence))


    def _visceral_memory_trace(self, intero: float,
                               emotional: float) -> float:
        """Visceral memory trace -- emotional memories with
        strong interoceptive components are particularly
        durable. AIC stores these as body-state memories."""
        if intero < 0.20:
            return 0.0
        return min(1.0, intero * emotional * 1.4)

    def _risk_prediction_signal(self, uncertainty: float,
                               intero: float) -> float:
        """Risk prediction signal -- AIC integrates uncertainty
        with interoceptive state to predict bodily risk.
        High uncertainty + high arousal = elevated risk signal."""
        if uncertainty < 0.20:
            return 0.0
        return min(1.0, uncertainty * intero * 1.3)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("aic_drive", 0.0),
            "intero": self.state.get("interoceptive_awareness", 0.0),
            "emotional": self.state.get("emotional_awareness", 0.0),
            "state": self.state.get("aic_state", "quiet"),
        }
