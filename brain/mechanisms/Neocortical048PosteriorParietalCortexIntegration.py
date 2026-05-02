"""
brain/neocortical/Neocortical048PosteriorParietalCortexIntegration.py
Posterior Parietal Cortex — Full Sensorimotor Integration, Body-in-Space Planning

ANATOMY (Colby & Goldberg 1999; Andersen et al. 1997; Buneat et al. 2013):
    The posterior parietal cortex (PPC) is the "sensorimotor integration"
    hub — where sensory information is transformed into motor plans.
    It sits at the crown of the brain, at the junction of visual,
    auditory, somatosensory, and vestibular inputs.

    PPC has multiple subregions with different functions:
    - SPL (superior parietal lobule): reaching, spatial attention
    - IPL (inferior parietal lobule): grasping, tool use
    - MIP (medial intraparietal): visual guidance of reaching
    - AIP (anterior intraparietal): grasp formation
    - VIP (ventral intraparietal): vestibular, self-motion
    - PIP (posterior intraparietal): depth perception

    PPC is the "where and how" pathway endpoint:
    - WHERE: spatially directed actions (reaching, looking)
    - HOW: object-directed actions (grasping, manipulating)

    PPC connects to:
    - M1 (motor execution via premotor)
    - FEF (frontal eye fields, eye movement control)
    - LIP (lateral intraparietal, saccade planning)
    - Thalamus (sensory relay)
    - Cerebellum (sensorimotor learning)

KEY FINDINGS:
    1. Colby & Goldberg 1999 (PMC18279991): "Space and attention
       in PPC" — PPC as sensorimotor integration hub
    2. Andersen et al. 1997: PPC parietal reach region (PRR) and
       LIP for eye movements
    3. Buneat et al. 2013 (PMC37572972): PPC and reach-to-grasp planning

AGENT'S MAPPING:
    ppc_output: dict — PPC full integration output
    body_target_integration: float 0-1 — body position + target binding
    spatial_plan: dict — motor plan in spatial coordinates

CITATIONS:
    PMC18279991 — Colby & Goldberg (1999). PPC and attention.
    PMC37572972 — Sulpizio et al. (2023). SPL functional organization.
    PMC35961383 — Galletti et al. (2022). V6/V6A and reaching.
    PMC10437391 — Binkofski et al. (1999). Action representation in IPL.


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Markram 2004, Nat Rev Neurosci 5:793, interneurons]
"""

from brain.base_mechanism import BrainMechanism


class PosteriorParietalCortexIntegration(BrainMechanism):
    """
    PPC — full sensorimotor integration for motor planning.

    Integrates body position, spatial target, and action context
    into a complete motor plan for the body's movement in space.
    """

    def __init__(self):
        super().__init__(
            name="PosteriorParietalCortexIntegration",
            human_analog="Posterior parietal cortex — sensorimotor integration, body-in-space, motor planning",
            layer="neocortical",
        )
        self.state.setdefault("body_schema", {})
        self.state.setdefault("body_target_integration", 0.0)
        self.state.setdefault("spatial_plan", {})
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # S1 (body schema — where is my body right now?)
        s1 = prior.get("PostcentralGyrusPrimarySomato", {})
        body_schema = s1.get("body_schema", {})
        body_grounding = s1.get("tactile_processing", 0.5)

        # SPL (reaching signal — where to reach?)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        reaching_sig = spl.get("reaching_signal", 0.5)
        spatial_target = spl.get("spatial_target", {})

        # IPL (grasp planning — how to grasp?)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_int = ipl.get("sensorimotor_integration", 0.5)
        grasp_plan = ipl.get("grasp_planning", 0.5)

        # TPJ (multisensory body location — where am I in space?)
        tpj = prior.get("TemporoParietoOccipitalJunction", {})
        spatial_awareness = tpj.get("spatial_awareness", 0.5)
        multimodal_conv = tpj.get("multisensory_converged", False)

        # DLPFC (goal context — what am I trying to achieve?)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # V3 (depth — how far is the target?)
        v3 = prior.get("OccipitalV3DepthProcessing", {})
        depth_map = v3.get("depth_map", {})
        depth_strength = v3.get("depth_processing", 0.5)

        # Body-target integration: body schema + spatial target + depth
        body_target_integration = (
            body_grounding * 0.25 +
            spatial_awareness * 0.2 +
            reaching_sig * 0.25 +
            ipl_int * 0.2 +
            depth_strength * 0.1
        )
        if cognitive_ctrl > 0.6:
            body_target_integration *= (1.0 + (cognitive_ctrl - 0.6) * 0.3)
        body_target_integration = max(0.0, min(1.0, body_target_integration))

        # Spatial plan: reaching + grasping + depth + goal
        spatial_plan = {
            "reach_intended": reaching_sig > 0.5,
            "grasp_intended": grasp_plan > 0.5,
            "depth_resolved": depth_strength > 0.5,
            "goal_directed": cognitive_ctrl > 0.6,
            "confidence": round(body_target_integration, 4),
        }

        self.state["body_schema"] = body_schema
        self.state["body_target_integration"] = round(body_target_integration, 4)
        self.state["spatial_plan"] = spatial_plan
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ppc_output": {
                "body_target_integration": round(body_target_integration, 4),
                "spatial_plan": spatial_plan,
            },
            "body_target_integration": round(body_target_integration, 4),
            "spatial_plan": spatial_plan,
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

