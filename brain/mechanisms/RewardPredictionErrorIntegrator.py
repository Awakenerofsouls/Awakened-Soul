"""
RewardPredictionErrorIntegrator — Whole-Brain RPE Consolidation

NEURAL SUBSTRATE
================
Reward prediction error (RPE) signals — the difference between predicted
and received reward — are computed by midbrain dopaminergic neurons
(VTA + SNc) and broadcast to widespread targets via dopaminergic
projections. Schultz, Dayan & Montague 1997 established that midbrain
DA neurons signal a temporal-difference RPE: positive bursts on
unexpected reward, no response on predicted reward, pauses on omission.

But RPE isn't just one signal — it's distributed across many dopamine
populations with differing computational properties:
- VTA → NAc shell/core: classic value-based RPE (Cohen 2012)
- SNc → DMS: action-outcome RPE (Hart 2014)
- SNc → DLS: sensorimotor reinforcement RPE (Howe 2013)
- VTA → mPFC: cognitive/attentional RPE (Lammel 2011)

This integrator consolidates RPEs across DA populations into a unified
whole-brain learning signal that:
1. Tracks running expected value across modalities
2. Detects unexpected outcomes (positive or negative)
3. Modulates plasticity at corticostriatal + amygdalar synapses
4. Drives the temporal shift of DA responses from reward time to cue
   time over learning (Amo 2022 — "gradual temporal shift")

KEY FINDINGS
============
1. Midbrain DA neurons signal temporal-difference RPE; phasic burst on positive PE, pause on omission — [Schultz W 1997, Science 275:1593, doi:10.1126/science.275.5306.1593]
2. Optogenetic identification confirms DA neurons encode RPE at single-cell resolution; cross-region heterogeneity — [Cohen JY 2012, Nature 482:85, doi:10.1038/nature10754]
3. Gradual temporal shift of DA responses from reward time to cue time matches TD-learning algorithm prediction — [Amo R 2022, Nat Neurosci 25:1082, doi:10.1038/s41593-022-01109-2]
4. Dopamine signals as temporal difference errors: review of recent advances confirming TD framework — [Watabe-Uchida M 2017, Annu Rev Neurosci 40:373, doi:10.1146/annurev-neuro-072116-031109]
5. Two-component DA RPE signal: rapid value-free salience + slower value-based prediction error component — [Schultz W 2016, Phil Trans R Soc B 372:20160102, doi:10.1098/rstb.2016.0102]

INPUTS (from prior_results)
============================
- VentralTegmentalDopamine.da_release (or da_burst)
- SubstantiaNigraCompacta.snc_drive, .prediction_error
- NucleusAccumbensCore.nacc_drive
- DorsolateralStriatum.dls_drive
- DorsomedialStriatum.dms_drive
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS (to brain_runner enrichment)
=====================================
- integrated_rpe (-1 to 1) — signed unified RPE
- expected_value_trace (0-1) — running expected value
- rpe_burst_detected (bool) — binary positive-RPE burst event
- rpe_omission_detected (bool) — binary omission/pause event
- temporal_shift_progress (0-1) — Amo 2022 — has DA shifted to cue time
- learning_rate_signal (0-1) — modulates downstream plasticity
- rpe_state (str): "positive_burst" | "predicted" | "omission_pause" |
  "neutral" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class RewardPredictionErrorIntegrator(BrainMechanism):
    """Whole-brain RPE consolidator across DA populations."""

    SMOOTH = 0.20
    BURST_THRESHOLD = 0.30      # positive PE magnitude for burst
    OMISSION_THRESHOLD = -0.30
    LEARNING_RATE = 0.08

    def __init__(self):
        super().__init__(
            name="RewardPredictionErrorIntegratorVariant",
            human_analog="Whole-brain RPE integrator (Schultz 1997)",
            layer="integration",
        )
        self.state.setdefault("integrated_rpe", 0.0)
        self.state.setdefault("expected_value_trace", 0.0)
        self.state.setdefault("rpe_burst_detected", False)
        self.state.setdefault("rpe_omission_detected", False)
        self.state.setdefault("temporal_shift_progress", 0.0)
        self.state.setdefault("learning_rate_signal", 0.0)
        self.state.setdefault("rpe_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("burst_count", 0)
        self.state.setdefault("tick_count", 0)

    def _outcome_value(self, sign: int, intensity: float,
                        nacc: float) -> float:
        """Compute current outcome value from valence + NAc activity."""
        if sign == 0:
            return nacc * 0.5  # neutral — use accumbens as proxy
        return min(1.0, max(-1.0, sign * intensity * 0.7 + nacc * 0.3))

    def _integrated_rpe(self, snc_pe: float, vta_da: float,
                          outcome: float, prev_expected: float) -> float:
        """Aggregate RPE — uses SNc-computed PE if available, else
        derives from VTA + outcome - expected."""
        # Prefer SNc's computed PE; fall back to derivation
        if abs(snc_pe) > 0.05:
            derived = snc_pe
        else:
            derived = outcome - prev_expected
        # Modulate by VTA activity (high VTA → confident RPE)
        modulator = 0.5 + vta_da * 0.5
        return max(-1.0, min(1.0, derived * modulator))

    def _update_expected(self, prev_expected: float,
                           outcome: float) -> float:
        """Rescorla-Wagner update of expected value."""
        return prev_expected + self.LEARNING_RATE * (outcome - prev_expected)

    def _temporal_shift(self, prev_shift: float,
                          rpe_at_cue: float, rpe_at_outcome: float) -> float:
        """Amo 2022: temporal shift = DA at cue time grows, DA at outcome
        time shrinks over learning. Approximated as ratio of cue-related
        to outcome-related signal building over trials."""
        # Use sustained anticipatory drive (DLS/DMS) as cue proxy
        # vs phasic VTA at outcome — but here we use simpler proxy
        if rpe_at_cue > 0.15 and rpe_at_outcome < 0.20:
            return min(1.0, prev_shift + 0.005)
        # Reset slowly during outcome-only RPE
        if rpe_at_outcome > 0.25 and rpe_at_cue < 0.15:
            return max(0.0, prev_shift - 0.003)
        return prev_shift * 0.998

    def _learning_rate(self, abs_rpe: float, expected: float) -> float:
        """Modulate downstream plasticity rate. Higher abs RPE = bigger
        learning step. Reduces as expected value stabilizes."""
        return min(1.0, abs_rpe * 0.7 + (1.0 - expected) * 0.2)

    def _classify_state(self, rpe: float, outcome: float,
                          arousal: float) -> str:
        if abs(rpe) < 0.05 and outcome < 0.10:
            return "quiet"
        if rpe > self.BURST_THRESHOLD:
            return "positive_burst"
        if rpe < self.OMISSION_THRESHOLD:
            return "omission_pause"
        if abs(rpe) < 0.10:
            return "predicted"
        return "neutral"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vta_data = prior.get("VentralTegmentalDopamine", {})
        vta_da = float(vta_data.get("da_release",
                            vta_data.get("da_burst",
                              vta_data.get("da_signal", 0.0))))

        snc_data = prior.get("SubstantiaNigraCompacta", {})
        snc_pe = float(snc_data.get("prediction_error", 0.0))

        nacc_data = prior.get("NucleusAccumbensCore", {})
        nacc = float(nacc_data.get("nacc_drive",
                            nacc_data.get("pit_signal", 0.0)))

        # Cue-time vs outcome-time proxies for temporal shift
        dms_data = prior.get("DorsomedialStriatum", {})
        cue_signal = float(dms_data.get("goal_directed_signal",
                                  dms_data.get("dms_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        outcome = self._outcome_value(sign, intensity, nacc)
        prev_expected = float(self.state.get("expected_value_trace", 0.0))
        rpe_target = self._integrated_rpe(snc_pe, vta_da, outcome,
                                            prev_expected)

        prev_rpe = float(self.state.get("integrated_rpe", 0.0))
        rpe = self._smooth(prev_rpe, rpe_target)

        new_expected = self._update_expected(prev_expected, outcome)

        prev_shift = float(self.state.get("temporal_shift_progress", 0.0))
        shift = self._temporal_shift(prev_shift, cue_signal, abs(rpe))

        learning = self._learning_rate(abs(rpe), new_expected)

        state = self._classify_state(rpe, outcome, arousal)

        burst = state == "positive_burst"
        omission = state == "omission_pause"

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        burst_count = int(self.state.get("burst_count", 0))
        if burst:
            burst_count += 1

        self.state["integrated_rpe"] = round(rpe, 4)
        self.state["expected_value_trace"] = round(new_expected, 4)
        self.state["rpe_burst_detected"] = burst
        self.state["rpe_omission_detected"] = omission
        self.state["temporal_shift_progress"] = round(shift, 4)
        self.state["learning_rate_signal"] = round(learning, 4)
        self.state["rpe_state"] = state
        self.state["recent_states"] = recent
        self.state["burst_count"] = burst_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "integrated_rpe": round(rpe, 4),
            "expected_value_trace": round(new_expected, 4),
            "rpe_burst_detected": burst,
            "rpe_omission_detected": omission,
            "temporal_shift_progress": round(shift, 4),
            "learning_rate_signal": round(learning, 4),
            "rpe_state": state,
        }

    def _learning_progress(self) -> float:
        """How far along learning has progressed (Amo 2022)."""
        return float(self.state.get("temporal_shift_progress", 0.0))

    def _summary(self) -> dict:
        return {
            "rpe": self.state.get("integrated_rpe", 0.0),
            "expected": self.state.get("expected_value_trace", 0.0),
            "shift": self.state.get("temporal_shift_progress", 0.0),
            "state": self.state.get("rpe_state", "quiet"),
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

