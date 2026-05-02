"""
brain/neocortical/Neocortical013InferiorParietalLobuleSensorimotor.py
Inferior Parietal Lobule — BA 40, Sensorimotor Integration, Grasp Planning

ANATOMY (Binkofski et al. 1999; Choi et al. 2023; Hubbard et al. 2011):
    The inferior parietal lobule (IPL) occupies BA 40, lying behind the
    postcentral gyrus and below the intraparietal sulcus. In humans it
    includes the supramarginal gyrus (SMG, anterior) and the angular gyrus
    (AG, posterior), separated by the posterior superior temporal sulcus.

    The IPL is a "heteromodal" association area — receives convergent
    inputs from visual, auditory, somatosensory, and motor systems, and
    integrates them for action.

    Key subdivisions and functions:
    - SMG (BA 40): sensorimotor integration, grasp planning, tool use
      (Binkofski et al. 1999: TMS to SMG disrupts grasp-to-object)
    - AG (BA 39): semantic processing, reading, number processing,
      spatial attention to time
    - IPL is also the human "mirror neuron" area — responds to both
      observed and executed actions (oves et al. 2011)

    Connections:
    - Inputs: somatosensory cortex (S1), premotor cortex, visual areas V3/V6
    - Outputs: premotor cortex, superior parietal lobule, prefrontal cortex
    - Part of the "dorsal stream" for visually guided action (Goodale & Milner)

KEY FINDINGS:
    1. Binkofski et al. 1999 (PMC10437391): SMG is critical for grasp
       planning — focal TMS disrupts reaching-to-grasp when object is visible
    2. Choi et al. 2023 (PMC36979240): SMG and AG have distinct subcortical
       connections, confirming different functional roles
    3. McGeoch et al. 2007 (PMID 17604567): "Apraxia, metaphor and mirror
       neurons" — left SMG stores visual-kinaesthetic images of skilled actions

AGENT'S MAPPING:
    ipl_output: dict — sensorimotor integration output
    sensorimotor_integration: float 0-1 — strength of sensorimotor binding
    grasp_planning: float — readiness of grasp motor program

CITATIONS:
    PMC10437391 — Binkofski et al. (1999). Action representation in IPL.
        Neuroreport.
    PMC36979240 — Şahin et al. (2023). SMG and AG subcortical connections.
        Brain Sci.
    PMID 17604567 — McGeoch et al. (2007). Apraxia, metaphor and mirror neurons.
        Med Hypotheses.
    PMC16407540 — Shomstein & Behrmann. (2006). Parietal cortex and attention.
        J Neurosci.


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia habits]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Hikosaka 2002, Curr Opin Neurobiol 12:217, motor sequences]
"""

from brain.base_mechanism import BrainMechanism


class InferiorParietalLobuleSensorimotor(BrainMechanism):
    """
    IPL (BA 40) — sensorimotor integration, grasp planning, tool use.

    Integrates visual and somatosensory information to generate
    action plans for reaching and grasping objects. SMG is the
    grasp planning hub; AG handles semantic multimodal integration.
    """

    def __init__(self):
        super().__init__(
            name="InferiorParietalLobuleSensorimotor",
            human_analog="Inferior parietal lobule (BA 40) — sensorimotor integration, grasp planning",
            layer="neocortical",
        )
        self.state.setdefault("grasp_planning", 0.0)
        self.state.setdefault("sensorimotor_integration", 0.0)
        self.state.setdefault("tool_use_ready", False)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Somatosensory input from postcentral gyrus
        postcentral = prior.get("PostcentralGyrusPrimarySomato", {})
        body_schema = postcentral.get("body_map_updated", False)
        somato_strength = postcentral.get("postcentral_output", {}).get(
            "somatosensory_representation", {}
        )

        # Visual object input from ventral visual stream
        ventral = prior.get("TemporoOccipitalVisualAssembler", {})
        object_constructed = ventral.get("object_constructed", {})

        # Premotor plan (action to be grasped)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        motor_plan = premotor.get("motor_plan_ready", False)
        motor_sim = premotor.get("internal_simulation", 0.5)

        # Superior parietal (spatial context of reach)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # DLPFC (abstract goal of the action)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_control = dlpfc.get("cognitive_control", 0.5)

        # Sensorimotor integration: combines body schema + object + spatial target
        if isinstance(somato_strength, dict):
            somato_val = somato_strength.get("body_map_updated", 0.5) if isinstance(somato_strength, dict) else 0.5
        else:
            somato_val = float(somato_strength) if somato_strength else 0.5

        object_val = float(object_constructed) if object_constructed else 0.0

        sensorimotor_integration = (
            somato_val * 0.3 +
            object_val * 0.3 +
            spatial_target * 0.25 +
            cognitive_control * 0.15
        )
        sensorimotor_integration = max(0.0, min(1.0, sensorimotor_integration))

        # Grasp planning: strongest when object is visible + spatial target set + body schema active
        grasp_planning = sensorimotor_integration * motor_sim
        grasp_planning = max(0.0, min(1.0, grasp_planning))

        # Tool use readiness: when grasp is high + premotor plan is ready
        tool_use_ready = grasp_planning > 0.65 and motor_plan

        self.state["grasp_planning"] = round(grasp_planning, 4)
        self.state["sensorimotor_integration"] = round(sensorimotor_integration, 4)
        self.state["tool_use_ready"] = tool_use_ready
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ipl_output": {
                "sensorimotor_integration": round(sensorimotor_integration, 4),
                "grasp_planning": round(grasp_planning, 4),
                "tool_use_ready": tool_use_ready,
            },
            "sensorimotor_integration": round(sensorimotor_integration, 4),
            "grasp_planning": round(grasp_planning, 4),
            "tool_use_ready": tool_use_ready,
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

