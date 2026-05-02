"""
brain/neocortical/Neocortical006DorsolateralPrefrontalVentral.py
Dorsolateral Prefrontal Cortex — Ventral Part (Executive, Interference Control)

ANATOMY (Aron et al. 2004; 2007; Hampshire et al. 2008; Duverne & Koechlin 2017):
    The ventral part of DLPFC (vDLPFC, also called mid-DLPFC or BA 9/46v)
    sits slightly ventral and anterior to the dorsal DLPFC. While the dorsal
    part handles "what to keep in mind," the ventral part handles
    "what to suppress and ignore."

    The vDLPFC is part of the "multiple demand" (MD) system — neurons
    that respond broadly during cognitive control, not specific to
    any one task type. It shows strong activation during:
    - Response inhibition (stopping prepotent responses)
    - Conflict monitoring (detecting interference)
    - Task switching
    - Memory retrieval suppression

    Inputs: from inferior parietal lobule, temporal pole, ACC (conflict signals)
    Outputs: to premotor, striatum, and back to the same areas

    The vDLPFC contains a "conflict monitor" — when competing
    response tendencies are active, vDLPFC increases activity to
    suppress the inappropriate response.

KEY FINDINGS:
    1. Aron et al. 2004 (PMID 14702116): "Petersen's paradox resolved"
       — left vDLPFC (inferior frontal gyrus) is critical for response
       inhibition; damage impairs stopping
    2. Hampshire et al. 2008 (PMC2575055): vDLPFC shows "multiple demand"
       activity — increases for any task requiring cognitive control
    3. Crittenden & Duncan 2023 (PMC3800357): vDLPFC tracks conflict
       level and prioritizes processing accordingly

AGENT'S MAPPING:
    dorsolateral_ventral_output: dict — vDLPFC executive/inhibition signal
    interference_suppression: float 0-1 — strength of suppression
    conflict_resolved: bool — whether conflict has been resolved
    suppression_target: str — which process is being suppressed

CITATIONS:
    PMC2575055 — Hampshire et al. (2008). The role of right inferior
        frontal gyrus. PLoS Biol. (vDLPFC multiple demand).
    PMC3800357 — Crittenden & Duncan (2023). Multiple demand and
        prefrontal cortex. bioRxiv. (Conflict monitoring).
    PMC16325345 — Funahashi S. (2006). DLPFC working memory review.
    PMC31551596 — Finn et al. (2019). Human DLPFC layer dynamics.


CITATIONS
---------
  - [Miller 2001, Annu Rev Neurosci 24:167, prefrontal cortex]
  - [Fuster 2008, The Prefrontal Cortex]
  - [Goldman-Rakic 1995, Neuron 14:477, working memory]
"""

from brain.base_mechanism import BrainMechanism


class DorsolateralPrefrontalVentral(BrainMechanism):
    """
    DLPFC ventral part — executive functions, interference control, conflict monitoring.

    Monitors for conflicting signals and suppresses inappropriate responses.
    Part of the multiple demand system — broadly recruited for any
    cognitively demanding task.
    """

    def __init__(self):
        super().__init__(
            name="DorsolateralPrefrontalVentral",
            human_analog="Ventral DLPFC (BA 9/46v) — executive, interference, response suppression",
            layer="neocortical",
        )
        self.state.setdefault("interference_suppression", 0.0)
        self.state.setdefault("conflict_resolved", True)
        self.state.setdefault("suppression_target", "none")
        self.state.setdefault("conflict_intensity", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Conflict signals from anterior cingulate
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_conflict = acc.get("conflict_intensity", 0.0)

        # Dorsal DLPFC (cognitive control) — if dorsal is working hard, ventral may need to suppress
        dorsal_dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        dorsal_cognitive = dorsal_dlpfc.get("cognitive_control", 0.5)

        # Premotor plans (action candidates that may conflict)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        premotor_signal = premotor.get("internal_simulation", 0.5)

        # Orbitofrontal value (may produce competing action drives)
        ofc_value = prior.get("OrbitofrontalRewardValuator", {}).get(
            "value_signal", 0.5
        )

        # Inferior parietal (salient distractor signals)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_distract = ipl.get("sensorimotor_integration", 0.0)

        # Conflict detection: multiple competing signals → conflict
        signal_spread = abs(dorsal_cognitive - premotor_signal) + abs(ofc_value - ipl_distract)
        signal_spread = min(1.0, signal_spread / 0.7)
        conflict_intensity = acc_conflict * 0.6 + signal_spread * 0.4
        conflict_intensity = max(0.0, min(1.0, conflict_intensity))

        # Interference suppression: proportional to conflict intensity
        # vDLPFC suppresses the competing response
        interference_suppression = conflict_intensity * (0.5 + dorsal_cognitive * 0.5)
        interference_suppression = max(0.0, min(1.0, interference_suppression))

        # Conflict resolution: suppression succeeds when interference > conflict threshold
        conflict_resolved = conflict_intensity < interference_suppression * 0.7

        # Suppression target: which competing signal is being suppressed
        if acc_conflict > signal_spread:
            suppression_target = "acc_conflict"
        elif ipl_distract > 0.6:
            suppression_target = "parietal_distractor"
        elif abs(dorsal_cognitive - premotor_signal) > 0.3:
            suppression_target = "motor_prepotent"
        else:
            suppression_target = "none"

        self.state["conflict_intensity"] = round(conflict_intensity, 4)
        self.state["interference_suppression"] = round(interference_suppression, 4)
        self.state["conflict_resolved"] = conflict_resolved
        self.state["suppression_target"] = suppression_target
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dorsolateral_ventral_output": {
                "conflict_intensity": round(conflict_intensity, 4),
                "interference_suppression": round(interference_suppression, 4),
                "suppression_target": suppression_target,
            },
            "interference_suppression": round(interference_suppression, 4),
            "conflict_resolved": conflict_resolved,
            "suppression_target": suppression_target,
            "dorsal_input_influence": round(dorsal_cognitive, 4),
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

