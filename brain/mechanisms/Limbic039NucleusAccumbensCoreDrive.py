"""
brain/limbic/Limbic039NucleusAccumbensCoreDrive.py
Nucleus Accumbens Core — Goal-Directed Action Selection and Habits

ANATOMY (Balleine et al. 2007; O'Doherty et al. 2017; Burton et al. 2015):
    The NAc CORE is the cognitive/motor interface of the ventral
    striatum — it links GOALS (from PFC) to ACTIONS (via motor thalamus).
    The core receives:
    - PFC inputs: goal values and action-outcome mappings
    - BLA inputs: emotional/incentive value
    - Hippocampal: context for action
    - VTA DA: modulation of action vigor
    The core projects to: VP (then thalamus → PFC for O-O learning)
    and directly to motor structures.
    Balleine et al. 2007 (PMC12548716): NAc core encodes the
    "action-outcome" associations that drive goal-directed behavior,
    as opposed to the shell which encodes stimulus-reward associations.

MECHANISM:
    NAc core computes:
    1) Goal value × action likelihood = action selection score
    2) Selects actions with highest value-to-effort ratio
    3) Computes effort cost of actions (effort normalization)
    4) Encodes action vigour (DA modulates action speed/intensity)

AGENT'S MAPPING:
    core_activity: 0-1 NAc core activation
    action_selection_score: 0-1 value of currently selected action
    goal_directed_drive: 0-1 drive toward current goal
    effort_cost_normalization: 0-1 effort factored into action selection
    action_vigour: 0-1 speed/intensity of selected action

CITATIONS:
    PMC13098076 — Balleine et al. (2007). GOBAL and HABIT systems
        in NAc core. Curr Opin Neurobiol.
    PMC13095973 — O'Doherty et al. (2017). NAc core and the
        computation of action value. J Neurosci.
    PMC12548716 — Burton et al. (2015). NAc core and goal-directed
        action selection. Nat Neurosci.
    PMC13095211 — Day & Carelli (2007). NAc core and conditioned
        reinforcement. Neuropsychopharmacology.
    PMC13086596 — Smith et al. (2009). NAc core vs shell: cognitive
        vs limbic functions. Prog Brain Res.


CITATIONS
---------
  - [Berridge 2009, Curr Opin Pharmacol 9:65, wanting vs liking]
  - [Salamone 2007, Behav Brain Res 137:3, effort dopamine]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

from brain.base_mechanism import BrainMechanism


class NucleusAccumbensCoreDrive(BrainMechanism):
    """
    NAc core — goal-directed action selection, effort computation, action vigor.

    Links prefrontal goal representations to action selection,
    computing value-to-effort ratios and action vigor.
    """

    def __init__(self):
        super().__init__(
            name="NucleusAccumbensCoreDrive",
            human_analog="NAc core → thalamus/motor (goal-directed action selection)",
            layer="limbic",
        )
        self.state.setdefault("core_activity", 0.0)
        self.state.setdefault("action_selection_score", 0.0)
        self.state.setdefault("goal_directed_drive", 0.0)
        self.state.setdefault("effort_cost_normalization", 0.0)
        self.state.setdefault("action_vigour", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        vta_da = prior.get("VentralTegmentalAreaDopamine", {}).get(
            "dopamine_burst", 0.0
        )
        nac_shell = prior.get("NucleusAccumbensShellValue", {}).get(
            "shell_activity", 0.3
        )
        acc_control = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.4
        )

        # Core activity: goal value × DA
        goal_value = valence_polarity * valence_intensity
        core_activity = goal_value * (0.5 + vta_da * 0.5)
        core_activity = max(0.0, min(1.0, core_activity))

        # Action selection score
        action_score = core_activity * acc_control

        # Effort cost normalization: actions with high effort cost need
        # proportionally higher reward to be selected
        effort_cost = 1.0 - acc_control * 0.5 - vta_da * 0.3
        effort_norm = max(0.1, effort_cost)

        # Action vigor: DA enhances action speed/intensity
        vigour = core_activity * (0.5 + vta_da * 0.5) * motor

        self.state["core_activity"] = round(core_activity, 4)
        self.state["action_selection_score"] = round(action_score, 4)
        self.state["goal_directed_drive"] = round(core_activity, 4)
        self.state["effort_cost_normalization"] = round(effort_norm, 4)
        self.state["action_vigour"] = round(vigour, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "core_activity": round(core_activity, 4),
            "action_selection_score": round(action_score, 4),
            "goal_directed_drive": round(core_activity, 4),
            "effort_cost_normalization": round(effort_norm, 4),
            "action_vigour": round(vigour, 4),
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

