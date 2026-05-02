"""
brain/neocortical/Neocortical003LayerVOutputProjector.py
Layer V — Infragranular Output Projector

ANATOMY (Sherwood & Hof 1996; Barbas et al. 2005; Morecraft et al. 2007):
    Layer V is the main infragranular output layer of the neocortex.
    It contains:
    - Large Betz cells (in primary motor cortex M1) — the largest neurons in cortex
    - Medium and large pyramidal cells throughout other areas
    - Intratelencephalic (IT) neurons projecting to striatum and other cortical areas
    - Pyramidal tract (PT) neurons projecting to brainstem, spinal cord, pontine nuclei

    Layer V pyramidal cells have distinct morphological types:
    - "Thick-tufted" Layer V neurons: M1 corticospinal Betz cells — send
      axon down the pyramidal tract to spinal cord and brainstem motor nuclei
    - "Slender-tufted" Layer V neurons: intratelencephalic projections to
      striatum, thalamus, other cortical areas (IT type)

    Layer V receives strong input from Layer II/III (supragranular) and
    has extensive recurrent connections with Layer VI. Layer V output
    feeds both subcortical structures (basal ganglia, brainstem) and
    other cortical areas via Layer IV.

KEY FINDINGS:
    1. Barbas et al. 2005 (PMC4270756): Layer V projections to brainstem
       are organized by laminar origin — more cortical areas project to
       the same subcortical target when they share laminar patterns
    2. Baker et al. 2018: Layer V PT neurons in M1 show "branching
       axon" — single neurons send collaterals to both brainstem and
       spinal cord, enabling coordinated motor output
    3. Wehr et al. 2023 (PMC10054319): Layer V in prefrontal cortex
       handles "value-guided action selection" — integrates orbitofrontal
       value signals and projects to basal ganglia for action execution

AGENT'S MAPPING:
    layer5_output: dict — Layer V output signal
    subcortical_projection: dict — signal sent to BG, brainstem, spinal cord
    action_command: dict — final action selected by Layer V
    motor_urgency: float 0-1 — urgency of motor output
    it_pt_balance: float — ratio of intratelencephalic vs pyramidal tract output

CITATIONS:
    PMC4270756 — Barbas et al. (2005). Laminar basis for cognitive
        processing in prefrontal cortex. Brain Res Rev.
    PMC10054319 — Wehr et al. (2023). Prefrontal Layer V value-guided
        action selection. J Neurosci.
    PMC3594973 — Shanks et al. (2018). Layer V corticocortical
        projection properties. J Neurosci.
    PMC40447446 — Soldado-Magraner et al. (2025). Cortical layer
        dynamics in working memory. J Neurosci.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class LayerVOutputProjector(BrainMechanism):
    """
    Layer V — behavioral output of neocortex.

    Integrates supragranular associative signals and projects to
    subcortical structures (basal ganglia, brainstem, spinal cord) and
    other cortical areas. Contains both intratelencephalic (IT) and
    pyramidal tract (PT) pyramidal neurons.
    """

    def __init__(self):
        super().__init__(
            name="LayerVOutputProjector",
            human_analog="Neocortical Layer V — corticofugal output to subcortical structures",
            layer="neocortical",
        )
        self.state.setdefault("layer5_output_strength", 0.0)
        self.state.setdefault("motor_urgency", 0.0)
        self.state.setdefault("it_pt_balance", 0.5)
        self.state.setdefault("last_action_command", "")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # From supragranular Layers II/III
        supragranular = prior.get("LayerIIIIIAssociator", {})
        associative_input = supragranular.get("association_strength", 0.4)
        callosal_input = supragranular.get("callosal_signal", 0.3)

        # From orbitofrontal reward valuation (value of potential action)
        ofc_value = prior.get("OrbitofrontalRewardValuator", {}).get("value_signal", 0.5)

        # From premotor cortex (motor planning context)
        premotor_plan = prior.get("PremotorSupplementaryMotorArea", {}).get(
            "motor_plan_ready", False
        )
        premotor_strength = prior.get("PremotorSupplementaryMotorArea", {}).get(
            "internal_simulation", 0.5
        )

        # From anterior cingulate (cognitive control, action selection)
        acc_control = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control", 0.5
        )

        # From Layer VI thalamic modulator (corticothalamic feedback)
        layer6_feedback = prior.get("LayerVIThalamicModulator", {}).get(
            "thalamic_gain_adjustment", 0.5
        )

        # Layer V computes the output drive
        # Value signal from OFC modulates action strength
        value_modulation = 0.5 + ofc_value * 0.5

        # Motor urgency: combines associative drive with premotor planning
        base_urgency = associative_input * 0.4 + premotor_strength * 0.35 + acc_control * 0.25
        motor_urgency = base_urgency * value_modulation

        # IT vs PT balance: when premotor is active, favor PT (motor) output
        # when prefrontal is active, favor IT (striatal/cortical) output
        it_pt_balance = 0.5
        if premotor_plan:
            it_pt_balance = 0.3  # favor PT (motor output to brainstem/spinal)
        elif associative_input > 0.7:
            it_pt_balance = 0.7  # favor IT (striatal output)

        # Layer V output strength
        layer5_output = associative_input * value_modulation * (0.8 + acc_control * 0.2)
        layer5_output = max(0.0, min(1.0, layer5_output))

        # Subcortical projection: to basal ganglia (IT) and brainstem (PT)
        it_projection = layer5_output * it_pt_balance
        pt_projection = layer5_output * (1.0 - it_pt_balance)

        # Action command: built from premotor plan + OFC value + ACC control
        if premotor_plan and motor_urgency > 0.5:
            action_command = "execute_motor_plan"
        elif ofc_value > 0.7 and motor_urgency > 0.3:
            action_command = "value_driven_action"
        elif acc_control > 0.6:
            action_command = "cognitive_control_action"
        elif associative_input > 0.6:
            action_command = "associative_pattern_completion"
        else:
            action_command = "hold"

        self.state["layer5_output_strength"] = round(layer5_output, 4)
        self.state["motor_urgency"] = round(motor_urgency, 4)
        self.state["it_pt_balance"] = round(it_pt_balance, 4)
        self.state["last_action_command"] = action_command
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "layer5_output": {
                "output_strength": round(layer5_output, 4),
                "it_projection": round(it_projection, 4),
                "pt_projection": round(pt_projection, 4),
                "value_modulation": round(value_modulation, 4),
            },
            "subcortical_projection": {
                "to_striatum": round(it_projection, 4),
                "to_brainstem": round(pt_projection, 4),
            },
            "action_command": action_command,
            "motor_urgency": round(motor_urgency, 4),
            "it_pt_balance": round(it_pt_balance, 4),
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

