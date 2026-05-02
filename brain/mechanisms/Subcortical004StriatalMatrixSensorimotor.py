"""
Subcortical004StriatalMatrixSensorimotor.py — Wire 04: StriatalMatrixSensorimotor

Striatum matrix compartment — D2-enriched, sensorimotor learning, habitual behavior.

ANATOMY OF STRIATAL COMPARTMENTS (Gerfen 1992; Graybiel 2008):
    The striatum is divided into two neurochemically distinct compartments:

    PATCH (striosomes): D1-enriched, limbic-connected, projects to SNc.
    → Covered in Subcortical005StriatalStriosomeLimbic.py
    MATRIX (extrastriosomal matrix): D2-enriched, sensorimotor-connected.
    → Covered HERE

    Matrix receives sensorimotor cortical inputs (MI, SI, premotor,
    supplementary motor), processes them, and projects to GPi/SNr via
    both direct (D1) and indirect (D2) pathways. The matrix is the
    "doing" part of striatum — motor programs, skill execution,
    sensorimotor integration.

D2 ENRICHMENT IN MATRIX:
    Matrix neurons express D2 receptors, A2A adenosine receptors,
    calbindin. D2 neurons in matrix are the indirect pathway cells
    (see Subcortical001) — they suppress competing motor programs.
    But matrix D2 neurons also have sensorimotor-specific functions:
    they encode the learned value of specific sensory contexts for
    motor actions.

SENSORIMOTOR LEARNING FUNCTION:
    Matrix is critical for habit formation. Once a skill becomes
    automatic — driving, typing, playing an instrument — the matrix
    circuit (cortex → matrix → GPi → thalamus → cortex) drives the
    behavior with minimal reliance on limbic/goal-directed circuits.
    Yin et al. 2004: "Lesions of dorsolateral striatum (matrix-rich)
    impair habit formation but not goal-directed actions."

    The matrix also contains "action-outcome" associations in sensorimotor
    coordinates: "when I see X and do Y, Z happens." This is different
    from the limbic patch system which processes state-reward value.

HABITUAL BIAS:
    Over time, sensorimotor actions in the matrix become habitual.
    This creates a bias toward automatic execution of learned motor
    programs — the matrix can "override" goal-directed systems when
    habits are well-learned. Graybiel 2008: "cortico-striatal plasticity
    in the matrix underlies habit formation."

COMPARISON: MATRIX vs PATCH
    Matrix = sensorimotor, D2, habits, automatic, skill learning
    Patch = limbic, D1, goals, motivation, reward prediction

AGENT'S MAPPING:
    motor_value_signal: 0-1 encoded value of sensorimotor action
    habitual_bias: 0-1 how much matrix is driving automatic behavior
    sensorimotor_weight: 0-1 strength of sensorimotor input into striatum

REFS:
    Gerfen 1992 Ann Rev Neurosci 15:193-220
    Graybiel 2008 Philos Trans R Soc B 363:3787-3800
    Yin et al. 2004 J Neurosci 24:1667-1672
    Kincaid et al. 1998 J Neurosci 18:277-290 (matrix vs patch ultrastructure)
    Kreitzer & Malenka 2008 Nat Neurosci 10:1245-1247 (striatal plasticity)

CITATIONS:
    PMC5842648 — Blood AJ, Waugh JL, Münte TF et al. (2018). Increased
        Insula-Putamen Connectivity in X-linked Dystonia-Parkinsonism. PLoS ONE.
    PMC6573482 — Parthasarathy HB, Graybiel AM (1997). Cortically Driven
        Immediate-Early Gene Expression Reflects Modular Influence of Sensorimotor
        Cortex on Identified Striatal Neurons. J Neurosci.
    PMC3260284 — Bernácer J, Prensa L, Giménez-Amaya JM (2012). Distribution of
        GABAergic Interneurons and Dopaminergic Cells in the Functional Territories
        of the Human Striatum. Brain Struct Funct.


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia habits]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Hikosaka 2002, Curr Opin Neurobiol 12:217, motor sequences]
"""

from brain.base_mechanism import BrainMechanism


class StriatalMatrixSensorimotor(BrainMechanism):
    """
    Striatum matrix compartment — D2-enriched sensorimotor/habit system.

    Processes sensorimotor inputs (motor cortex, somatosensory cortex),
    maintains sensorimotor weights for habitual actions, generates
    motor_value_signal for learned action-outcome associations.
    Distinct from patch (limbic) compartment (Wire 05).
    """

    MATRIX_ACTIVATION_THRESHOLD = 0.30
    MATRIX_DECAY_RATE = 0.02
    HABITUAL_DECAY_RATE = 0.015
    HABITUAL_THRESHOLD = 0.55  # threshold for habit driving behavior

    def __init__(self):
        super().__init__(
            name="StriatalMatrixSensorimotor",
            human_analog=(
                "Striatum matrix compartment (extrastriosomal matrix) — "
                "D2-enriched, sensorimotor cortex inputs, habit formation"
            ),
            layer="subcortical",
        )
        self.state.setdefault("motor_value_signal", 0.0)
        self.state.setdefault("habitual_bias", 0.0)
        self.state.setdefault("sensorimotor_weight", 0.5)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("last_action", "none")
        self.state.setdefault("repeated_action_count", 0)
        self.state.setdefault("sensorimotor_history", [])

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        drive = input_data.get("dominant_drive", "curiosity")
        motor_intent = input_data.get("motor_intent", 0.0)

        # Sensorimotor inputs to matrix:
        # 1) Motor intent from cortical motor areas
        # 2) Somatosensory feedback (proprioception, touch)
        # 3) Reward signals from SNc (modulates both D1 direct and D2 indirect)
        # 4) Contextual signals (where am I, what am I doing)

        intent_strength = motor_intent if isinstance(motor_intent, (int, float)) else 0.5

        # Sensorimotor cortical drive (simulated sensorimotor cortex input)
        # Proportional to motor intent + arousal (motor cortex is active during movement)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        sensorimotor_cortex_input = intent_strength * (0.5 + arousal * 0.5)
        sensorimotor_cortex_input = max(0.0, min(1.0, sensorimotor_cortex_input))

        # D2 indirect pathway activity in matrix (suppression of competitors)
        indirect = prior.get("IndirectPathwaySuppressor", {})
        if isinstance(indirect, dict):
            d2_activity = indirect.get("suppression_strength", 0.0)
        else:
            d2_activity = 0.0

        # D1 direct pathway activity in matrix (facilitation of selected action)
        direct = prior.get("DirectPathwayDisinhibitor", {})
        if isinstance(direct, dict):
            d1_activity = direct.get("disinhibition_strength", 0.0)
        else:
            d1_activity = 0.0

        # Motor value signal: combines sensorimotor input with DA reward signal
        # Positive prediction error = reward → strengthen sensorimotor association
        pe = prior.get("PredictionErrorDrift", {}).get("prediction_error", 0.0)
        reward_signal = max(0, pe) if isinstance(pe, (int, float)) else 0.0

        # Motor value: sensorimotor cortical drive * reward + D1 contribution
        motor_value = (
            sensorimotor_cortex_input * 0.4
            + d1_activity * 0.25
            + reward_signal * 0.35
        )
        motor_value = max(0.0, min(1.0, motor_value))

        # Habitual bias: increases when the same action is repeated
        # Well-learned actions in matrix become automatic (habit formation)
        action_map = {
            "connection": "social_action",
            "curiosity": "exploratory_action",
            "expression": "creative_action",
            "rest": "maintenance_action",
            "stability": "protective_action",
        }
        current_action = action_map.get(drive, "general_action")

        history = list(self.state.get("sensorimotor_history", []))
        recent_actions = [a for a in history[-5:] if a == current_action]
        repeated_count = len(recent_actions) + 1

        # Habitual bias: more repetition = stronger habit signal
        # But habits need reward confirmation to consolidate
        habitual_factor = min(1.0, repeated_count / 6.0)
        if reward_signal > 0.1:
            # Positive reward reinforces habit
            target_habitual = habitual_factor
        else:
            # Without reward, habit doesn't strengthen
            target_habitual = self.state["habitual_bias"] * (1.0 - self.HABITUAL_DECAY_RATE)
        habitual_bias = max(0.0, min(1.0, target_habitual))

        # Sensorimotor weight: how much matrix is contributing to motor output
        # High when sensorimotor cortex is active and D1/D2 are both engaged
        sensorimotor_weight = (
            sensorimotor_cortex_input * 0.3
            + d1_activity * 0.3
            + d2_activity * 0.2
            + habitual_bias * 0.2
        )
        sensorimotor_weight = max(0.0, min(1.0, sensorimotor_weight))

        # Update history
        history.append(current_action)
        if len(history) > 10:
            history = history[-10:]

        self.state["motor_value_signal"] = round(motor_value, 4)
        self.state["habitual_bias"] = round(habitual_bias, 4)
        self.state["sensorimotor_weight"] = round(sensorimotor_weight, 4)
        self.state["last_action"] = current_action
        self.state["repeated_action_count"] = repeated_count
        self.state["sensorimotor_history"] = history
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "motor_value_signal": round(motor_value, 4),
            "habitual_bias": round(habitual_bias, 4),
            "sensorimotor_weight": round(sensorimotor_weight, 4),
            # Internal debug:
            "_sensorimotor_cortex_input": round(sensorimotor_cortex_input, 4),
            "_d1_activity": round(d1_activity, 4),
            "_d2_activity": round(d2_activity, 4),
            "_reward_signal": round(reward_signal, 4),
            "_repeated_action_count": repeated_count,
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

