"""
AnteriorOlfactoryNucleus — AON / Bilateral Olfactory Bridge

NEURAL SUBSTRATE
================
The anterior olfactory nucleus (AON, also "anterior olfactory cortex")
sits at the rostral end of the olfactory cortex, immediately caudal to
the olfactory bulb. Receives bidirectional input from olfactory bulb
mitral/tufted cells. AON is the principal substrate for:
- Bilateral olfactory integration via anterior commissure
- Top-down feedback to OB (gain control on incoming odor signals)
- Odor recognition memory + familiarity
- Social olfactory recognition (rodents)

Three subdivisions: pars externa (lateral, AOB-adjacent), pars principalis
(main subdivision), and dorsal/ventral subregions. Pyramidal projection
neurons + GABAergic interneurons.

Outputs: bilateral OB feedback, piriform cortex, olfactory tubercle,
amygdala (via lateral olfactory tract collaterals).

KEY FINDINGS
============
1. AON pars externa is the principal bilateral olfactory integrator;
   contralateral connections via anterior commissure permit binaural
   odor comparison — [Yan 2008, J Neurosci 28:1683, PMID 18272689]
2. AON top-down projection to OB granule cells provides gain control
   on incoming odor signals; activity-dependent plasticity —
   [Markopoulos 2012, Neuron 76:1175, doi:10.1016/j.neuron.2012.10.028]
3. AON is critical for social olfactory recognition memory in rodents;
   selective lesion impairs familiarity discrimination —
   [Kogan 2000, Hippocampus 10:47, PMID 10706226]
4. AON neurons encode odor identity at single-cell resolution; population
   code distinct from OB — [Brunjes 2005, Brain Res Rev 50:305, PMID 16229896]
5. AON shows activity-dependent plasticity to repeated odor exposure;
   familiarity coding distinct from PIRiform cortex —
   [Kay 2003, Trends Neurosci 26:480, PMID 12948660]

INPUTS
======
- OlfactoryBulb.ob_drive
- PiriformCortex.pir_drive (feedback)
- AmygdalaCorticalAnterior.aco_drive (when present)
- ArousalRegulator.tonic_level

OUTPUTS
=======
- aon_drive (0-1)
- bilateral_integration_signal (0-1)
- ob_feedback_command (0-1) — top-down gain control
- olfactory_familiarity_signal (0-1)
- aon_state (str): "novel_odor" | "familiar_odor" |
  "social_recognition" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AnteriorOlfactoryNucleus(BrainMechanism):
    """AON — bilateral olfactory bridge + top-down OB feedback."""

    BASELINE = 0.10
    SMOOTH = 0.20
    NOVEL_THRESHOLD = 0.50
    FAMILIAR_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="AnteriorOlfactoryNucleus",
            human_analog="Anterior olfactory nucleus (bilateral olfactory)",
            layer="limbic",
        )
        self.state.setdefault("aon_drive", self.BASELINE)
        self.state.setdefault("bilateral_integration_signal", 0.0)
        self.state.setdefault("ob_feedback_command", 0.0)
        self.state.setdefault("olfactory_familiarity_signal", 0.0)
        self.state.setdefault("aon_state", "quiet")
        self.state.setdefault("recent_odors", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ob: float, pir: float, aco: float,
                       arousal: float) -> float:
        """AON firing — driven by OB primarily, modulated by feedback."""
        target = self.BASELINE + ob * 0.55 + pir * 0.20 + aco * 0.15
        target += max(0.0, arousal - 0.40) * 0.10
        return min(1.0, target)

    def _bilateral_integration(self, drive: float, ob: float) -> float:
        """Bilateral olfactory integration via anterior commissure
        (Yan 2008)."""
        return min(1.0, drive * 0.6 + ob * 0.4)

    def _ob_feedback(self, drive: float, familiarity: float) -> float:
        """Top-down OB granule-cell gain control (Markopoulos 2012)."""
        return min(1.0, drive * 0.5 + familiarity * 0.5)

    def _familiarity(self, ob: float, recent: list) -> float:
        """Olfactory familiarity (Kay 2003 activity-dependent plasticity)."""
        if ob < 0.20:
            return 0.5  # neutral
        if not recent:
            return 0.10
        similar = sum(1 for o in recent[-30:] if abs(o - ob) < 0.15)
        return min(1.0, 0.30 + similar * 0.05)

    def _classify_state(self, drive: float, familiarity: float, aco: float) -> str:
        if drive < 0.15:
            return "quiet"
        if aco > 0.40:
            return "social_recognition"
        if familiarity < 0.20:
            return "novel_odor"
        if familiarity > self.FAMILIAR_THRESHOLD:
            return "familiar_odor"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ob_data = prior.get("OlfactoryBulb", {})
        ob = float(ob_data.get("ob_drive", 0.0))

        pir_data = prior.get("PiriformCortex", {})
        pir = float(pir_data.get("pir_drive", 0.0))

        aco_data = prior.get("AmygdalaCorticalAnterior", {})
        aco = float(aco_data.get("aco_drive", 0.0))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        target = self._drive_target(ob, pir, aco, arousal)
        prev_drive = float(self.state.get("aon_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        recent = list(self.state.get("recent_odors", []))
        familiarity = self._familiarity(ob, recent)
        bilateral = self._bilateral_integration(new_drive, ob)
        feedback = self._ob_feedback(new_drive, familiarity)

        if ob > 0.20:
            recent.append(round(ob, 4))
        if len(recent) > 100:
            recent = recent[-100:]

        state = self._classify_state(new_drive, familiarity, aco)

        self.state["aon_drive"] = round(new_drive, 4)
        self.state["bilateral_integration_signal"] = round(bilateral, 4)
        self.state["ob_feedback_command"] = round(feedback, 4)
        self.state["olfactory_familiarity_signal"] = round(familiarity, 4)
        self.state["aon_state"] = state
        self.state["recent_odors"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "aon_drive": round(new_drive, 4),
            "bilateral_integration_signal": round(bilateral, 4),
            "ob_feedback_command": round(feedback, 4),
            "olfactory_familiarity_signal": round(familiarity, 4),
            "aon_state": state,
        }

    def _social_recognition_index(self, aco: float, familiarity: float) -> float:
        """Social olfactory recognition (Kogan 2000)."""
        return min(1.0, aco * 0.6 + familiarity * 0.4)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("aon_drive", 0.0),
            "familiarity": self.state.get("olfactory_familiarity_signal", 0.0),
            "feedback": self.state.get("ob_feedback_command", 0.0),
            "state": self.state.get("aon_state", "quiet"),
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

