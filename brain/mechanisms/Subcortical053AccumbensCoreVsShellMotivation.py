"""
Subcortical053AccumbensCoreVsShellMotivation.py — Wire 53: NAcc Motivation

Neural substrate: Nucleus accumbens core vs shell — goal vs habit motivation.

The nucleus accumbens (NAc) is the ventral striatum — a basal ganglia
structure at the interface of limbic and motor systems. It has two
major subterritories: the core and the shell, with anatomically and
functionally distinct roles in motivation and behavior.

Cardinal 2002 established the dissociation: core supports "goal-
directed" behavior — actions based on current value assessments of
outcomes — while shell supports "habitual" behavior — more automatic,
context-driven responses. This was shown via disconnection studies:
core lesions abolish outcome devaluation effects (goal-directed intact
habits broken), shell lesions reduce Pavlovian approach behavior.

Baldo 2007 extended this, mapping the interface between feeding
motivation and compulsive overeating, showing core/shell differential
involvement in drive states.

KEY RESEARCH FINDINGS:
1. Anatomical segregation. Heimer et al. 1997: core = central NAc,
   shell = surrounding laminar organization. Core is continuous with
   dorsal striatum; shell is more limbic-associated. Shell has
   calbindin-rich matrix, core has more substance P.

2. Afferents differ by subregion. Cardinal et al. 2002: Core receives
   inputs from: prelimbic cortex (PFC area 32), basolateral amygdala
   (BLA), ventral hippocampus, and parabrachial. Shell receives:
   lateral hypothalamus, lateral septum, ventral tegmental area (VTA),
   and infralimbic cortex. Shell has a distinct set of afferents
   that support its role in maintaining drive states.

3. Efferents differ. Core projects to: substantia nigra (SNr), ventral
   pallidum (VP), and subthalamic nucleus. Shell projects to: VP,
   lateral hypothalamus, and VTA — more limbic outputs. Core has
   more direct motor output; shell has more modulatory/hormonal output.

4. Goal-directed vs. habitual behavior. Cardinal 2002: "The core is
   critical for goal-directed actions: inactivation of the NAc core
   but not shell blocked the effects of outcome devaluation on
   instrumental performance." Shell lesions impaired conditioned
   approach but not instrumental learning. Different roles in the
   broader motivation circuit.

5. Dopamine in core vs. shell. Bassareo et al. 2007: DA in core
   encodes "stimulus-reward prediction error" for specific rewards;
   DA in shell encodes "general motivation/incentive salience." Core
   DA transmission is more selective, shell DA more diffuse. This
   difference supports the core's role in precise goal-assessment.

6. Seeking vs. consuming. Baldo 2007: Shell is more involved in
   "consummatory" aspects (eating, drinking, sexual behavior), while
   core is more involved in "seeking/preparatory" aspects (approach
   behavior, exploration). Berridge: shell = "liking" (pleasure
   hotspot, see PleasureAnchor), core = "wanting" (incentive drive).

7. Addiction and compulsion. Belin 2009: "Transition from voluntary
   to habitual drug use is accompanied by a shift from core to shell
   involvement." Core-based goal-directed system fails in addiction;
   shell-based habit system takes over, producing compulsive drug-
   seeking.shell may drive "habit-like" compulsive drug seeking.

8. Motivation balance. The core/shell balance can be measured as a
   ratio: high core = goal-directed, high shell = habitual drive.
   This balance shifts with learning, addiction, and stress.

9. Shell in feeding and reward. Shell lesions suppress eating (kill
   motivation to eat), while core lesions disrupt the learning of
   which actions produce food. Shell maintains "appetitive state."

OUTPUTS:
  accumbens_motivation_signal: float 0-1 — total NAc activation
  core_shell_balance: float 0-1 — 0=shell-dominant, 1=core-dominant
  goal_directedness: float 0-1 — degree of goal-directed vs habitual

INPUTS:
  limbic_signal: amygdala/hippocampal emotional input
  PFC_input: prefrontal cognitive control
  reward_signal: VTA DA reward signal
  drive_state: hunger/thirst/motivation level
  devaluation_status: whether the outcome has been devalued

CITATIONS:
    PMC4819964 — Aitken TJ, Greenfield VY, Wassum KM (2016). Nucleus Accumbens Core
        Dopamine Signaling Tracks the Need-Based Motivational Value of Food-Paired
        Cues. Learn Mem.
    PMC5061892 — Collins AL, Aitken TJ, Greenfield VY et al. (2016). Nucleus
        Accumbens Acetylcholine Receptors Modulate Dopamine and Motivation.
        Neuropsychopharmacology.


CITATIONS
---------
  - [Berridge 2009, Curr Opin Pharmacol 9:65, wanting vs liking]
  - [Salamone 2007, Behav Brain Res 137:3, effort dopamine]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

from brain.base_mechanism import BrainMechanism


class AccumbensCoreVsShellMotivation(BrainMechanism):
    """
    NAc core vs shell — goal-directed vs habitual motivation.

    Core supports goal-directed action selection (outcome-based);
    shell supports habitual drive and appetitive states. Their
    dynamic balance determines the mode of motivation.
    """

    CORE_ACTIVATION_GAIN = 0.60
    SHELL_ACTIVATION_GAIN = 0.50
    GOAL_LEARNING_RATE = 0.06
    HABIT_LEARNING_RATE = 0.04
    SHELL_DRIVE_DECAY = 0.03

    def __init__(self):
        super().__init__(
            name="AccumbensCoreVsShellMotivation",
            human_analog="Nucleus accumbens core vs shell — motivation dichotomy",
            layer="subcortical",
        )
        self.state.setdefault("accumbens_motivation_signal", 0.0)
        self.state.setdefault("core_shell_balance", 0.5)
        self.state.setdefault("goal_directedness", 0.6)
        self.state.setdefault("core_activation", 0.0)
        self.state.setdefault("shell_activation", 0.0)
        self.state.setdefault("appetitive_drive", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        limbic_signal = input_data.get("limbic_signal", 0.5)
        PFC_input = input_data.get("PFC_input", 0.5)
        reward_signal = input_data.get("reward_signal", 0.0)
        drive_state = input_data.get("drive_state", 0.5)
        devaluation_status = input_data.get("devaluation_status", False)
        consummatory_signal = input_data.get("consummatory_signal", 0.0)
        seeking_signal = input_data.get("seeking_signal", 0.0)

        # --- Core activation (goal-directed) ---
        # Core: driven by PFC (cognitive evaluation of outcomes),
        # reward signals (RPE), and devaluation awareness
        outcome_eval = PFC_input * 0.5
        reward_boost = reward_signal * 0.4
        devaluation_factor = 0.7 if devaluation_status else 1.0

        core_activation = (outcome_eval + reward_boost) * devaluation_factor * self.CORE_ACTIVATION_GAIN
        core_activation = max(0.0, min(1.0, core_activation))

        # --- Shell activation (habitual/appetitive) ---
        # Shell: driven by limbic/emotional signals, drive state,
        # consummatory cues, and less by PFC cognitive evaluation
        limbic_base = limbic_signal * 0.4
        drive_contribution = drive_state * 0.35
        consummatory_boost = consummatory_signal * 0.25

        shell_activation = (limbic_base + drive_contribution + consummatory_boost) * self.SHELL_ACTIVATION_GAIN
        shell_activation = max(0.0, min(1.0, shell_activation))

        # --- Core/shell balance ---
        # Ratio: 0 = fully shell, 1 = fully core
        total_activation = core_activation + shell_activation
        if total_activation > 0.001:
            balance = core_activation / total_activation
        else:
            balance = 0.5  # neutral

        # Smooth balance changes
        balance_ema = self.state["core_shell_balance"] * 0.85 + balance * 0.15
        self.state["core_shell_balance"] = max(0.0, min(1.0, balance_ema))

        # --- Goal directedness ---
        # High core activation + low devaluation = goal-directed
        # High shell activation with drive = habitual/appetitive
        if devaluation_status:
            # Outcome devalued — goal-directed system must re-evaluate
            # If core is strong, behavior adjusts (goal-directed)
            # If shell is strong, behavior continues despite devaluation (habit)
            if self.state["core_shell_balance"] > 0.55:
                # Core dominant — adjusts behavior → goal-directed
                adjustment = 0.05 * (1.0 - self.state["goal_directedness"])
                self.state["goal_directedness"] = min(0.95, self.state["goal_directedness"] + adjustment)
            else:
                # Shell dominant — behavior persists despite devaluation
                self.state["goal_directedness"] = max(0.1, self.state["goal_directedness"] - 0.08)
        else:
            # Normal conditions — learn from reward
            if reward_signal > 0.4:
                delta = self.GOAL_LEARNING_RATE * core_activation * reward_signal
                self.state["goal_directedness"] = min(0.95, self.state["goal_directedness"] + delta)

        # Shell habitual learning
        if drive_state > 0.7:
            self.state["goal_directedness"] = max(0.2, self.state["goal_directedness"] - 0.02)

        # --- Appetitive drive ---
        # Shell drives the "appetitive state" — sustained motivation to seek
        new_drive = self.state["appetitive_drive"] * 0.85 + shell_activation * 0.15
        new_drive += drive_state * 0.03
        if consummatory_signal > 0.5:
            new_drive -= self.SHELL_DRIVE_DECAY * 0.5
        self.state["appetitive_drive"] = max(0.0, min(1.0, new_drive))

        # --- Total motivation signal ---
        total_motivation = (core_activation + shell_activation) / 2.0 + self.state["appetitive_drive"] * 0.2
        total_motivation = max(0.0, min(1.0, total_motivation))

        self.state["accumbens_motivation_signal"] = total_motivation
        self.state["core_activation"] = core_activation
        self.state["shell_activation"] = shell_activation
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "accumbens_motivation_signal": round(total_motivation, 4),
            "core_shell_balance": round(self.state["core_shell_balance"], 4),
            "goal_directedness": round(self.state["goal_directedness"], 4),
            "core_activation": round(core_activation, 4),
            "shell_activation": round(shell_activation, 4),
            "appetitive_drive": round(self.state["appetitive_drive"], 4),
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

