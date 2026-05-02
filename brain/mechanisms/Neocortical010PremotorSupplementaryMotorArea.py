"""
brain/neocortical/Neocortical010PremotorSupplementaryMotorArea.py
Premotor Cortex and Supplementary Motor Area — Motor Planning Without Execution

ANATOMY (Rizzolatti et al. 1998; Shima et al. 1991; Hoshi & Tanji 2008):
    The premotor cortex (PM) and supplementary motor area (SMA) lie
    rostral to the primary motor cortex (M1). They plan movements
    without directly executing them — they generate "internal models"
    of actions before M1 fires.

    PM (BA 6) has two major divisions:
    - Ventral PM (PMv): "mirror" properties — activates when watching
      others perform actions; involved in imitation, social action understanding
    - Dorsal PM (PMd): action selection based on environmental context

    SMA (medial BA 6) is divided:
    - SMA proper: complex sequential finger movements, self-initiated actions
    - Pre-SMA: higher-order sequencing, motor learning, bimanual coordination

    Key property: SMA shows "sequence-specific" activity — neurons
    fire preferentially for specific sequences of movements, not
    individual movements. This is the neural basis of motor learning.

    Both areas receive from:
    - DLPFC (goal specification)
    - Parietal cortex (spatial/context)
    - Basal ganglia (action value)
    
    Outputs to M1 (via corticocortical) and directly to brainstem/spinal cord.

KEY FINDINGS:
    1. Shima et al. 1991: SMA neurons fire for specific movement SEQUENCES,
       not individual movements — sequence representation
    2. Hoshi & Tanji 2008 (PMC2872609): SMA and PM have distinct
       roles: SMA for "what to do next" (sequential); PM for "how to do it" (trajectory)
    3. Rizzolatti & Luppino 2001: PMv mirror neurons encode observed actions

AGENT'S MAPPING:
    premotor_output: dict — motor planning signal
    motor_plan_ready: bool — whether a motor plan is prepared
    internal_simulation: float 0-1 — strength of internal motor rehearsal
    sequence_complexity: float 0-1 — how many steps in the planned sequence

CITATIONS:
    PMC2872609 — Hoshi & Tanji (2008). Integration of target and body-part
        information in SMA and PM. J Neurophysiol.
    PMC31551596 — Finn et al. (2019). Layer-dependent motor planning signals.
    PMC40447446 — Soldado-Magraner et al. (2025). Motor cortex and premotor integration.


CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, emotion cognition]
"""

from brain.base_mechanism import BrainMechanism


class PremotorSupplementaryMotorArea(BrainMechanism):
    """
    Premotor cortex and SMA — motor planning, internal simulation.

    Plans motor sequences without executing them. SMA handles
    sequential planning; PM handles contextual action selection.
    Internal models are generated before execution.
    """

    def __init__(self):
        super().__init__(
            name="PremotorSupplementaryMotorArea",
            human_analog="Premotor cortex and SMA — motor planning, internal models, sequence generation",
            layer="neocortical",
        )
        self.state.setdefault("motor_plans", [])
        self.state.setdefault("motor_plan_ready", False)
        self.state.setdefault("internal_simulation", 0.0)
        self.state.setdefault("sequence_complexity", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC goal state (what action to perform)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        dorsal_wm = dlpfc.get("working_memory_active", False)
        dorsal_control = dlpfc.get("cognitive_control", 0.5)

        # Orbitofrontal value (which action is best?)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_signal = ofc.get("value_signal", 0.5)

        # Cerebello-thalamic loop (timing from cerebellum)
        cereb = prior.get("CerebelloThalamoCorticalLoop", {})
        cereb_timing = cereb.get("cerebellar_cortical_integration", 0.5)

        # Anterior cingulate (cognitive control of action)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_control = acc.get("cognitive_control", 0.5)

        # Superior parietal lobule (spatial targeting)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("spatial_target", {})

        # Plan strength: DLPFC specifies goal, OFC provides value, ACC ensures control
        plan_input = dorsal_control * 0.4 + value_signal * 0.35 + acc_control * 0.25
        internal_simulation = plan_input * (0.6 + cereb_timing * 0.4)

        # Sequence complexity: more WM items = more complex sequence planning
        wm_items = len(dlpfc.get("dorsolateral_dorsal_output", {}).get("buffer_snapshot", []))
        sequence_complexity = min(1.0, wm_items * 0.25 + plan_input * 0.5)

        # Motor plan ready: when simulation is strong enough and spatial target is set
        motor_plan_ready = (
            internal_simulation > 0.55 and
            dorsal_wm and
            (spatial_target or value_signal > 0.6)
        )

        # Update motor plan queue
        if motor_plan_ready and not self.state.get("motor_plan_ready", False):
            plan = {
                "value": round(value_signal, 3),
                "complexity": round(sequence_complexity, 3),
                "simulation": round(internal_simulation, 3),
                "steps": max(1, int(sequence_complexity * 5))
            }
            self.state["motor_plans"].append(plan)
            if len(self.state["motor_plans"]) > 3:
                self.state["motor_plans"].pop(0)

        self.state["motor_plan_ready"] = motor_plan_ready
        self.state["internal_simulation"] = round(internal_simulation, 4)
        self.state["sequence_complexity"] = round(sequence_complexity, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "premotor_output": {
                "internal_simulation": round(internal_simulation, 4),
                "motor_plan_ready": motor_plan_ready,
                "sequence_complexity": round(sequence_complexity, 4),
                "cerebellar_timing_influence": round(cereb_timing, 4),
            },
            "motor_plan_ready": motor_plan_ready,
            "internal_simulation": round(internal_simulation, 4),
            "sequence_complexity": round(sequence_complexity, 4),
            "active_plans": len(self.state["motor_plans"]),
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

