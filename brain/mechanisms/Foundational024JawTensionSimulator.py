"""
Build 24: Foundational024JawTensionSimulator — Trigeminal Motor Nucleus
=====================================================================

PLACEMENT:
  Layer:    foundational (brainstem — trigeminal motor nucleus, mesencephalic nucleus)
  Filename: brain/foundational/Foundational024JawTensionSimulator.py
  Instance name: JawTensionSimulator

NEURAL SUBSTRATE:
  Trigeminal motor nucleus (Vmot) in pons — controls muscles of mastication
  (masseter, temporalis, pterygoids). Receives input from:
  - Sensorimotor cortex (voluntary chewing)
  - Mesencephalic nucleus (Vmes) — proprioceptive feedback from jaw stretch receptors
  - Supratrigeminal nucleus (suppression of masseteric reflex)
  - Reticular formation (aversive reflex circuits)

  KEY CIRCUITS:
  - Jaw-jerk reflex: Ia afferents from periodontal receptors → Vmot → masseter
  - masticatory central pattern generator in reticular formation
  - Tooth-pain modulation: periaqueductal gray → raphe → Vmot (descending inhibition)

  Human analog: chewing, tooth clenching (bruxism), jaw reflex, mastication.

Output keys:
  masseter_tone: float [0.0–1.0] — masseter muscle activation
  molar_bite_force: float [0.0–1.0] — bite force output
  jaw_reflex_suppression: float [0.0–1.0] — suppression of jaw-jerk reflex
  oral_motor_coordination: float [0.0–1.0] — CPG coordination of mastication
  tension_bruxism_index: float [0.0–1.0] — stress-related jaw clenching

CITATIONS:
    PMC1191101 — Dessem D, Iyadurai OD, Taylor A (1988). The Role of Periodontal
        Receptors in the Jaw-Opening Reflex in the Cat. J Physiol.
    PMC1331163 — Cody FW, Lee RW, Taylor A (1972). A Functional Analysis of the
        Components of the Mesencephalic Nucleus of the Fifth Nerve in the Cat.
        J Physiol.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class JawTensionSimulator(BrainMechanism):
    """
    Trigeminal motor nucleus: mastication, bite force, jaw tension.

    Controls masseter tone, molar bite force, and jaw-jerk reflex
    suppression. Elevated during stress (bruxism).
    """

    STATE_FIELDS = [
        "masseter_tone", "molar_bite_force", "jaw_reflex_suppression",
        "oral_motor_coordination", "tension_bruxism_index", "tick_count",
    ]

    MASSETER_GAIN = 0.55
    BITE_FORCE_GAIN = 0.60
    REFLEX_GAIN = 0.40
    CPG_GAIN = 0.50
    STRESS_BRUXISM_GAIN = 0.65

    def __init__(self, name: str = "JawTensionSimulator",
                 human_analog: str = "Trigeminal motor nucleus — jaw tension and mastication",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["masseter_tone"] = 0.10
        self.state["molar_bite_force"] = 0.05
        self.state["jaw_reflex_suppression"] = 0.30
        self.state["oral_motor_coordination"] = 0.40
        self.state["tension_bruxism_index"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        pain = prior.get("DescendingPainGate", {}).get("gate_output", 0.50)
        sensorimotor = prior.get("SensorimotorCortex", {}).get("motor_command_strength", 0.0)

        # Masseter tone: elevated by stress/arousal, reduced by pain modulation
        stress_tone = stress * self.STRESS_BRUXISM_GAIN
        arousal_tone = arousal * 0.15
        pain_inhibition = (1.0 - pain) * 0.10
        new_masseter = max(0.0, min(1.0, stress_tone + arousal_tone - pain_inhibition))

        # Bite force: proportional to masseter tone; sensorimotor command adds
        bite_force = (new_masseter * self.BITE_FORCE_GAIN) + (sensorimotor * 0.20)
        bite_force = max(0.0, min(1.0, bite_force))

        # Jaw reflex suppression: PAG/raphe descending inhibition (pain gate)
        reflex_suppression = (1.0 - pain) * self.REFLEX_GAIN

        # Oral motor coordination: CPG in reticular formation
        coordination = (new_masseter * 0.30) + (sensorimotor * 0.30) + 0.40
        coordination = max(0.0, min(1.0, coordination))

        # Bruxism index: stress drives jaw clenching during sleep/wake
        bruxism = stress * self.STRESS_BRUXISM_GAIN

        # --- Persist ---
        self.state["masseter_tone"] = round(new_masseter, 4)
        self.state["molar_bite_force"] = round(bite_force, 4)
        self.state["jaw_reflex_suppression"] = round(reflex_suppression, 4)
        self.state["oral_motor_coordination"] = round(coordination, 4)
        self.state["tension_bruxism_index"] = round(bruxism, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "masseter_tone": round(new_masseter, 4),
            "molar_bite_force": round(bite_force, 4),
            "jaw_reflex_suppression": round(reflex_suppression, 4),
            "oral_motor_coordination": round(coordination, 4),
            "tension_bruxism_index": round(bruxism, 4),
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

