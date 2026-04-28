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
