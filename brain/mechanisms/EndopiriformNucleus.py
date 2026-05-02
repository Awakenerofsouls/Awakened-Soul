"""
EndopiriformNucleus — En / Olfactory-Limbic Bridge

NEURAL SUBSTRATE
================
The endopiriform nucleus (En) is a deep nucleus medial to piriform cortex,
ventral to claustrum. Two subdivisions: dorsal (En-d) and ventral (En-v).
Receives strong piriform cortex + olfactory tubercle + amygdala input.
Projects bilaterally back to piriform + amygdala + entorhinal — a
recurrent olfactory-limbic loop.

Functional role: gain control + temporal integration of olfactory
processing, with strong susceptibility to epileptiform discharge (En is
the principal site of olfactory-evoked kindling seizures, Loscher 1995).

KEY FINDINGS
============
1. Endopiriform nucleus is the principal target of piriform cortex
   pyramidal cells and projects back to piriform + amygdala —
   recurrent olfactory-limbic loop —
   [Behan 1999, J Comp Neurol 408:532, PMID 10340504]
2. En is the lowest-threshold site for olfactory-evoked kindling
   seizures; intrinsic excitatory recurrence —
   [Loscher 1995, Brain Res 671:97, PMID 7728563]
3. En neurons exhibit broad multi-glomerular odor responses; integrate
   across receptor channels — [Litaudon 2003, J Comp Neurol 463:226, doi:10.1002/cne.10742]
4. En→amygdala projection mediates odor-fear associations independent
   of piriform — [Sosulski 2011, Nature 472:213, doi:10.1038/nature09868]
5. Endopiriform-claustrum continuum: anatomical + developmental
   relationship; both involved in cross-area integration —
   [Mathur 2014, Front Syst Neurosci 8:48, doi:10.3389/fnsys.2014.00048]

INPUTS
======
- PiriformCortex.pir_drive
- OlfactoryTubercleStriatal.ot_drive
- BasolateralAmygdala.bla_drive
- AnteriorOlfactoryNucleus.aon_drive

OUTPUTS
=======
- en_drive (0-1)
- piriform_feedback_command (0-1)
- amygdala_olfactory_drive (0-1)
- recurrent_excitation_signal (0-1)
- en_state (str): "active_olfactory" | "recurrent_engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class EndopiriformNucleus(BrainMechanism):
    """En — recurrent olfactory-limbic bridge."""

    BASELINE = 0.10
    SMOOTH = 0.20
    RECURRENT_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="EndopiriformNucleus",
            human_analog="Endopiriform nucleus (olfactory-limbic bridge)",
            layer="limbic",
        )
        self.state.setdefault("en_drive", self.BASELINE)
        self.state.setdefault("piriform_feedback_command", 0.0)
        self.state.setdefault("amygdala_olfactory_drive", 0.0)
        self.state.setdefault("recurrent_excitation_signal", 0.0)
        self.state.setdefault("en_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, pir: float, ot: float, bla: float, aon: float) -> float:
        target = self.BASELINE + pir * 0.40 + ot * 0.20 + bla * 0.20 + aon * 0.10
        return min(1.0, target)

    def _piriform_feedback(self, drive: float, pir: float) -> float:
        """Recurrent feedback to piriform (Behan 1999)."""
        return min(1.0, drive * 0.6 + pir * 0.4)

    def _amygdala_drive(self, drive: float, bla: float) -> float:
        """En→amygdala olfactory pathway (Sosulski 2011)."""
        return min(1.0, drive * 0.5 + bla * 0.5)

    def _recurrent_excitation(self, drive: float, pir: float) -> float:
        """Intrinsic recurrent excitation (Loscher 1995)."""
        if drive < 0.30:
            return 0.0
        return min(1.0, drive * pir * 1.4)

    def _classify_state(self, drive: float, recurrent: float) -> str:
        if recurrent > self.RECURRENT_THRESHOLD:
            return "recurrent_engaged"
        if drive > 0.25:
            return "active_olfactory"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pir_data = prior.get("PiriformCortex", {})
        pir = float(pir_data.get("pir_drive", 0.0))

        ot_data = prior.get("OlfactoryTubercleStriatal", {})
        ot = float(ot_data.get("ot_drive", 0.0))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        aon_data = prior.get("AnteriorOlfactoryNucleus", {})
        aon = float(aon_data.get("aon_drive", 0.0))

        target = self._drive_target(pir, ot, bla, aon)
        prev_drive = float(self.state.get("en_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        pir_fb = self._piriform_feedback(new_drive, pir)
        amy_drive = self._amygdala_drive(new_drive, bla)
        recurrent = self._recurrent_excitation(new_drive, pir)

        state = self._classify_state(new_drive, recurrent)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["en_drive"] = round(new_drive, 4)
        self.state["piriform_feedback_command"] = round(pir_fb, 4)
        self.state["amygdala_olfactory_drive"] = round(amy_drive, 4)
        self.state["recurrent_excitation_signal"] = round(recurrent, 4)
        self.state["en_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "en_drive": round(new_drive, 4),
            "piriform_feedback_command": round(pir_fb, 4),
            "amygdala_olfactory_drive": round(amy_drive, 4),
            "recurrent_excitation_signal": round(recurrent, 4),
            "en_state": state,
        }

    def _epileptiform_susceptibility(self, recurrent: float) -> float:
        """Kindling-seizure susceptibility (Loscher 1995)."""
        return min(1.0, recurrent * 0.85)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("en_drive", 0.0),
            "recurrent": self.state.get("recurrent_excitation_signal", 0.0),
            "amygdala": self.state.get("amygdala_olfactory_drive", 0.0),
            "state": self.state.get("en_state", "quiet"),
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

