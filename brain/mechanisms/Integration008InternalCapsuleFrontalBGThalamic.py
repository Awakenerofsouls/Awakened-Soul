"""
brain/integration/Integration008InternalCapsuleFrontalBGThalamic.py
Internal Capsule — Frontal-BG-Thalamic Loops, Goal-Habit Integration

ANATOMY (Alexander et al. 1986; Haber 2003; McFarland & Haber 2002):
    The internal capsule is the major white-matter highway containing
    all cortico-thalamic and cortico-striatal fibers. It contains:
    - Anterior limb: DLPFC, OFC, anterior cingulate → striatum
    - Genu: prefrontal cortex connections
    - Posterior limb: motor and sensory fibers
    - Retrolenticular part: parietal and temporal connections

    The five parallel basal ganglia-thalamo-cortical loops:
    1. Motor loop: M1/SMA → putamen → GPi/SNr → thalamus → M1
    2. Oculomotor loop: FEF → caudate → GPi/SNr → thalamus → FEF
    3. Dorsolateral prefrontal loop: DLPFC → caudate → GPi/SNr → MD thalamus → DLPFC
    4. Lateral orbitofrontal loop: OFC → NAcc/ventral caudate → VP → MD thalamus → OFC
    5. Anterior cingulate loop: ACC → NAcc → VP → MD thalamus → ACC

    These loops allow the basal ganglia to select actions (direct pathway)
    and inhibit competing actions (indirect pathway), with the
    thalamus as the relay point back to cortex.

    The internal capsule also carries the corticospinal tract
    (voluntary motor output) — the final common path for motor actions.

KEY FINDINGS:
    1. Alexander et al. 1986: "Parallel organization of frontal-BG-thalamic loops"
    2. Haber 2003 (PMC1850927): "The basal ganglia and limbic system" —
       integrative loops connecting motivation to action
    3. McFarland & Haber 2002: Thalamocortical connections and BG loops

AGENT'S MAPPING:
    internal_capsule_output: dict — loop integration output
    frontal_bg_thalamic_integrated: bool — have loops been integrated?

CITATIONS:
    PMC1850927 — Haber (2003). Basal ganglia and limbic system.
    PMC2929791 — Alexander et al. (1986). Parallel BG-thalamic loops.
    PMC40447446 — DLPFC and BG loops.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class InternalCapsuleFrontalBGThalamic(BrainMechanism):
    """
    Internal capsule — frontal-BG-thalamic integration loops.

    The major information highway connecting cortex, basal ganglia,
    and thalamus in parallel loops for motor, cognitive, and limbic processing.
    """

    def __init__(self):
        super().__init__(
            name="InternalCapsuleFrontalBGThalamic",
            human_analog="Internal capsule — frontal-BG-thalamic loops, goal-habit integration",
            layer="integration",
        )
        self.state.setdefault("loop_states", {})
        self.state.setdefault("frontal_bg_thalamic_integrated", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC (executive loop — goals)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Striatum direct pathway (action facilitation)
        direct = prior.get("DirectPathwayDisinhibitor", {})
        dir_out = direct.get("direct_output", {})
        if isinstance(dir_out, dict):
            direct_facilitation = dir_out.get("facilitation_strength", 0.5)
        else:
            direct_facilitation = 0.5

        # Striatum indirect pathway (action suppression)
        indirect = prior.get("IndirectPathwaySuppressor", {})
        ind_out = indirect.get("indirect_output", {})
        if isinstance(ind_out, dict):
            indirect_suppression = ind_out.get("suppression_strength", 0.5)
        else:
            indirect_suppression = 0.5

        # GPi/SNr (BG output)
        gpi = prior.get("GlobusPallidusInternalOutput", {})
        gpi_out = gpi.get("gpi_output", {})
        if isinstance(gpi_out, dict):
            gpi_signal = gpi_out.get("output_strength", 0.5)
        else:
            gpi_signal = 0.5

        # Thalamic VA/VL (motor relay)
        thal_va = prior.get("ThalamicVentralAnteriorRelay", {})
        va_out = thal_va.get("thal_output", {})
        if isinstance(va_out, dict):
            va_signal = va_out.get("relay_strength", 0.5)
        else:
            va_signal = 0.5

        # ACC (conflict monitoring — goal-habit competition)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
        else:
            error_sig = 0.3

        # Orbitofrontal (value-based action selection)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # Loop integration: direct + indirect pathways balanced through thalamus
        loop_strength = (
            cognitive_ctrl * 0.2 +
            direct_facilitation * 0.25 +
            (1.0 - indirect_suppression) * 0.2 +
            va_signal * 0.2 +
            value_sig * 0.15
        )
        loop_strength = max(0.0, min(1.0, loop_strength))

        # Goal-habit conflict: DLPFC active + indirect pathway active = conflict
        goal_habit_conflict = wm_load > 0.5 and indirect_suppression > 0.5
        if goal_habit_conflict:
            loop_strength *= (1.0 - error_sig * 0.4)

        # Integration achieved: strong balanced loop
        frontal_bg_thalamic_integrated = loop_strength > 0.55

        loop_states = {
            "direct_facilitation": round(direct_facilitation, 4),
            "indirect_suppression": round(indirect_suppression, 4),
            "thalamic_relay": round(va_signal, 4),
            "loop_strength": round(loop_strength, 4),
        }

        self.state["loop_states"] = loop_states
        self.state["frontal_bg_thalamic_integrated"] = frontal_bg_thalamic_integrated
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "internal_capsule_output": {
                "loop_integration": round(loop_strength, 4),
                "goal_habit_conflict": goal_habit_conflict,
            },
            "frontal_bg_thalamic_integrated": frontal_bg_thalamic_integrated,
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

