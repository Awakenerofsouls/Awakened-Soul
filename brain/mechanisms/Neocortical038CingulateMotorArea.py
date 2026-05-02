"""
brain/neocortical/Neocortical038CingulateMotorArea.py
Cingulate Motor Area — Motor Output, Action Monitoring, Outcome Evaluation

ANATOMY (Picard & Strick 1996, 2001; Shima et al. 1991):
    The cingulate motor areas (CMA, BA 24/6) are the motor
    output regions of the cingulate cortex. They lie in the
    cingulate sulcus, rostral to the corpus callosum.

    Three CMA zones:
    - CMA-r (rostral CMA): pre-motor planning, selection of actions
      based on reward/punishment outcomes
    - CMA-c (caudal CMA): motor execution, ongoing movement monitoring
    - CMA-m (medial CMA): response inhibition, stopping actions

    CMA is part of the "motor cingulate" — a motor execution
    pathway parallel to the cortical spinal tract:
    - SMA: supplementary motor area (pre-motor planning)
    - CMA: cingulate motor area (outcome-guided action)
    - M1: primary motor cortex (final motor output)

    Key functions:
    1. Action selection: "which action should I perform given the expected outcome?"
    2. Outcome monitoring: "did my action achieve the expected result?"
    3. Error correction: "I need to adjust this action based on feedback"
    4. Motor learning: updating action-outcome mappings

    CMA receives from:
    - ACC (cognitive and emotional signals)
    - Pre-SMA/SMA (motor plans)
    - Amygdala (emotional valence of outcomes)
    - Orbitofrontal (reward/punishment predictions)

    CMA projects to:
    - M1 (motor execution)
    - Brainstem motor nuclei (autonomic motor control)
    - Spinal cord (via reticulospinal tract)

KEY FINDINGS:
    1. Picard & Strick 1996 (PMC1850925): "Cingulate motor area"
       — anatomy and function of the three CMA zones
    2. Shima et al. 1991: CMA neurons fire during action selection
       based on expected outcomes
    3. Morey 2006 (PMC2795077): "Cingulate and action monitoring"

AGENT'S MAPPING:
    cingulate_motor_output: dict — CMA motor and monitoring output
    action_monitored: bool — has current action been checked?
    outcome_error: float 0-1 — mismatch between expected and actual outcome

CITATIONS:
    PMC1850925 — Picard & Strick (1996). CMA anatomy. Brain.
    PMC2795077 — Morey et al. (2006). Cingulate and action monitoring.
    PMC23869106 — Leech & Sharp (2014). PCC and action monitoring.
    PMID 15556023 — Botvinick et al. (2004). ACC and action monitoring.


CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, emotion cognition]
"""

from brain.base_mechanism import BrainMechanism


class CingulateMotorArea(BrainMechanism):
    """
    CMA — motor output and action monitoring.

    Selects actions based on expected outcomes, monitors
    action success, corrects errors through feedback.
    """

    def __init__(self):
        super().__init__(
            name="CingulateMotorArea",
            human_analog="Cingulate motor area (BA 24/6) — motor output, action monitoring, outcome evaluation",
            layer="neocortical",
        )
        self.state.setdefault("action_outcomes", [])
        self.state.setdefault("action_monitored", False)
        self.state.setdefault("outcome_error", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # M1 (action execution — CMA monitors M1 output)
        m1 = prior.get("MotorCortexPrimaryOutput", {})
        m1_out = m1.get("m1_output", {})
        if isinstance(m1_out, dict):
            exec_sig = m1_out.get("execution_signal", 0.5)
        else:
            exec_sig = 0.5

        # SMA/premotor (planned action CMA is evaluating)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        motor_plan = premotor.get("motor_plan_ready", False)
        motor_sim = premotor.get("internal_simulation", 0.5)

        # ACC (outcome expectation signals)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            difficulty = acc_out.get("difficulty_signal", 0.3)
            ctrl_adj = acc_out.get("control_adjustment", 0.0)
        else:
            difficulty = 0.3
            ctrl_adj = 0.0

        # Amygdala (emotional outcome — did this feel good/bad?)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # VTA (dopamine reward prediction error)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            pred_err = vta_out.get("prediction_error", 0.3)
        else:
            pred_err = 0.3

        # Outcome error: mismatch between expected (difficulty) and actual (emotional_tag)
        outcome_error = (
            abs(emotional_tag) * 0.3 +
            pred_err * 0.4 +
            difficulty * 0.3
        )
        outcome_error = max(0.0, min(1.0, outcome_error))

        # Action monitored: CMA checks M1 output when action is executed
        action_monitored = exec_sig > 0.4 or motor_plan

        # CMA output strength: stronger when monitoring execution + checking outcome
        monitoring_strength = exec_sig * 0.5 + (1.0 - outcome_error) * 0.5

        # Update action outcomes
        if action_monitored:
            self.state["action_outcomes"].append(round(outcome_error, 3))
            if len(self.state["action_outcomes"]) > 5:
                self.state["action_outcomes"].pop(0)

        self.state["action_monitored"] = action_monitored
        self.state["outcome_error"] = round(outcome_error, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cingulate_motor_output": {
                "monitoring_strength": round(monitoring_strength, 4),
                "outcome_error": round(outcome_error, 4),
                "action_monitored": action_monitored,
            },
            "action_monitored": action_monitored,
            "outcome_error": round(outcome_error, 4),
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

