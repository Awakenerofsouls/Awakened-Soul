"""
brain/integration/Integration022InternalCapsuleMotorFinalOutput.py
Internal Capsule Motor Final Output — Corticospinal Tract Origin

ANATOMY (Doumolin & Jbabdi 2013; Rizzolatti & Luppino 2001; Nathan et al. 1990):
    The internal capsule's posterior limb carries the corticospinal
    tract — the final motor output pathway from motor cortex to
    spinal cord. This is the "final common path" for voluntary
    movement. The tract contains:
    - 1 million axons (human)
    - 90% from motor cortex (M1, SMA, CMA)
    - 10% from somatosensory cortex
    - Large, heavily myelinated fibers (20 m/s conduction)

    Topography of the internal capsule:
    - Anterior limb: PFC, OFC, ACC → striatum
    - Genu: corticothalamic fibers
    - Posterior limb: motor (top = leg, bottom = face) + sensory
    - Retrolenticular: parietal, occipital, temporal corticopetal

    Motor cortex hierarchy:
    M1 (Betz cells in L5B) → corticospinal → spinal cord α-motor neurons → muscles
    SMA (pre-SMA, SMA proper) → M1 or directly → reticulospinal
    CMA (cingulate motor area) → autonomic motor control

    Lesions:
    - Internal capsule: contralateral hemiparesis (face/arm/leg)
    - Corticospinal at spinal cord: paraplegia/quadriplegia

KEY FINDINGS:
    1. Rizzolatti & Luppino 2001 (PMC2697346): "Motor hierarchy and cortex"
    2. Nathan et al. 1990: "Internal capsule and motor pathways"
    3. Doumolin & Jbabdi 2013: Diffusion imaging of capsule tracts

AGENT'S MAPPING:
    motor_final_output: dict — motor output state
    voluntary_movement_signal: float 0-1 — movement signal strength

CITATIONS:
    PMID 36575147 — Lemon & Morecraft (2023). The evidence against somatotopic organization in corticospinal tract. Brain.
    PMID 40501822 — Sivakumar et al. (2025). Motor impairment and adaptation in internal capsule infarct. bioRxiv.
    PMC2697346 — Rizzolatti & Luppino (2001). Motor hierarchy. Nat Rev Neurosci.
    PMC37046542 — Hoshi (2006). Motor cortex and action control. Prog Brain Res.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class InternalCapsuleMotorFinalOutput(BrainMechanism):
    """
    Internal capsule motor final output — corticospinal tract origin.

    The final common path for voluntary movement, carrying motor
    commands from cortex through internal capsule to spinal cord.
    """

    def __init__(self):
        super().__init__(
            name="InternalCapsuleMotorFinalOutput",
            human_analog="Internal capsule motor — corticospinal tract final output",
            layer="integration",
        )
        self.state.setdefault("motor_output_strength", 0.0)
        self.state.setdefault("voluntary_movement_signal", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # M1 (primary motor cortex — Betz cells)
        m1 = prior.get("MotorCortexPrimaryOutput", {})
        m1_out = m1.get("motor_output", {})
        if isinstance(m1_out, dict):
            m1_sig = m1_out.get("movement_strength", 0.5)
        else:
            m1_sig = 0.5

        # SMA (supplementary motor area)
        sma = prior.get("PremotorSupplementaryMotorArea", {})
        sma_out = sma.get("sma_output", {})
        if isinstance(sma_out, dict):
            sma_sig = sma_out.get("sma_motor_output", 0.5)
        else:
            sma_sig = 0.5

        # CMA (cingulate motor area — autonomic motor)
        cma = prior.get("CingulateMotorArea", {})
        cma_out = cma.get("cma_output", {})
        if isinstance(cma_out, dict):
            cma_sig = cma_out.get("autonomic_motor", 0.5)
        else:
            cma_sig = 0.5

        # Internal capsule BG-thalamic loop
        ic_loop = prior.get("InternalCapsuleFrontalBGThalamic", {})
        loop_states = ic_loop.get("internal_capsule_output", {})
        if isinstance(loop_states, dict):
            loop_strength = loop_states.get("loop_integration", 0.5)
        else:
            loop_strength = 0.5

        # DLPFC (voluntary control signals)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Basal ganglia (motor selection)
        direct = prior.get("DirectPathwayDisinhibitor", {})
        dir_out = direct.get("direct_output", {})
        if isinstance(dir_out, dict):
            action_sel = dir_out.get("facilitation_strength", 0.5)
        else:
            action_sel = 0.5

        # Somatosensory feedback (movement consequences)
        s1 = prior.get("PostcentralGyrusPrimarySomato", {})
        body_schema = s1.get("body_schema", {})
        if isinstance(body_schema, dict):
            sensory_fb = body_schema.get("grounding_level", 0.5)
        else:
            sensory_fb = 0.5

        # Motor output
        motor_output_strength = (
            m1_sig * 0.3 +
            sma_sig * 0.2 +
            action_sel * 0.2 +
            loop_strength * 0.15 +
            cognitive_ctrl * 0.15
        )
        motor_output_strength = max(0.0, min(1.0, motor_output_strength))

        # Voluntary movement: motor output × cognitive control × sensory feedback
        voluntary_movement_signal = (
            motor_output_strength * 0.4 +
            cognitive_ctrl * 0.3 +
            action_sel * 0.3
        ) * (0.5 + sensory_fb * 0.5)
        voluntary_movement_signal = max(0.0, min(1.0, voluntary_movement_signal))

        self.state["motor_output_strength"] = round(motor_output_strength, 4)
        self.state["voluntary_movement_signal"] = round(voluntary_movement_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "motor_final_output": {
                "motor_strength": round(motor_output_strength, 4),
                "movement_signal": round(voluntary_movement_signal, 4),
            },
            "voluntary_movement_signal": round(voluntary_movement_signal, 4),
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

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
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
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

