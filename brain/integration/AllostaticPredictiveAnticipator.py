"""
AllostaticPredictiveAnticipator — Predictive Allostasis / Anticipatory Regulation

NEURAL SUBSTRATE
================
Allostasis (Sterling & Eyer 1988; Sterling 2012) is the brain's
predictive regulation of physiology — adjusting bodily setpoints
ANTICIPATORILY based on expected demands rather than reactively
responding to deviations from a fixed setpoint (homeostasis). The
neural substrate involves the agranular insula + ACC + amygdala +
hypothalamus + brainstem, integrated with prefrontal predictive
coding.

The functional account (Barrett 2017; Kleckner 2017): the brain runs a
generative model of body state, predicts upcoming visceral demands
from current behavioral context, and pre-emptively adjusts hormones,
sympathetic tone, and metabolic preparation to meet those demands.
Prediction errors between expected and actual interoceptive signals
get propagated up through the visceromotor cortex (mid + posterior
insula) to update the model.

Allostatic regulation is computationally a Bayesian filter over
visceral state: prior (predicted state) + likelihood (current
interoception) → posterior (best guess) + correction (action).
Chronic prediction errors that the system can't resolve produce
"allostatic load" — the wear-and-tear from sustained correction
attempts (McEwen 1998).

KEY FINDINGS
============
1. Allostasis: anticipatory adjustment of physiology rather than
   reactive homeostasis; predictive regulation —
   [Sterling P 2012, Physiol Behav 106:5, doi:10.1016/j.physbeh.2011.06.004]
2. Brain runs a generative model of body state; visceromotor cortex
   predicts and corrects interoceptive signals —
   [Barrett LF 2017, Nat Rev Neurosci 18:419, doi:10.1038/nrn.2017.65]
3. Allostatic load: cumulative wear from chronic regulatory failure;
   contributes to disease — [McEwen BS 1998, N Engl J Med 338:171, doi:10.1056/NEJM199801153380307]
4. Visceromotor cortex predicts interoceptive sensations; mid-insular
   prediction errors update homeostatic priors —
   [Kleckner IR 2017, Nat Hum Behav 1:0069, doi:10.1038/s41562-017-0069]
5. Chronic stress + allostatic overload alter hippocampal + amygdala
   structure; mediated by sustained glucocorticoid load —
   [McEwen BS 2007, Physiol Rev 87:873, doi:10.1152/physrev.00041.2006]

INPUTS (from prior_results)
============================
- ParaventricularNucleusHypothalamus.gr_feedback_load (cortisol load)
- InsulaAnterior.aic_drive (interoception integrator)
- InsulaPosterior.posterior_insula_drive (raw interoception)
- VitalCoreRegulator.vital_drive
- ValenceTagger.aversive_signal, .valence_intensity
- ArcuateAgRP.feeding_motivation (energy demand)
- CircadianTimer.circadian_phase (anticipated demand profile)

OUTPUTS (to brain_runner enrichment)
=====================================
- predicted_demand (0-1) — anticipated regulatory demand
- prediction_error (-1 to 1) — actual minus predicted
- anticipatory_adjustment (0-1) — pre-emptive correction signal
- allostatic_load (0-1) — accumulated unresolved error
- regulatory_state (str): "anticipating" | "correcting" |
  "overloaded" | "stable" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AllostaticPredictiveAnticipator(BrainMechanism):
    """Predictive allostasis — anticipatory visceral regulation."""

    BASELINE = 0.10
    SMOOTH = 0.18
    OVERLOAD_THRESHOLD = 0.55
    LOAD_BUILD_RATE = 0.012
    LOAD_RECOVERY_RATE = 0.008

    def __init__(self):
        super().__init__(
            name="AllostaticPredictiveAnticipatorVariant",
            human_analog="Predictive allostasis (Sterling 2012, Barrett 2017)",
            layer="integration",
        )
        self.state.setdefault("predicted_demand", 0.0)
        self.state.setdefault("prediction_error", 0.0)
        self.state.setdefault("anticipatory_adjustment", 0.0)
        self.state.setdefault("allostatic_load", 0.0)
        self.state.setdefault("regulatory_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("expected_baseline", 0.5)
        self.state.setdefault("tick_count", 0)

    def _circadian_demand_curve(self, phase: float) -> float:
        """Expected metabolic/regulatory demand follows circadian profile.
        Peak demand ~midday (phase 0.5), low overnight (phase 0)."""
        # Sinusoidal demand: high at noon, low at midnight
        import math
        return 0.30 + 0.30 * math.sin((phase - 0.25) * 2 * math.pi)

    def _predicted_demand(self, circadian: float, feeding_drive: float,
                            valence_intensity: float) -> float:
        """Anticipated demand combining circadian profile, energy state,
        and current emotional load (any of these forecast upcoming
        regulatory cost)."""
        return min(1.0, circadian * 0.4 + feeding_drive * 0.3
                      + valence_intensity * 0.3)

    def _prediction_error(self, predicted: float, actual: float) -> float:
        """Signed error: actual minus predicted. Positive = under-predicted
        (system surprised by demand). Negative = over-predicted (system
        prepared for nothing)."""
        return max(-1.0, min(1.0, actual - predicted))

    def _anticipatory_adjustment(self, predicted: float,
                                    pe_history: float) -> float:
        """Pre-emptive correction — driven by predicted demand and biased
        by recent prediction-error history. If recent errors say we keep
        underestimating, anticipate higher this time."""
        return min(1.0, predicted * 0.7 + max(0.0, pe_history) * 0.3)

    def _update_allostatic_load(self, prev_load: float,
                                   pe: float) -> float:
        """Allostatic load accumulates when prediction errors are large
        and unresolved (McEwen 1998). Recovers slowly during stable
        prediction."""
        abs_pe = abs(pe)
        if abs_pe > 0.30:
            # Significant error — wear accumulates
            return min(1.0, prev_load + abs_pe * self.LOAD_BUILD_RATE)
        # Small/no error — slow recovery
        return max(0.0, prev_load - self.LOAD_RECOVERY_RATE)

    def _classify_state(self, predicted: float, pe: float,
                          load: float, anticipation: float) -> str:
        if predicted < 0.10 and abs(pe) < 0.10:
            return "quiet"
        if load > self.OVERLOAD_THRESHOLD:
            return "overloaded"
        if abs(pe) > 0.30:
            return "correcting"
        if anticipation > 0.30:
            return "anticipating"
        return "stable"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        circadian_data = prior.get("CircadianTimer", {})
        circadian_phase = float(circadian_data.get("circadian_phase", 0.5))
        circadian_demand = self._circadian_demand_curve(circadian_phase)

        agrp_data = prior.get("ArcuateAgRP", {})
        feeding = float(agrp_data.get("feeding_motivation",
                              agrp_data.get("agrp_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))

        # ACTUAL current demand — sum of interoceptive + visceral signals
        aic_data = prior.get("InsulaAnterior", {})
        aic = float(aic_data.get("aic_drive", 0.0))
        post_insula = prior.get("InsulaPosterior", {})
        pi = float(post_insula.get("posterior_insula_drive",
                            post_insula.get("aic_drive", 0.0)))
        pvn_data = prior.get("ParaventricularNucleusHypothalamus", {})
        gr_load = float(pvn_data.get("gr_feedback_load", 0.0))

        actual_demand = min(1.0, aic * 0.35 + pi * 0.30
                                + gr_load * 0.20 + intensity * 0.15)

        predicted = self._predicted_demand(circadian_demand, feeding,
                                              intensity)
        # If no interoceptive sources reported anything, the brain hasn't
        # received a contradicting actual-demand signal — Sterling 2012's
        # predictive regulation falls through to the predicted value
        # rather than treating absence as a zero-demand mismatch.
        no_actual = (aic == 0.0 and pi == 0.0 and gr_load == 0.0
                     and not prior.get("InsulaAnterior")
                     and not prior.get("InsulaPosterior")
                     and not prior.get("ParaventricularNucleusHypothalamus"))
        if no_actual:
            actual_demand = predicted
        pe = self._prediction_error(predicted, actual_demand)

        prev_pe = float(self.state.get("prediction_error", 0.0))
        # Smoothed prediction-error history for the anticipatory term
        pe_smoothed = prev_pe * 0.8 + pe * 0.2

        anticipation = self._anticipatory_adjustment(predicted, pe_smoothed)

        prev_load = float(self.state.get("allostatic_load", 0.0))
        load = self._update_allostatic_load(prev_load, pe)

        state = self._classify_state(predicted, pe, load, anticipation)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        # Smoothed predicted_demand for output stability
        prev_pred = float(self.state.get("predicted_demand", 0.0))
        smoothed_pred = self._smooth(prev_pred, predicted)

        self.state["predicted_demand"] = round(smoothed_pred, 4)
        self.state["prediction_error"] = round(pe, 4)
        self.state["anticipatory_adjustment"] = round(anticipation, 4)
        self.state["allostatic_load"] = round(load, 4)
        self.state["regulatory_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "predicted_demand": round(smoothed_pred, 4),
            "prediction_error": round(pe, 4),
            "anticipatory_adjustment": round(anticipation, 4),
            "allostatic_load": round(load, 4),
            "regulatory_state": state,
        }

    def _wear_index(self, recent_states: list) -> float:
        """Sustained overload = wear (McEwen 2007 chronic-stress signature)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        overload = sum(1 for s in win if s == "overloaded")
        return overload / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "predicted": self.state.get("predicted_demand", 0.0),
            "pe": self.state.get("prediction_error", 0.0),
            "anticipation": self.state.get("anticipatory_adjustment", 0.0),
            "load": self.state.get("allostatic_load", 0.0),
            "state": self.state.get("regulatory_state", "quiet"),
        }
