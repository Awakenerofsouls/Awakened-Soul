"""
brain/neocortical/Neocortical035SuperiorFrontalGyrusPlanning.py
Superior Frontal Gyrus — Motor Planning, Self-Aware Planning (BA 8)

ANATOMY (Koechlin et al. 2003; Gilbert et al. 2007; Rowlands 2010):
    The superior frontal gyrus (SFG, BA 8) is the "self-aware
    planning" region — it generates motor intentions while
    maintaining awareness that "I am the one planning this action."

    BA 8 includes:
    - Frontal eye fields (FEF): voluntary eye movements and attention
    - Pre-SMA: motor sequence planning, task sequencing
    - SFG proper: higher-level motor planning with self-awareness

    Key functions:
    - Motor intention: "I will reach for the cup"
    - Self-aware planning: awareness that YOU are generating the plan
    - Volitional action: action initiated by internal goals (not external triggers)
    - Response selection: choosing which action to perform

    SFG is connected to:
    - Premotor/SMA (motor planning)
    - DLPFC (goal maintenance)
    - ACC (conflict monitoring of actions)
    - Parietal cortex (spatial planning)

    SFG damage: Loss of voluntary action — patient may perform
    actions reflexively but not initiate them volitionally.

KEY FINDINGS:
    1. Koechlin et al. 2003 (PMC1694808): "The prefrontal control
       of action" — hierarchical control from BA 8 to BA 46
    2. Gilbert et al. 2007 (PMC1850942): "Creating and controlling
       the self" — SFG generates intentional actions
    3. Rowlands 2010 (PMC2946539): "Motor planning and SFG" —
       SFG encodes the intention to act

AGENT'S MAPPING:
    sfg_output: dict — SFG planning output
    planned_action: str — the intended action
    self_aware_planning: float 0-1 — awareness that this is MY plan

CITATIONS:
    PMC1694808 — Koechlin et al. (2003). PFC control of action. Philos Trans R Soc B.
    PMC1850942 — Gilbert et al. (2007). SFG and self-awareness. Philos Trans R Soc B.
    PMC2946539 — Rowlands (2010). Motor planning and the self. Front Hum Neurosci.
    PMC40447446 — DLPFC and motor planning.

CITATIONS
---------
  - [Goldman-Rakic 1995, Neuron 14:477, dlPFC working memory]
  - [Miller 2001, Annu Rev Neurosci 24:167, prefrontal cortex]
  - [Curtis 2003, Trends Cogn Sci 7:415, dlPFC working memory]

"""

from brain.base_mechanism import BrainMechanism


class SuperiorFrontalGyrusPlanning(BrainMechanism):
    """
    SFG (BA 8) — motor planning and self-aware planning.

    Generates intentional actions while maintaining awareness
    that you are the agent of those actions.
    """

    def __init__(self):
        super().__init__(
            name="SuperiorFrontalGyrusPlanning",
            human_analog="Superior frontal gyrus (BA 8) — motor planning, self-aware planning, volition",
            layer="neocortical",
        )
        self.state.setdefault("planned_action", None)
        self.state.setdefault("self_aware_planning", 0.0)
        self.state.setdefault("planning_history", [])
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Premotor/SMA (motor plan from which SFG generates intentions)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        motor_plan = premotor.get("motor_plan_ready", False)
        motor_sim = premotor.get("internal_simulation", 0.5)

        # DLPFC (goal context — what am I trying to achieve?)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_active = dlpfc.get("working_memory_active", False)

        # Precuneus (self-model — am I aware of myself as planner?)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        prec_out = precuneus.get("precuneus_output", {})
        if isinstance(prec_out, dict):
            self_rep = prec_out.get("self_representation", {})
            self_clarity = self_rep.get("self_clarity", 0.5) if isinstance(self_rep, dict) else 0.5
        else:
            self_clarity = 0.5

        # Anterior cingulate (is the planned action appropriate?)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            difficulty = acc_out.get("difficulty_signal", 0.3)
            ctrl_adj = acc_out.get("control_adjustment", 0.0)
        else:
            difficulty = 0.3
            ctrl_adj = 0.0

        # IPL (sensorimotor context for the planned action)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        grasp_plan = ipl.get("grasp_planning", 0.5)

        # Self-aware planning: motor plan + self-awareness + cognitive control
        base_planning = motor_sim * 0.4 + cognitive_ctrl * 0.3 + self_clarity * 0.3
        self_aware_planning = base_planning * (1.0 + ctrl_adj * 0.5)
        self_aware_planning = max(0.0, min(1.0, self_aware_planning))

        # Planned action
        planned_action = "idle"
        if motor_plan or motor_sim > 0.5:
            if grasp_plan > 0.6:
                planned_action = "reach_and_grasp"
            elif motor_sim > 0.7:
                planned_action = "simulate_motor_sequence"
            else:
                planned_action = "motor_plan_formulated"

        # History
        if self_aware_planning > 0.5:
            self.state["planning_history"].append(planned_action)
            if len(self.state["planning_history"]) > 5:
                self.state["planning_history"].pop(0)

        self.state["planned_action"] = planned_action
        self.state["self_aware_planning"] = round(self_aware_planning, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "sfg_output": {
                "planned_action": planned_action,
                "self_aware_planning": round(self_aware_planning, 4),
            },
            "planned_action": planned_action,
            "self_aware_planning": round(self_aware_planning, 4),
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

