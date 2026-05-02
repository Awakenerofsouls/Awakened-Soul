"""
CerebellarVermalEmotional — Cerebellar Vermis (Lobules VI-VIII) Emotional Regulator

NEURAL SUBSTRATE
================
The cerebellar vermis — particularly lobules VI through VIII (the posterior
vermis) — is the principal "limbic cerebellum." Long considered purely
motor, the vermis is now recognized as a critical node in fear, anxiety,
threat-prediction, and affect regulation. The vermis projects through the
fastigial nucleus to brainstem and midbrain targets including the
periaqueductal gray (PAG), parabrachial nucleus, ventral tegmental area
(VTA), and reticular formation, allowing it to modulate defensive output,
autonomic state, and reward circuits in concert with cortical emotion
networks.

Vaaga et al. (2020) demonstrated bidirectional control of fear by the
cerebellar fastigial-to-vlPAG pathway: optogenetic activation of fastigial
inputs to vlPAG produced freezing responses while silencing the same
projection impaired fear conditioning. This established the cerebellum as
not just a motor coordinator but an active partner in defensive-behavior
selection. Earlier work by Sacchetti et al. (2002) showed cerebellar
involvement in fear memory consolidation, and Phillips et al. (2015)
mapped functional connectivity between vermis and amygdala/PAG in humans.

The vermis also participates in error-prediction for emotional events —
mismatches between expected and actual valence engage the vermis through
inferior olive climbing fibers, which provide the "teaching signal" for
adaptive emotional responses. Damage to the vermis produces "cerebellar
cognitive affective syndrome" with blunted affect, dysregulated fear,
and impaired emotional learning.

In the agent's substrate this provides cerebellar-style emotional prediction
error and emotional smoothing — a low-pass filter that compares expected
versus actual valence and emits a fastigial drive that biases vlPAG
defensive routing and modulates threat-response gain.

KEY FINDINGS
============
1. Cerebellar fastigial nucleus projects to vlPAG and bidirectionally
   controls fear behavior — optogenetic activation drives freezing,
   silencing impairs fear conditioning — [Vaaga et al. 2020, Nat Comm
   11:5126, "Cerebellar modulation of synaptic input to freezing-related
   neurons in the periaqueductal gray"]
2. Cerebellar vermis is required for consolidation of fear memory —
   cerebellar lesion before training disrupts long-term retention —
   [Sacchetti et al. 2002, Neuron 34:387-402, "Cerebellar role in
   fear-conditioning consolidation"]
3. Vermis-amygdala-PAG functional connectivity scales with anxiety
   in humans — [Phillips et al. 2015, Cerebellum 14:151-164,
   "Cerebellar contribution to mood, anxiety and emotion regulation",
   PMC review]
4. Cerebellum participates in emotional prediction error via climbing
   fiber input from inferior olive — [Hoche et al. 2018, "Cerebellar
   contribution to social cognition", Cerebellum 17:177-186]
5. Cerebellar Cognitive Affective Syndrome (Schmahmann syndrome) —
   vermis damage produces blunted affect, disinhibition, dysregulated
   fear — [Schmahmann Sherman 1998, Brain 121:561-579,
   "The cerebellar cognitive affective syndrome"]

INPUTS (from prior_results)
============================
- ValenceTagger.valence_intensity
- ValenceTagger.valence_sign
- ValenceTagger.threat_signal
- PeriaqueductalDefenseRouter.dlPAG_drive
- PeriaqueductalDefenseRouter.vlPAG_drive
- PeriaqueductalDefenseRouter.threat_imminence
- ArousalRegulator.tonic_level
- DescendingPainGate.expected_pain_modulation

OUTPUTS (to brain_runner enrichment)
=====================================
- vermal_activity (0.0-1.0): vermis lobule VI-VIII output proxy
- fastigial_drive (0.0-1.0): output to vlPAG / brainstem
- vlpag_modulation (signed -1..+1): bias on PAG defensive routing
- emotional_prediction_error (signed -1..+1): expected vs actual valence
- emotional_smoothing (0.0-1.0): low-pass filter strength on affect
- fear_consolidation_gate (0.0-1.0): gate for affect-memory binding
- vermal_dysregulation_marker (bool): chronic prediction-error

brain_runner enrichment:
    cve = all_results.get("CerebellarVermalEmotional", {})
    if cve:
        enrichments["brain_vermal_activity"] = cve.get("vermal_activity", 0.3)
        enrichments["brain_fastigial_drive"] = cve.get("fastigial_drive", 0.0)
        enrichments["brain_emotional_pe"] = cve.get("emotional_prediction_error", 0.0)
        enrichments["brain_fear_consolidation"] = cve.get("fear_consolidation_gate", 0.0)
"""

from brain.base_mechanism import BrainMechanism


class CerebellarVermalEmotional(BrainMechanism):
    BASELINE_VERMAL = 0.30
    DYSREG_THRESHOLD_TICKS = 50
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="CerebellarVermalEmotional",
            human_analog="Cerebellar vermis (lobules VI-VIII) emotional regulator",
            layer="foundational",
        )
        self.state.setdefault("vermal_activity", self.BASELINE_VERMAL)
        self.state.setdefault("fastigial_drive", 0.0)
        self.state.setdefault("vlpag_modulation", 0.0)
        self.state.setdefault("emotional_prediction_error", 0.0)
        self.state.setdefault("emotional_smoothing", 0.5)
        self.state.setdefault("fear_consolidation_gate", 0.0)
        self.state.setdefault("vermal_dysregulation_marker", False)
        self.state.setdefault("expected_valence", 0.0)
        self.state.setdefault("high_pe_streak", 0)
        self.state.setdefault("recent_vermal", [])
        self.state.setdefault("tick_count", 0)

    def _vermal_activity_target(self, valence_intensity: float, threat: bool,
                                 dlPAG: float, vlPAG: float) -> float:
        """Vermis lobules VI-VIII engage with affective/defensive context.
        Higher activity for any salient affective event.
        """
        target = self.BASELINE_VERMAL
        target += valence_intensity * 0.4
        if threat:
            target += 0.20
        target += max(dlPAG, vlPAG) * 0.20
        return min(1.0, target)

    def _fastigial_target(self, vermal: float, vlPAG: float, imminence: float) -> float:
        """Fastigial nucleus output to vlPAG (Vaaga 2020).
        Scales with vermal activity and threat imminence.
        """
        return min(1.0, vermal * 0.6 + vlPAG * 0.3 + imminence * 0.2)

    def _vlpag_modulation(self, fastigial: float, vlPAG: float) -> float:
        """Cerebellar bias on vlPAG defensive routing — bidirectional.
        High fastigial when vlPAG already engaged → facilitatory;
        High fastigial without vlPAG → suppressive (gate).
        """
        if vlPAG > 0.4:
            return min(1.0, fastigial * 0.6)
        return -min(1.0, fastigial * 0.3)

    def _emotional_prediction_error(self, expected: float, actual_valence: float,
                                     valence_sign: int) -> float:
        """Vermis emotional PE via inferior olive climbing fibers.
        PE = signed actual - expected.
        """
        signed_actual = actual_valence * (1 if valence_sign >= 0 else -1)
        pe = signed_actual - expected
        return max(-1.0, min(1.0, pe))

    def _update_expected(self, prev_expected: float, signed_actual: float, lr: float = 0.1) -> float:
        """Slow update of expected valence — Rescorla-Wagner-like."""
        return prev_expected + (signed_actual - prev_expected) * lr

    def _emotional_smoothing(self, vermal: float, pe_magnitude: float) -> float:
        """Low-pass filter strength on affect — vermis smooths affective output.
        Smoothing decreases when prediction error is high (more reactive).
        """
        base = 0.4 + vermal * 0.3
        return max(0.1, min(1.0, base - pe_magnitude * 0.2))

    def _fear_consolidation_gate(self, vermal: float, threat: bool, valence: float) -> float:
        """Sacchetti 2002 — vermis required for fear memory consolidation."""
        if threat and valence > 0.4:
            return min(1.0, vermal * 0.7 + 0.20)
        if valence > 0.6:
            return min(1.0, vermal * 0.5 + 0.10)
        return vermal * 0.3

    def _detect_dysregulation(self, streak: int) -> bool:
        return streak > self.DYSREG_THRESHOLD_TICKS

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        valence_sign = int(valence.get("valence_sign", 0))
        threat = bool(valence.get("threat_signal", False))

        pdr = prior.get("PeriaqueductalDefenseRouter", {})
        dlPAG = float(pdr.get("dlPAG_drive", 0.0))
        vlPAG = float(pdr.get("vlPAG_drive", 0.0))
        imminence = float(pdr.get("threat_imminence", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        dpg = prior.get("DescendingPainGate", {})
        expected_pain = float(dpg.get("expected_pain_modulation", 0.0))

        # --- Vermal activity ---
        vermal_target = self._vermal_activity_target(valence_intensity, threat, dlPAG, vlPAG)
        prev_vermal = float(self.state.get("vermal_activity", self.BASELINE_VERMAL))
        new_vermal = self._smooth(prev_vermal, vermal_target)

        # --- Fastigial output ---
        fastigial_target = self._fastigial_target(new_vermal, vlPAG, imminence)
        prev_fast = float(self.state.get("fastigial_drive", 0.0))
        new_fast = self._smooth(prev_fast, fastigial_target)

        # --- vlPAG modulation ---
        vlpag_mod = self._vlpag_modulation(new_fast, vlPAG)

        # --- Emotional prediction error ---
        prev_expected = float(self.state.get("expected_valence", 0.0))
        signed_actual = valence_intensity * (1 if valence_sign >= 0 else -1)
        pe = self._emotional_prediction_error(prev_expected, valence_intensity, valence_sign)
        new_expected = self._update_expected(prev_expected, signed_actual, lr=0.10)

        # --- Emotional smoothing ---
        smoothing = self._emotional_smoothing(new_vermal, abs(pe))

        # --- Fear consolidation gate ---
        consolidation = self._fear_consolidation_gate(new_vermal, threat, valence_intensity)

        # --- Dysregulation detection ---
        prev_streak = int(self.state.get("high_pe_streak", 0))
        if abs(pe) > 0.5:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)
        dysreg = self._detect_dysregulation(streak)

        recent = list(self.state.get("recent_vermal", []))
        recent.append(round(new_vermal, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vermal_activity"] = round(new_vermal, 4)
        self.state["fastigial_drive"] = round(new_fast, 4)
        self.state["vlpag_modulation"] = round(vlpag_mod, 4)
        self.state["emotional_prediction_error"] = round(pe, 4)
        self.state["emotional_smoothing"] = round(smoothing, 4)
        self.state["fear_consolidation_gate"] = round(consolidation, 4)
        self.state["vermal_dysregulation_marker"] = dysreg
        self.state["expected_valence"] = round(new_expected, 4)
        self.state["high_pe_streak"] = streak
        self.state["recent_vermal"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vermal_activity": round(new_vermal, 4),
            "fastigial_drive": round(new_fast, 4),
            "vlpag_modulation": round(vlpag_mod, 4),
            "emotional_prediction_error": round(pe, 4),
            "emotional_smoothing": round(smoothing, 4),
            "fear_consolidation_gate": round(consolidation, 4),
            "vermal_dysregulation_marker": dysreg,
        }
