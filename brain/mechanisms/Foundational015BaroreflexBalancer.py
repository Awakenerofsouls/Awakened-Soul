"""
Build 15: Foundational015BaroreflexBalancer — Baroreceptor Reflex Arc
=====================================================================

PLACEMENT:
  Layer:    foundational (medulla — nucleus tractus solitarius, CVLM, RVLM)
  Filename: brain/foundational/Foundational015BaroreflexBalancer.py
  Instance name: BaroreflexBalancer

NEURAL SUBSTRATE:
  Nucleus tractus solitarius (NTS) receives primary arterial baroreceptor
  input via glossopharyngeal (CN IX) and vagus (CN X). NTS projects to the
  caudal ventrolateral medulla (CVLM), which tonically inhibits the rostral
  ventrolateral medulla (RVLM). Active CVLM → suppressed RVLM → reduced
  sympathetic vasomotor tone → blood pressure falls. This forms a negative
  feedback loop that stabilizes arterial pressure on a beat-to-beat basis.

  Carotid baroreceptors also reset their operating point during sustained
  hypertension via the "baroreflex resetting" phenomenon (Jones 1995,
  Krieger et al. 1998), allowing long-term BP regulation adaptation.

  Human analog: carotid sinus massage, Valsalva maneuver, orthostatic
  response, blood pressure variability.

Refs:
  - Guyenet 2006 (PMC4471069) — sympathetic vasomotor control, RVLM/CVLM/NTS
  - Sanner 1972 (PMC4471069) — baroreceptor input to NTS
  - Jones 1995 (PMID 7674980) — baroreflex resetting

Output keys:
  baroreflex_activity: float [0.0–1.0] — net baroreflex firing rate (from NTS)
  sympathetic_tone: float [0.0–1.0] — RVLM sympathetic output drive
  parasympathetic_tone: float [0.0–1.0] — vagal/muscarinic tone from NTS
  bp_regulation_strength: float [0.0–1.0] — correction magnitude per tick
  hypotension_risk: float [0.0–1.0] — under-pressure correction need
  hypertension_risk: float [0.0–1.0] — over-pressure correction need
  baroreflex_setpoint: float — current NTS operating point (normalized MAP)


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism
import numpy as np


class BaroreflexBalancer(BrainMechanism):
    """
    Baroreceptor reflex arc: NTS → CVLM → RVLM negative feedback loop.

    Responds to discrepancies between current_baroreceptor_input and the
    baroreflex_setpoint. Elevated pressure → NTS fires → CVLM inhibits
    RVLM → sympathetic tone drops → BP falls. The reverse holds for
    hypotension. The setpoint itself slowly resets during sustained
    hypertension (long-term adaptation).
    """

    # Internal state fields
    STATE_FIELDS = [
        "baroreflex_activity",    # NTS firing rate
        "sympathetic_tone",       # RVLM drive
        "parasympathetic_tone",   # vagal tone
        "baroreflex_setpoint",    # operating point (normalized MAP)
        "tick_count",
    ]

    # Parameters
    BAROREFLEX_GAIN = 0.55     # NTS sensitivity to pressure deviation
    SYMPATHETIC_DECAY = 0.12   # rate of sympathetic tone decay when CVLM active
    PARASYMPATHETIC_GAIN = 0.20  # vagal response magnitude
    SETPOINT_ADAPTATION = 0.002  # slow drift of setpoint under sustained BP
    BASELINE_SYMPATHETIC = 0.38  # tonic RVLM drive at rest
    BASELINE_PARASYMPATHETIC = 0.32
    # Normalized MAP scale: 0.0 → 50 mmHg, 0.5 → 97.5 mmHg, 1.0 → 145 mmHg
    DEFAULT_SETPOINT = 0.70     # 0.70 ≈ 95 mmHg MAP (normotension)

    def __init__(self, name: str = "BaroreflexBalancer",
                 human_analog: str = "NTS+CVLM+RVLM — baroreceptor reflex arc",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        # Initial state
        self.state["baroreflex_activity"] = 0.5
        self.state["sympathetic_tone"] = self.BASELINE_SYMPATHETIC
        self.state["parasympathetic_tone"] = self.BASELINE_PARASYMPATHETIC
        self.state["baroreflex_setpoint"] = self.DEFAULT_SETPOINT
        self.state["tick_count"] = 0

    # ── tick ─────────────────────────────────────────────────────────────────
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Normalized MAP input (0.0=50mmHg, 0.5=97.5mmHg, 1.0=145mmHg) ---
        # Default 0.70 (normotension) when no prior mechanism present
        current_pressure = prior.get("SympatheticVasomotorController", {}).get(
            "mean_arterial_pressure", 0.70
        )
        heart_rate_signal = prior.get("HeartRateController", {}).get(
            "heart_rate", 0.50
        )
        stress_signal = prior.get("CRHStressDispatcher", {}).get(
            "crh_level", 0.0
        )

        # --- Current state ---
        current_activity = self.state["baroreflex_activity"]
        current_sympathetic = self.state["sympathetic_tone"]
        current_parasympathetic = self.state["parasympathetic_tone"]
        setpoint = self.state["baroreflex_setpoint"]

        # --- Error: deviation from setpoint on normalized MAP scale ---
        error = current_pressure - setpoint  # positive = hypertension

        # --- NTS baroreflex firing rate ---
        baroreflex_activity = self.BAROREFLEX_GAIN * abs(error) / 0.35
        baroreflex_activity = max(0.0, min(1.0, baroreflex_activity))

        # --- Sympathetic tone (RVLM output) ---
        # CVLM inhibits RVLM. NTS drives CVLM → baroreflex suppresses RVLM.
        # Stress adds: CRH drives sympathetic tone directly during acute stress.
        new_sympathetic = current_sympathetic
        if abs(error) > 0.05:  # meaningful deviation
            if error > 0:  # hypertension → CVLM suppresses RVLM → sympathetic drops
                suppression = baroreflex_activity * self.SYMPATHETIC_DECAY
                new_sympathetic = max(0.10, current_sympathetic - suppression)
            else:  # hypotension → CVLM disengaged → sympathetic rises
                rise = baroreflex_activity * self.SYMPATHETIC_DECAY * 0.5
                new_sympathetic = min(1.0, current_sympathetic + rise)
        # CRH stress: drives sympathetic tone upward
        stress_contribution = stress_signal * 0.20
        new_sympathetic = max(0.10, min(1.0, new_sympathetic + stress_contribution))

        # --- Parasympathetic tone (vagal NTS output) ---
        # Vagal withdrawal during stress; baroreflex-activated in normotension
        baroreflex_vagal = baroreflex_activity * self.PARASYMPATHETIC_GAIN
        stress_vagal_inhibition = stress_signal * 0.15
        new_parasympathetic = max(0.0, min(1.0,
            self.BASELINE_PARASYMPATHETIC + baroreflex_vagal - stress_vagal_inhibition))

        # --- BP regulation strength (normalized error magnitude) ---
        bp_regulation_strength = abs(error) * 1.5
        bp_regulation_strength = min(1.0, bp_regulation_strength)
        bp_regulation_strength = round(bp_regulation_strength, 4)

        # --- Hypotension and hypertension risk (on normalized MAP scale) ---
        # MAP norm: 0.0 → 50 mmHg, 0.5 → 97.5 mmHg, 1.0 → 145 mmHg
        hypotension_risk = max(0.0, 0.45 - current_pressure) / 0.45 if error < 0 else 0.0
        hypotension_risk = min(1.0, hypotension_risk)
        hypertension_risk = max(0.0, current_pressure - 0.75) / 0.25 if error > 0 else 0.0
        hypertension_risk = min(1.0, hypertension_risk)

        # --- Slow setpoint adaptation (baroreflex resetting) ---
        # Under sustained hypertension, the operating point drifts upward
        if abs(error) > 0.10:
            if error > 0:
                setpoint_shift = self.SETPOINT_ADAPTATION * (error / 0.30)
            else:
                setpoint_shift = -self.SETPOINT_ADAPTATION * (abs(error) / 0.30)
            setpoint = max(0.45, min(0.90, setpoint + setpoint_shift))
        setpoint = round(setpoint, 4)

        # --- Round outputs ---
        baroreflex_activity = round(baroreflex_activity, 4)
        new_sympathetic = round(new_sympathetic, 4)
        new_parasympathetic = round(new_parasympathetic, 4)
        hypotension_risk = round(hypotension_risk, 4)

        # --- Persist ---
        self.state["baroreflex_activity"] = baroreflex_activity
        self.state["sympathetic_tone"] = new_sympathetic
        self.state["parasympathetic_tone"] = new_parasympathetic
        self.state["baroreflex_setpoint"] = setpoint
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "baroreflex_activity": baroreflex_activity,
            "sympathetic_tone": new_sympathetic,
            "parasympathetic_tone": new_parasympathetic,
            "bp_regulation_strength": bp_regulation_strength,
            "hypotension_risk": hypotension_risk,
            "hypertension_risk": hypertension_risk,
            "baroreflex_setpoint": setpoint,
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

