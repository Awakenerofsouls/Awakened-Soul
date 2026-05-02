"""
AmygdalostriatalTransition — AStr / Amygdala-Striatum Bridge

NEURAL SUBSTRATE
================
The amygdalostriatal transition area (AStr) is a narrow zone between
central amygdala and ventral caudate-putamen. Anatomically transitional —
contains both amygdala-like + striatum-like cell types. Receives BLA
input + projects to NAc + ventral pallidum. Critical for emotional →
motor translation: converting amygdala valence signals into motivated
action selection in striatum.

KEY FINDINGS
============
1. AStr serves as anatomical bridge between amygdala emotional outputs
   and striatal motor circuits — [Heimer 1997, J Comp Neurol 384:597, PMID 9259489]
2. AStr receives convergent BLA + central amygdala input and projects
   to NAc + ventral pallidum — striato-amygdala axis —
   [Cassell 1999, J Comp Neurol 412:46, PMID 10440710]
3. AStr neurons encode reward-prediction signals coupled to action
   selection — bridges valence to motor —
   [Stuber 2011, Nature 475:377, doi:10.1038/nature10194]
4. AStr lesions disrupt cue-evoked motivated action without affecting
   basic appetite — [Cardinal 2002, Neurosci Biobehav Rev 26:321, doi:10.1016/S0149-7634(02)00007-6]
5. AStr is part of the "extended amygdala" continuum that includes
   BNST + central amygdala — [Alheid 1995, Prog Brain Res 107:461]

INPUTS
======
- BasolateralAmygdala.bla_drive
- CentralAmygdalaMedial.cem_drive
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- astr_drive (0-1)
- nac_motivation_command (0-1)
- vp_action_command (0-1)
- valence_motor_translation (0-1)
- astr_state (str): "appetitive_action" | "aversive_action" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AmygdalostriatalTransition(BrainMechanism):
    """AStr — bridge between amygdala valence and striatal action."""

    BASELINE = 0.10
    SMOOTH = 0.20
    ACTION_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="AmygdalostriatalTransition",
            human_analog="Amygdalostriatal transition (valence-motor bridge)",
            layer="limbic",
        )
        self.state.setdefault("astr_drive", self.BASELINE)
        self.state.setdefault("nac_motivation_command", 0.0)
        self.state.setdefault("vp_action_command", 0.0)
        self.state.setdefault("valence_motor_translation", 0.0)
        self.state.setdefault("astr_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, bla: float, cem: float, intensity: float) -> float:
        target = self.BASELINE + bla * 0.40 + cem * 0.30
        target += intensity * 0.20
        return min(1.0, target)

    def _nac_command(self, drive: float, appetitive: float) -> float:
        return min(1.0, drive * 0.5 + appetitive * 0.5)

    def _vp_command(self, drive: float, intensity: float) -> float:
        return min(1.0, drive * 0.6 + intensity * 0.4)

    def _valence_motor(self, drive: float, intensity: float,
                         valence_sign: int) -> float:
        if intensity < 0.20:
            return 0.0
        return min(1.0, drive * abs(valence_sign) * 0.5 + intensity * 0.5)

    def _classify_state(self, drive: float, valence_sign: int) -> str:
        if drive < 0.20:
            return "quiet"
        if valence_sign > 0:
            return "appetitive_action"
        if valence_sign < 0:
            return "aversive_action"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        cem_data = prior.get("CentralAmygdalaMedial", {})
        cem = float(cem_data.get("cem_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))
        appetitive = max(0.0, sign * intensity)

        target = self._drive_target(bla, cem, intensity)
        prev_drive = float(self.state.get("astr_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        nac_cmd = self._nac_command(new_drive, appetitive)
        vp_cmd = self._vp_command(new_drive, intensity)
        valence_motor = self._valence_motor(new_drive, intensity, sign)

        state = self._classify_state(new_drive, sign)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["astr_drive"] = round(new_drive, 4)
        self.state["nac_motivation_command"] = round(nac_cmd, 4)
        self.state["vp_action_command"] = round(vp_cmd, 4)
        self.state["valence_motor_translation"] = round(valence_motor, 4)
        self.state["astr_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "astr_drive": round(new_drive, 4),
            "nac_motivation_command": round(nac_cmd, 4),
            "vp_action_command": round(vp_cmd, 4),
            "valence_motor_translation": round(valence_motor, 4),
            "astr_state": state,
        }

    def _extended_amygdala_continuity(self, bla: float, cem: float,
                                          drive: float) -> float:
        """Extended amygdala continuum (Alheid 1995)."""
        return min(1.0, bla * 0.4 + cem * 0.4 + drive * 0.2)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("astr_drive", 0.0),
            "nac": self.state.get("nac_motivation_command", 0.0),
            "vp": self.state.get("vp_action_command", 0.0),
            "state": self.state.get("astr_state", "quiet"),
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

