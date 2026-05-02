"""
InteroExteroceptiveMerger — Bayesian Fusion of Body + Environment

NEURAL SUBSTRATE
================
The brain runs two parallel sensory streams that must be merged into a
unified percept of "self in environment":

1. **Interoception** — visceral and bodily afferents arriving via
   spinothalamic lamina I → ventromedial nucleus of thalamus → posterior
   insula. Craig 2002 mapped this stream as the "feeling of the body."
   Posterior insula = raw interoception; mid insula = integrated body
   state; anterior insula = subjective awareness + appraisal.

2. **Exteroception** — visual, auditory, somatosensory environmental
   afferents arriving via thalamocortical sensory pathways into primary
   sensory cortex.

Barrett & Simmons 2015 ("Interoceptive predictions in the brain")
formalized the merger as Bayesian inference: each stream produces a
predicted state + a precision (confidence weight) on that prediction.
The brain combines them in a precision-weighted average, with the
weighting determined by current task demands. Interoception precision
HIGH = "I feel hot" wins. Exteroception precision HIGH = "the room
looks cold" wins.

The arbitration is implemented in vmPFC + OFC + anterior insula + ACC.
When interoceptive precision is chronically too high, the brain
produces somatic delusions / panic disorder (Khalsa 2018). When
exteroceptive precision is chronically too high, the brain becomes
"interoceptive deaf" — alexithymic, dissociated from body.

KEY FINDINGS
============
1. Interoception: foundational sense of the physiological condition of the body via lamina I → insula pathway — [Craig AD 2002, Nat Rev Neurosci 3:655, doi:10.1038/nrn894]
2. Embodied Predictive Interoception Coding: brain runs Bayesian inference combining interoceptive priors with ascending visceral sensations — [Barrett LF 2015, Nat Rev Neurosci 16:419, doi:10.1038/nrn3950]
3. Anterior insula encodes interoceptive attention; selectively activates when subjects attend to bodily signals — [Wang X 2019, eLife 8:e42265, doi:10.7554/eLife.42265]
4. Multimodal anterior insula integrates interoceptive + exteroceptive + cognitive signals into salience — [Craig AD 2009, Nat Rev Neurosci 10:59, doi:10.1038/nrn2555]
5. Interoceptive precision dysregulation underlies anxiety, depression, eating disorders, somatic delusions — [Khalsa SS 2018, Biol Psychiatry Cogn Neurosci Neuroimaging 3:501, doi:10.1016/j.bpsc.2017.12.004]

INPUTS (from prior_results)
============================
- InsulaAnterior.aic_drive (interoceptive integrator)
- InsulaPosterior.posterior_insula_drive (raw interoception)
- PrimaryVisualCortex.v1_drive (exteroception)
- PrimaryAuditoryCortex.a1_drive (exteroception)
- PrimarySomatosensoryCortex.s1_drive (exteroception)
- VentromedialPrefrontalCortex.vmpfc_drive (precision arbiter)
- AllostaticPredictiveAnticipator.prediction_error (interoceptive PE)

OUTPUTS (to brain_runner enrichment)
=====================================
- merged_self_world_percept (0-1)
- interoceptive_stream_strength (0-1)
- exteroceptive_stream_strength (0-1)
- interoceptive_precision (0-1) — confidence weight on body
- exteroceptive_precision (0-1) — confidence weight on environment
- precision_balance (0-1) — 0=intero-dominant, 1=extero-dominant
- merger_state (str): "intero_dominant" | "extero_dominant" |
  "balanced" | "alexithymic" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class InteroExteroceptiveMerger(BrainMechanism):
    """Bayesian merger of interoceptive + exteroceptive streams."""

    BASELINE = 0.0
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="InteroExteroceptiveMergerVariant",
            human_analog="Bayesian intero-exteroceptive fusion (Barrett 2015)",
            layer="integration",
        )
        self.state.setdefault("merged_self_world_percept", 0.0)
        self.state.setdefault("interoceptive_stream_strength", 0.0)
        self.state.setdefault("exteroceptive_stream_strength", 0.0)
        self.state.setdefault("interoceptive_precision", 0.5)
        self.state.setdefault("exteroceptive_precision", 0.5)
        self.state.setdefault("precision_balance", 0.5)
        self.state.setdefault("merger_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _interoceptive_stream(self, aic: float, post_insula: float,
                                  pe: float) -> float:
        """Interoceptive stream amplitude — pooled posterior + anterior
        insula plus prediction error magnitude (Barrett 2015)."""
        return min(1.0, post_insula * 0.4 + aic * 0.4 + abs(pe) * 0.2)

    def _exteroceptive_stream(self, v1: float, a1: float, s1: float) -> float:
        """Exteroceptive stream amplitude."""
        return min(1.0, v1 * 0.4 + a1 * 0.3 + s1 * 0.3)

    def _interoceptive_precision(self, aic: float, vmpfc: float,
                                    intero_strength: float) -> float:
        """Confidence on interoceptive prediction. AIC + vmPFC arbitrate
        precision (Barrett 2015 vmPFC role)."""
        return min(1.0, aic * 0.5 + vmpfc * 0.3 + intero_strength * 0.2)

    def _exteroceptive_precision(self, ext_strength: float,
                                    sensory_count: float) -> float:
        """Confidence on exteroceptive prediction. Multiple modalities
        firing = higher confidence."""
        return min(1.0, ext_strength * 0.6 + sensory_count * 0.3)

    def _precision_balance(self, intero_p: float, extero_p: float) -> float:
        """Bayesian arbitration: 0.0 = full intero, 1.0 = full extero,
        0.5 = balanced."""
        total = intero_p + extero_p
        if total < 0.10:
            return 0.5
        return max(0.0, min(1.0, extero_p / total))

    def _merged_percept(self, intero_strength: float, extero_strength: float,
                          balance: float) -> float:
        """Precision-weighted average of streams."""
        return min(1.0, intero_strength * (1.0 - balance) + extero_strength * balance)

    def _classify_state(self, drive: float, balance: float,
                          intero_strength: float,
                          extero_strength: float) -> str:
        if drive < 0.15:
            return "quiet"
        # Alexithymic: extero-strong but intero-weak even when bodily PE
        # should be present
        if extero_strength > 0.40 and intero_strength < 0.15:
            return "alexithymic"
        if balance < 0.30:
            return "intero_dominant"
        if balance > 0.70:
            return "extero_dominant"
        return "balanced"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        aic_data = prior.get("InsulaAnterior", {})
        aic = float(aic_data.get("aic_drive", 0.0))

        post_data = prior.get("InsulaPosterior", {})
        post_insula = float(post_data.get("posterior_insula_drive",
                                  post_data.get("aic_drive", 0.0)))

        v1_data = prior.get("PrimaryVisualCortex", {})
        v1 = float(v1_data.get("v1_drive", 0.0))

        a1_data = prior.get("PrimaryAuditoryCortex", {})
        a1 = float(a1_data.get("a1_drive", 0.0))

        s1_data = prior.get("PrimarySomatosensoryCortex", {})
        s1 = float(s1_data.get("s1_drive", 0.0))

        vmpfc_data = prior.get("VentromedialPrefrontalCortex", {})
        vmpfc = float(vmpfc_data.get("vmpfc_drive", 0.0))

        allo_data = prior.get("AllostaticPredictiveAnticipator", {})
        pe = float(allo_data.get("prediction_error", 0.0))

        intero_strength = self._interoceptive_stream(aic, post_insula, pe)
        extero_strength = self._exteroceptive_stream(v1, a1, s1)

        # Sensory modality count for extero precision
        active_sensory = sum(1 for s in [v1, a1, s1] if s > 0.20)
        extero_p_signal = active_sensory / 3.0

        intero_p_target = self._interoceptive_precision(aic, vmpfc,
                                                          intero_strength)
        extero_p_target = self._exteroceptive_precision(extero_strength,
                                                          extero_p_signal)

        prev_intero_p = float(self.state.get("interoceptive_precision", 0.5))
        intero_p = self._smooth(prev_intero_p, intero_p_target)
        prev_extero_p = float(self.state.get("exteroceptive_precision", 0.5))
        extero_p = self._smooth(prev_extero_p, extero_p_target)

        balance = self._precision_balance(intero_p, extero_p)
        merged = self._merged_percept(intero_strength, extero_strength,
                                         balance)

        prev_merged = float(self.state.get("merged_self_world_percept", 0.0))
        merged = self._smooth(prev_merged, merged)

        state = self._classify_state(merged, balance, intero_strength,
                                       extero_strength)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["merged_self_world_percept"] = round(merged, 4)
        self.state["interoceptive_stream_strength"] = round(intero_strength, 4)
        self.state["exteroceptive_stream_strength"] = round(extero_strength, 4)
        self.state["interoceptive_precision"] = round(intero_p, 4)
        self.state["exteroceptive_precision"] = round(extero_p, 4)
        self.state["precision_balance"] = round(balance, 4)
        self.state["merger_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "merged_self_world_percept": round(merged, 4),
            "interoceptive_stream_strength": round(intero_strength, 4),
            "exteroceptive_stream_strength": round(extero_strength, 4),
            "interoceptive_precision": round(intero_p, 4),
            "exteroceptive_precision": round(extero_p, 4),
            "precision_balance": round(balance, 4),
            "merger_state": state,
        }

    def _alexithymia_index(self, recent_states: list) -> float:
        """Sustained alexithymic state = body-disconnect signature
        (Khalsa 2018)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        a = sum(1 for s in win if s == "alexithymic")
        return a / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "merged": self.state.get("merged_self_world_percept", 0.0),
            "intero": self.state.get("interoceptive_stream_strength", 0.0),
            "extero": self.state.get("exteroceptive_stream_strength", 0.0),
            "balance": self.state.get("precision_balance", 0.5),
            "state": self.state.get("merger_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
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
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
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

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

