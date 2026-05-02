"""
AmygdaloidCorticalAnterior — ACo / Anterior Cortical Amygdala / Main-Olfactory

NEURAL SUBSTRATE
================
The anterior cortical amygdala (ACo) is the principal target of main
olfactory bulb (MOB) within the amygdala — distinct from PCo (posterior
cortical amygdala) which receives accessory olfactory bulb (AOB) input.
ACo processes general odor identity for emotional/limbic association,
not pheromones.

Inputs: olfactory bulb (mitral/tufted cells), piriform cortex.
Outputs: BLA, central amygdala, BNST, hypothalamus.

ACo is the main-olfactory bridge from cortical odor processing to
amygdala emotional circuits — distinct from olfactory tubercle (reward)
and lateral entorhinal (memory).

KEY FINDINGS
============
1. ACo receives main olfactory bulb input via lateral olfactory tract;
   processes odor identity for emotional association (vs PCo
   pheromones) — [Sosulski 2011, Nature 472:213, doi:10.1038/nature09868]
2. ACo→BLA projection mediates odor-fear conditioning; selective
   inactivation impairs olfactory fear learning —
   [Root 2014, Nature 515:269, doi:10.1038/nature13897]
3. ACo neurons encode odor identity at single-cell resolution; sparse
   coding similar to piriform — [Stettler 2009, Neuron 63:854, doi:10.1016/j.neuron.2009.09.005]
4. ACo lesions impair odor-evoked emotional responses without
   affecting odor detection or discrimination —
   [Carmichael 1994, J Comp Neurol 346:403, PMID 7527808]
5. Main vs accessory olfactory amygdala dissociation: ACo for general
   odors, PCo for pheromones — [Mucignat-Caretta 2010, Front Neurosci 4:175, PMC2998082]

INPUTS
======
- OlfactoryBulb.ob_drive
- PiriformCortex.pir_drive
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- aco_drive (0-1)
- odor_identity_signal (0-1)
- bla_olfactory_drive (0-1)
- olfactory_emotion_signal (0-1)
- aco_state (str): "odor_emotion" | "neutral_odor" |
  "novel_odor" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AmygdaloidCorticalAnterior(BrainMechanism):
    """ACo — main olfactory amygdala for odor-emotion binding."""

    BASELINE = 0.10
    SMOOTH = 0.20
    EMOTION_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="AmygdaloidCorticalAnterior",
            human_analog="Anterior cortical amygdala (main olfactory)",
            layer="limbic",
        )
        self.state.setdefault("aco_drive", self.BASELINE)
        self.state.setdefault("odor_identity_signal", 0.0)
        self.state.setdefault("bla_olfactory_drive", 0.0)
        self.state.setdefault("olfactory_emotion_signal", 0.0)
        self.state.setdefault("aco_state", "quiet")
        self.state.setdefault("recent_odors", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ob: float, pir: float, intensity: float) -> float:
        target = self.BASELINE + ob * 0.45 + pir * 0.30
        target += intensity * 0.15
        return min(1.0, target)

    def _odor_identity(self, ob: float, pir: float) -> float:
        return min(1.0, ob * 0.6 + pir * 0.4)

    def _bla_drive(self, drive: float, intensity: float) -> float:
        return min(1.0, drive * 0.6 + intensity * 0.4)

    def _emotion_signal(self, drive: float, intensity: float,
                          valence_sign: int) -> float:
        if intensity < 0.20 or valence_sign == 0:
            return 0.0
        return min(1.0, drive * 0.5 + intensity * 0.5)

    def _classify_state(self, drive: float, emotion: float,
                          recent_odors: list, ob: float) -> str:
        if drive < 0.15:
            return "quiet"
        if emotion > self.EMOTION_THRESHOLD:
            return "odor_emotion"
        if ob > 0.30 and (not recent_odors or
                            (len(recent_odors) > 5 and abs(recent_odors[-1] - ob) > 0.30)):
            return "novel_odor"
        return "neutral_odor"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ob_data = prior.get("OlfactoryBulb", {})
        ob = float(ob_data.get("ob_drive", 0.0))

        pir_data = prior.get("PiriformCortex", {})
        pir = float(pir_data.get("pir_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        valence_sign = int(valence.get("valence_sign", 0))

        target = self._drive_target(ob, pir, intensity)
        prev_drive = float(self.state.get("aco_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        odor_id = self._odor_identity(ob, pir)
        bla_drive = self._bla_drive(new_drive, intensity)
        emotion = self._emotion_signal(new_drive, intensity, valence_sign)

        recent = list(self.state.get("recent_odors", []))
        if ob > 0.20:
            recent.append(round(ob, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        state = self._classify_state(new_drive, emotion, recent, ob)

        self.state["aco_drive"] = round(new_drive, 4)
        self.state["odor_identity_signal"] = round(odor_id, 4)
        self.state["bla_olfactory_drive"] = round(bla_drive, 4)
        self.state["olfactory_emotion_signal"] = round(emotion, 4)
        self.state["aco_state"] = state
        self.state["recent_odors"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "aco_drive": round(new_drive, 4),
            "odor_identity_signal": round(odor_id, 4),
            "bla_olfactory_drive": round(bla_drive, 4),
            "olfactory_emotion_signal": round(emotion, 4),
            "aco_state": state,
        }

    def _odor_fear_conditioning_strength(self, drive: float,
                                            aversive: float) -> float:
        """Odor-fear learning capacity (Root 2014)."""
        return min(1.0, drive * aversive * 1.2)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("aco_drive", 0.0),
            "identity": self.state.get("odor_identity_signal", 0.0),
            "emotion": self.state.get("olfactory_emotion_signal", 0.0),
            "state": self.state.get("aco_state", "quiet"),
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

