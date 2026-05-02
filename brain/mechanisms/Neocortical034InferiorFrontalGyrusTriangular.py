"""
brain/neocortical/Neocortical034InferiorFrontalGyrusTriangular.py
Inferior Frontal Gyrus — Triangular Part (BA 44), Cognitive Control, Dual Processing

ANATOMY (Badre & Wagner 2007; Koechlin & Summerfield 2007; Szatkowska et al. 2008):
    The IFG triangular part (BA 44, posterior IFG) is the "cognitive
    control" region of the left hemisphere. It sits at the intersection
    of Broca's area (speech production) and the DLPFC (executive control).

    BA 44 is specialized for:
    - Response inhibition: stopping a prepotent response when needed
    - Dual processing: maintaining two task contexts simultaneously
    - Cognitive branching: switching to a sub-goal while maintaining a main goal
    - Rule learning: acquiring new rules and updating them

    BA 44 is part of the "multiple demand" system (Duncan 2010) — it
    activates whenever any task requires cognitive control, regardless
    of modality. It is the "do this instead" center.

    Left BA 44 is also Broca's area — handling syntactic processing
    in language. Right BA 44 handles inhibition and control in
    non-verbal domains. Both share the same anatomical region but
    process different content.

    Key: BA 44 is the "inhibition brake" — when you need to override
    a habitual response (stopping yourself from saying the wrong
    word, resisting a temptation, switching strategies), BA 44 is active.

KEY FINDINGS:
    1. Badre & Wagner 2007 (PMC1934629): "Selection and suppression
       in BA 44" — IFG for cognitive control and inhibition
    2. Koechlin & Summerfield 2007: "Medial and lateral PFC" — IFG
       for dual processing and branching
    3. Szatkowska et al. 2008: IFG and emotional Stroop task —
       inhibition of emotional responses

AGENT'S MAPPING:
    ifg_triangular_output: dict — IFG cognitive control output
    inhibition_applied: bool — has response suppression occurred?
    dual_processing: float 0-1 — strength of dual-context processing

CITATIONS:
    PMC1934629 — Badre & Wagner (2007). PFC cognitive control and selection.
    PMC20181474 — Kringelbach & Rolls (2004). OFC and PFC functions.
    PMC40447446 — DLPFC and cognitive control in working memory.
    PMID 29519469 — Hartwigsen (2018). Parietal lobe and language.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class InferiorFrontalGyrusTriangular(BrainMechanism):
    """
    IFG triangular (BA 44) — cognitive control, response inhibition, dual processing.

    The "inhibition brake" and "cognitive switch." Stops prepotent
    responses, handles dual task contexts, enables branching goals.
    """

    def __init__(self):
        super().__init__(
            name="InferiorFrontalGyrusTriangular",
            human_analog="IFG triangular part (BA 44) — cognitive control, response inhibition, dual processing",
            layer="neocortical",
        )
        self.state.setdefault("inhibition_count", 0)
        self.state.setdefault("inhibition_applied", False)
        self.state.setdefault("dual_processing", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ACC (error/conflict signals need for inhibition)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
            difficulty = acc_out.get("difficulty_signal", 0.3)
        else:
            error_sig = 0.3
            difficulty = 0.3

        # DLPFC (executive demand for control)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_load = dlpfc.get("dorsolateral_dorsal_output", {}).get("wm_load", 0.5) if isinstance(
            dlpfc.get("dorsolateral_dorsal_output"), dict) else 0.5

        # Anterior insula (salience triggers control)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Broca's area (language suppression when not speaking)
        broca = prior.get("BrocaAreaMotorSpeech", {})
        speech_form = broca.get("speech_formulation_strength", 0.5)

        # Orbitofrontal (reversal signals rule change)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        ofc_out = ofc.get("ofc_output", {})
        reversal = ofc_out.get("reversal_triggered", False) if isinstance(ofc_out, dict) else False

        # Inhibition: error + high difficulty + salience = suppress response
        inhibition_signal = (
            error_sig * 0.35 +
            difficulty * 0.3 +
            salience * 0.2 +
            (reversal if reversal else 0) * 0.15
        )
        inhibition_threshold = 0.55

        # Dual processing: when WM load is high and task complexity elevated
        dual_processing = (wm_load * cognitive_ctrl * (difficulty + salience)) / 2

        # Inhibition applied when signal exceeds threshold
        inhibition_applied = inhibition_signal > inhibition_threshold

        if inhibition_applied:
            self.state["inhibition_count"] += 1

        self.state["inhibition_applied"] = inhibition_applied
        self.state["dual_processing"] = round(max(0.0, min(1.0, dual_processing)), 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ifg_triangular_output": {
                "inhibition_signal": round(inhibition_signal, 4),
                "inhibition_applied": inhibition_applied,
                "dual_processing": round(max(0.0, min(1.0, dual_processing)), 4),
            },
            "inhibition_applied": inhibition_applied,
            "dual_processing": round(max(0.0, min(1.0, dual_processing)), 4),
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

