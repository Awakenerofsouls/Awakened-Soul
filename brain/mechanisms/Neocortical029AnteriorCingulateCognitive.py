"""
brain/neocortical/Neocortical029AnteriorCingulateCognitive.py
Anterior Cingulate Cortex (Dorsal) — Cognitive Error Monitoring, Conflict

ANATOMY (Botvinick et al. 2004; Holroyd & Yeung 2012; Shenhav et al. 2013):
    The dorsal anterior cingulate cortex (dACC, BA 32/24) is the
    "cognitive monitoring" center. It sits at the intersection of
    cognitive control (DLPFC) and emotional salience (AI/vmPFC).

    dACC has two key functions:
    1. Error monitoring: detects when processing goes wrong (conflicts,
       mistakes, failures) — the "candle" that burns when things go wrong
    2. Task difficulty signaling: computes "how hard is this task right now"
       and signals need for more cognitive control

    dACC encodes "expected value of control" (Shenhav 2013) — it computes
    whether investing more cognitive control will pay off. When the
    expected value is high, dACC signals DLPFC to increase control.
    When it's low, control is relaxed.

    dACC receives from:
    - ACC (limbic) for emotional conflict
    - DLPFC (cognitive load signals)
    - Anterior insula (salience signals)
    - Thalamus (sensory monitoring)
    and projects to:
    - DLPFC (increase/decrease control)
    - Pre-SMA/SMA (motor adjustment)
    - Brainstem nuclei (autonomic adjustment)

KEY FINDINGS:
    1. Botvinick et al. 2004 (PMID 15556023): "Conflict monitoring and ACC"
       — dACC signals conflict to trigger cognitive control
    2. Fellows 2005 (PMID 15705613): "Is ACC necessary for cognitive control?"
       — review of ACC lesion studies showing impaired error monitoring
    3. Bush et al. 2022 (PMC36040991): "Action-value in dACC" — dACC
       encodes value of control effort during self-regulation

AGENT'S MAPPING:
    acc_dorsal_output: dict — dACC monitoring output
    error_signal: float 0-1 — error/conflict detected
    difficulty_signal: float 0-1 — task difficulty level
    cognitive_adjustment: float 0-1 — control adjustment needed

CITATIONS:
    PMID 15556023 — Botvinick et al. (2004). Conflict monitoring and ACC. Trends Cogn Sci.
    PMID 15705613 — Fellows (2005). ACC and cognitive control. Brain.
    PMC36040991 — Bush et al. (2022). Action-value in dACC. PLoS ONE.
    PMID 19487195 — Craig (2009). Anterior insula and awareness. Phil Trans B.


CITATIONS
---------
  - [Botvinick 2001, Psychol Rev 108:624, conflict monitoring]
  - [Carter 1998, Science 280:747, ACC conflict]
  - [Shenhav 2013, Neuron 79:217, expected value]
"""

from brain.base_mechanism import BrainMechanism


class AnteriorCingulateCognitive(BrainMechanism):
    """
    dACC — cognitive error monitoring and conflict resolution.

    Detects errors and conflicts, signals need for more cognitive
    control. The "do I need to pay more attention?" center.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorCingulateCognitive",
            human_analog="Dorsal anterior cingulate cortex — error monitoring, cognitive control",
            layer="neocortical",
        )
        self.state.setdefault("error_history", [])
        self.state.setdefault("error_signal", 0.0)
        self.state.setdefault("difficulty_signal", 0.0)
        self.state.setdefault("cognitive_adjustment", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC (cognitive load — how hard is working memory?)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Anterior insula (salience — is there an important event?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)
        av_binding = prior.get("PosteriorSuperiorTemporalGyrus", {}).get("audiovisual_binding", 0.5)

        # Limbic ACC (emotional conflict)
        acc_limbic = prior.get("AnteriorCingulateConflict", {})
        acc_out = acc_limbic.get("acc_output", {})
        if isinstance(acc_out, dict):
            conflict = acc_out.get("conflict_level", 0.3)
        else:
            conflict = 0.3

        # Orbitofrontal (value — is this worth the effort?)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # IFG triangular (inhibition monitoring)
        ifg = prior.get("InferiorFrontalGyrusTriangular", {})
        inhibition = ifg.get("inhibition_applied", False)

        # Error signal: conflict + high WM load + high salience = potential error
        # Also: when value is high and WM is overloaded, errors more likely
        error_signal = (
            conflict * 0.3 +
            (wm_load * cognitive_ctrl) * 0.3 +
            salience * 0.2 +
            (av_binding if av_binding < 0.4 else 0) * 0.2
        )
        error_signal = max(0.0, min(1.0, error_signal))

        # Difficulty signal: based on WM load and conflict
        difficulty_signal = (wm_load * 0.5 + conflict * 0.3 + salience * 0.2)
        difficulty_signal = max(0.0, min(1.0, difficulty_signal))

        # Cognitive adjustment: dACC → DLPFC to increase/decrease control
        # High difficulty + high value = increase control; low value = relax
        if value_sig > 0.6 and difficulty_signal > 0.5:
            cognitive_adjustment = difficulty_signal * 0.8
        elif value_sig < 0.4:
            cognitive_adjustment = -0.2
        else:
            cognitive_adjustment = 0.0

        # Error history
        if error_signal > 0.5:
            self.state["error_history"].append(round(error_signal, 3))
            if len(self.state["error_history"]) > 5:
                self.state["error_history"].pop(0)

        self.state["error_signal"] = round(error_signal, 4)
        self.state["difficulty_signal"] = round(difficulty_signal, 4)
        self.state["cognitive_adjustment"] = round(cognitive_adjustment, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "acc_dorsal_output": {
                "error_signal": round(error_signal, 4),
                "difficulty_signal": round(difficulty_signal, 4),
                "control_adjustment": round(cognitive_adjustment, 4),
            },
            "error_signal": round(error_signal, 4),
            "difficulty_signal": round(difficulty_signal, 4),
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

