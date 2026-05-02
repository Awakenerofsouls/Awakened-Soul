"""
brain/integration/Integration025CerebellarCorticalPredictiveLoop.py
Cerebellar-Cortical Predictive Loop — Universal Transform for Error-Based Prediction Refinement

ANATOMY (Ito 2008; Ramnani 2006; Diedrichsen 2019; Schmahmann 2019):
    The cerebellum contains the neural circuitry for internal models —
    predictive simulations that generate expected sensory/motivational
    consequences of actions or states, compare them against actual signals,
    and output refined predictions.

    Canonical circuit (Marr-Alam-Jung model):
    Mossy fibers → Granule cells → Parallel fibers → Purkinje cells → Deep nuclei → output
    Climbing fibers (from inferior olive) carry error signals that teach the Purkinje cells
    through long-term depression (LTD) at parallel fiber → Purkinje synapses.

    Cortico-cerebellar loops (Ramnani 2006):
    - Primary motor cortex → pontine nuclei → cerebellum (input)
    - Cerebellum → thalamus → motor/premotor cortex (output)
    - Non-motor loops: prefrontal, parietal, temporal cortex also connect via pontine nuclei
    - This means cerebellar error correction applies across all cortical domains

    Universal Cerebellar Transform (Diedrichsen 2019):
    The same computational operation — error-based prediction refinement —
    is applied across all cortical domains. The cerebellum doesn't "understand"
    what it's predicting; it just applies the same learning rule to whatever
    prediction signal arrives.

    Cerebellar Cognitive Affective Syndrome (Schmahmann 2019):
    Lesions to the cerebellum produce deficits in: executive function, spatial
    cognition, linguistic processing, emotional regulation — confirming the
    cerebellar transform applies to non-motor domains.

KEY FINDINGS:
    1. Ito 2008 (PMID 18567940): "Control of mental activities by internal models
       in the cerebellum" — foundational forward-model paper
    2. Ramnani 2006 (PMID 16924257): "The primate cortico-cerebellar system" —
       anatomy of non-motor cortical-cerebellar loops
    3. Sokolov et al. 2017 (PMID 28765005): "Adaptive prediction for movement and
       cognition" — cerebellum as adaptive prediction system
    4. Schmahmann 2019 (PMID 30853531): "The cerebellum and cognition" —
       cerebellar cognitive affective syndrome, non-motor domains
    5. Diedrichsen et al. 2019 (PMID 31439098): "Universal transform or multiple
       functionalities" — argues one cerebellar computation across all domains

AGENT'S MAPPING:
    cerebellar_prediction_refined: dict — per-source refined predictions
    prediction_error_signal: float 0-1 — total normalized prediction error
    forward_model_confidence: float 0-1 — model quality (accuracy + stability), dampened on cold-start
    error_signal_strength: float 0-1 — raw error magnitude
    domains_processed: int — how many sources were refined this tick
    warm_sources: int — how many sources had prior forward models (vs cold-start)
    warm_fraction: float 0-1 — fraction of sources that are warm (vs first-seen)

CITATIONS:
    PMID 18567940 — Ito (2008). Control of mental activities by internal models. Ann N Y Acad Sci.
    PMID 16924257 — Ramnani (2006). Primate cortico-cerebellar system. Nat Rev Neurosci.
    PMID 28765005 — Sokolov et al. (2017). Adaptive prediction for movement and cognition. Prog Neurobiol.
    PMID 30853531 — Schmahmann (2019). The cerebellum and cognition. Neurosci Lett.
    PMID 31439098 — Diedrichsen et al. (2019). Universal transform or multiple functionalities? PNAS.


CITATIONS
---------
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive]
"""

from brain.base_mechanism import BrainMechanism


class CerebellarCorticalPredictiveLoop(BrainMechanism):
    """
    Cerebellar-cortical predictive loop — universal transform.

    Applies error-based prediction refinement (Diedrichsen's universal transform)
    across all cortical prediction signals. Reads from prior_results, maintains
    forward models in self.state, outputs refined predictions and error signals.

    Cold-start behavior: first encounter of a source produces error=0 (no prior
    model), confidence dampened by warm_fraction. Downstream consumers should
    check warm_fraction to know whether error/confidence are from tested models
    or cold-start zeros.

    State bounded to live sources via stale-key pruning (100-tick window).
    """

    # Learning rate for forward-model update toward actual signal
    LEARNING_RATE = 0.15

    # Ticks before a source with no predictions is considered stale
    STALE_THRESHOLD = 100

    # Default weight for proxy prediction sources (vs explicit predictions at 0.5)
    PROXY_WEIGHT = 0.4

    def __init__(self):
        super().__init__(
            name="CerebellarCorticalPredictiveLoop",
            human_analog="Cerebellum — universal transform, error-based prediction refinement",
            layer="integration",
        )
        self.state.setdefault("error_variance", 0.0)
        self.state.setdefault("last_error", None)  # None = first tick sentinel
        self.state.setdefault("signal_count", 0)
        self.state.setdefault("tick_count", 0)
        # Forward models: expected_<source> for each live prediction source
        # Pruned to bounded set via stale-key cleanup
        self.state.setdefault("_last_seen", {})  # source -> last tick seen

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Tick count incremented at top so all uses are consistent
        self.state["tick_count"] = self.state.get("tick_count", 0) + 1
        tick_count = self.state["tick_count"]

        prediction_signals = []

        # === Always-on sources ===

        # 1. Explicit prediction signals from any mechanism that emits them
        for mech_name, mech_output in prior.items():
            if isinstance(mech_output, dict) and "prediction" in mech_output:
                prediction_signals.append({
                    "source": mech_name,
                    "signal": mech_output["prediction"],
                    "weight": mech_output.get("prediction_confidence", 0.5),
                })

        # 2. VIF directional tension signals — always included (proxy predictions)
        vif = prior.get("VectorizedIdentityFields", {})
        if isinstance(vif, dict):
            for k, v in vif.items():
                if isinstance(v, dict) and "tension" in v:
                    prediction_signals.append({
                        "source": f"vif_{k}",
                        "signal": v["tension"],
                        "weight": self.PROXY_WEIGHT,
                    })

        # 3. PDS desire strength — always included (proxy prediction)
        pds = prior.get("PreDesireState", {})
        if isinstance(pds, dict) and "desire_strength" in pds:
            prediction_signals.append({
                "source": "pds_desire",
                "signal": pds["desire_strength"],
                "weight": self.PROXY_WEIGHT,
            })

        # === Stale-key pruning ===

        current_sources = {entry["source"] for entry in prediction_signals}
        last_seen = self.state["_last_seen"]

        for src in current_sources:
            last_seen[src] = tick_count

        stale_sources = [
            src for src, last_tick in last_seen.items()
            if tick_count - last_tick >= self.STALE_THRESHOLD
        ]
        for src in stale_sources:
            self.state.pop(f"expected_{src}", None)
            last_seen.pop(src, None)

        # === Forward model computation ===

        total_error = 0.0
        refined_predictions = {}
        warm_sources = 0

        for entry in prediction_signals:
            current_signal = entry["signal"]
            source = entry["source"]
            weight = entry["weight"]
            expected_key = f"expected_{source}"

            is_warm = expected_key in self.state
            expected = self.state.get(expected_key, current_signal)

            error = abs(current_signal - expected)
            total_error += error * weight

            # Count as warm only if we had a prior expected value
            if is_warm:
                warm_sources += 1

            # Error-based learning: update forward model toward actual
            new_expected = expected + self.LEARNING_RATE * (current_signal - expected)
            self.state[expected_key] = round(new_expected, 4)

            refined_predictions[source] = {
                "original": round(current_signal, 4),
                "refined": round(new_expected, 4),
                "error": round(error, 4),
                "is_warm": is_warm,
            }

        # Normalize error across signals
        n_signals = max(1, len(prediction_signals))
        normalized_error = min(1.0, total_error / n_signals)

        # === Confidence = accuracy + stability, dampened on cold-start ===

        last_error = self.state["last_error"]
        if last_error is None:
            # First tick: no prior error to compare, start with zero variance
            smooth_variance = self.state["error_variance"]
        else:
            error_delta = abs(normalized_error - last_error)
            smooth_variance = self.state["error_variance"] * 0.8 + error_delta * 0.2

        error_component = 1.0 - normalized_error
        stability_component = max(0.0, 1.0 - smooth_variance * 2)
        base_confidence = max(0.1, 0.5 * error_component + 0.5 * stability_component)

        warm_fraction = warm_sources / max(1, n_signals)
        # Dampen confidence on cold-start; full confidence only when models are tested
        confidence = base_confidence * (0.3 + 0.7 * warm_fraction)

        # === Persist state ===

        self.state["error_variance"] = round(smooth_variance, 4)
        self.state["last_error"] = normalized_error
        self.state["signal_count"] = n_signals
        self.persist_state()

        return {
            "cerebellar_prediction_refined": refined_predictions,
            "prediction_error_signal": round(normalized_error, 4),
            "forward_model_confidence": round(confidence, 4),
            "error_signal_strength": round(total_error, 4),
            "domains_processed": n_signals,
            "warm_sources": warm_sources,
            "warm_fraction": round(warm_fraction, 4),
            # brain_* enrichments for TSB consumer wiring
            # Named brain_forward_model_error (not brain_prediction_error) to distinguish
            # from Subcortical004 PredictionErrorDrift's dopaminergic reward PE signal (Schultz 1998).
            # Integration025's signal = cerebellar forward-model error via climbing fibers (Ito 2008).
            "brain_forward_model_error": round(normalized_error, 4),
            "brain_forward_model_confidence": round(confidence, 4),
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

