"""
brain/neocortical/Neocortical031DorsalPrefrontalCentralExecutive.py
Dorsal Prefrontal Cortex (BA 9/46) — Central Executive Network Hub

ANATOMY (Duncan & Owen 2000; Petrides 2005; Owen et al. 2005):
    The dorsal prefrontal cortex (dPFC, BA 9/46) is the "central
    executive" hub — the highest-level cognitive control region.
    It receives convergent inputs from all sensory modalities,
    all subcortical systems, and all associative cortical areas,
    and uses them to guide goal-directed behavior.

    BA 9 (dorsal BA 9) and BA 46 (mid-DLPFC) form a functional
    unit specialized for:
    - Working memory maintenance (holding information in mind)
    - Task-set switching (changing between rules/goals)
    - Task monitoring (checking if you're doing the right thing)
    - Cognitive branching (pursuing a sub-goal while maintaining a main goal)
    - Novel task engagement (doing something you've never done before)

    dPFC is most active during tasks that require:
    - Holding a rule in mind while executing an action
    - Switching between two tasks
    - Processing multiple pieces of information simultaneously
    - Monitoring performance and adjusting strategy

    dPFC is the "most human" region of the brain — its large size
    and complexity correlate with higher cognitive abilities in humans
    compared to other primates.

KEY FINDINGS:
    1. Duncan & Owen 2000 (PMC11160327): "Common frontal activations
       during diverse cognitive tasks" — dPFC is the common hub
    2. Petrides 2005 (PMC2929791): "The DLPFC and cognitive control"
       — BA 9/46 for executive working memory
    3. Owen et al. 2005: "Executive functions" — dPFC supports
       novel problem-solving and planning

AGENT'S MAPPING:
    dorsal_pfc_output: dict — dPFC central executive output
    central_executive_active: bool — is CEN engaged?
    task_focus: float 0-1 — strength of cognitive control

CITATIONS:
    PMC11160327 — Duncan & Owen (2000). Common frontal activations. Neuroimage.
    PMC2929791 — Petrides (2005). DLPFC and cognitive control. Scholarpedia.
    PMC40447446 — DLPFC working memory and prefrontal function.
    PMC31551596 — Cognitive control and prefrontal cortex.


CITATIONS
---------
  - [Miller 2001, Annu Rev Neurosci 24:167, prefrontal cortex]
  - [Fuster 2008, The Prefrontal Cortex]
  - [Goldman-Rakic 1995, Neuron 14:477, working memory]
"""

from brain.base_mechanism import BrainMechanism


class DorsalPrefrontalCentralExecutive(BrainMechanism):
    """
    dPFC — central executive network hub.

    The highest-level cognitive control region. Holds goals,
    switches tasks, monitors performance, handles novel situations.
    """

    def __init__(self):
        super().__init__(
            name="DorsalPrefrontalCentralExecutive",
            human_analog="Dorsal prefrontal cortex (BA 9/46) — central executive, working memory hub",
            layer="neocortical",
        )
        self.state.setdefault("executive_buffer", [])
        self.state.setdefault("central_executive_active", False)
        self.state.setdefault("task_focus", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC dorsal (already computed working memory load)
        dl_dorsal = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dl_dorsal.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dl_dorsal.get("cognitive_control", 0.5)

        # ACC (difficulty/error signals increase executive demand)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            difficulty = acc_out.get("difficulty_signal", 0.3)
            ctrl_adj = acc_out.get("control_adjustment", 0.0)
        else:
            difficulty = 0.3
            ctrl_adj = 0.0

        # Anterior insula (salience signals executive switch)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)
        net_switch = ains.get("network_switch_trigger", "default")

        # Orbitofrontal (value guides executive priority)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # Task focus: base cognitive control + adjustment from ACC + salience boost
        base_focus = cognitive_ctrl * 0.6 + difficulty * 0.4
        exec_adjustment = ctrl_adj if ctrl_adj > 0 else 0.0
        salience_boost = 0.2 if salience > 0.6 else 0.0

        task_focus = base_focus + exec_adjustment + salience_boost
        task_focus = max(0.0, min(1.0, task_focus))

        # Central executive active when: high task focus + working memory load
        central_executive_active = task_focus > 0.55 and wm_load > 0.4

        # Network mode: executive when active, default otherwise
        network_mode = "executive" if central_executive_active else "default"

        self.state["task_focus"] = round(task_focus, 4)
        self.state["central_executive_active"] = central_executive_active
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dorsal_pfc_output": {
                "central_executive": central_executive_active,
                "task_focus": round(task_focus, 4),
                "network_mode": network_mode,
            },
            "central_executive_active": central_executive_active,
            "task_focus": round(task_focus, 4),
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

