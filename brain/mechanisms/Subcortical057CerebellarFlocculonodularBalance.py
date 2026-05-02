"""
Subcortical057CerebellarFlocculonodularBalance.py — Wire 57: Archicerebellum

Neural substrate: Flocculonodular lobe (archicerebellum) — vestibulocerebellum.

The flocculonodular lobe (FNL) is the phylogenetically oldest part of the
cerebellum — the archicerebellum. It consists of the nodulus (central)
and two flocculi (lateral), connected to the vestibular nuclei and
participating in the vestibulo-ocular reflex (VOR) and balance control.

Barmack 2003 mapped the vestibular-recipient zones of the cerebellar
cortex: the FNL receives primary vestibular afferents (from semicircular
canals and otolith organs) and secondary vestibular afferents (from
vestibular nuclei). It projects back to vestibular nuclei, which
influence eye muscles and postural muscles. Blanks 2010 reviewed the
anatomical organization of the FNL in detail.

KEY RESEARCH FINDINGS:
1. Vestibulo-ocular reflex (VOR). The FNL is the cerebellar modulator
   of the VOR. Without cerebellar modulation, the VOR is maladaptive —
   eye movements don't compensate for head movements, causing visual
   blur during movement. With FNL (flocculus), the VOR is calibrated
   to match the gain (1.0 for clear vision during head movement).
   Lisberger 1994: "The flocculus functions as an adaptive filter for
   the VOR."

2. Vestibular afferents. Barmack & Shojaku 1995: Primary vestibular
   afferents (from semicircular canals: horizontal, anterior, posterior)
   project directly to the flocculus and nodulus. Otolith afferents
   (linear acceleration from utricle and saccule) also project to the
   nodulus. These provide real-time head position and motion signals.

3. VOR gain plasticity. The flocculus implements adaptive gain control
   of the VOR. If the VOR gain is wrong (too high or too low), error
   signals (visual slip signals from the optokinetic system) cause
   the flocculus to adjust the gain of the VOR via long-term depression
   (LTD) at parallel fiber-Purkinje cell synapses in the flocculus.
   This is one of the best-characterized examples of cerebellar
   motor learning.

4. Spatial orientation and gravity. The nodulus and ventral uvula
   process otolith signals to detect head tilt relative to gravity.
   This is critical for: (a) detecting body orientation in space,
   (b) disambiguating linear from angular acceleration, (c) sensing
   gravitational vertical. Tammer 2006: nodulus lesion causes
   "tilting" behavior — rats walk with head tilted, difficulty with
   spatial orientation tasks.

5. Nodulus in gravity detection. The nodulus computes the gravity
   vector from otolith signals. It uses the time-averaged otolith
   input (which averages acceleration over ~10 seconds) to compute
   the vertical direction. Lesions of nodulus produce "gravity
   blindness" — inability to correctly orient to gravity.

6. Eye movement control. Floccular Purkinje cells encode the eye
   movement commands (eye velocity, position) during VOR. They
   receive vestibular input and produce outputs to the vestibular
   nuclei that drive eye muscles via the vestibular nerve. The
   flocculus encodes both the motor command and the error signal.

7. Balance and posture. FNL contributes to automatic postural
   adjustments — the vestibular input from FNL modulates extensor
   muscle tone for balance. Loss of FNL produces ataxia of trunk/
   head, nystagmus, and "positional vertigo" symptoms.

8. Spatial orientation factor. The FNL integrates vestibular
   (linear + angular acceleration) and visual input to maintain
   a spatial orientation signal — "where am I relative to vertical."
   This is a prerequisite for accurate movement planning.

OUTPUTS:
  VOR_signal: float 0-1 — VOR activation and calibration state
  balance_weight: float 0-1 — strength of vestibular balance contribution
  spatial_orientation_factor: float 0-1 — internal model of vertical/gravity

INPUTS:
  vestibular_input: from semicircular canals (angular velocity)
  otolith_input: linear acceleration from otolith organs
  visual_slip: retinal slip error signal for VOR adaptation
  head_movement: head motion signal
  gravity_reference: reference gravitational vector

CITATIONS:
    PMC12449109 — Machado Filho WS, Martinez JAR, França Junior MC (2025).
        Neurophysiology of the Cerebellum and Clinical Correlations: A Review.
        Arq Neuropsiquiatr.
    PMC6573528 — Goto MM, Romero GG, Balaban CD (1997). Transient Changes in
        Flocculonodular Lobe Protein Kinase C Expression During Vestibular
        Compensation. J Neurophysiol.


CITATIONS
---------
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive affective]
"""

from brain.base_mechanism import BrainMechanism


class CerebellarFlocculonodularBalance(BrainMechanism):
    """
    Flocculonodular lobe (archicerebellum) — VOR, balance, spatial orientation.

    Receives primary and secondary vestibular afferents, modulates
    the VOR, computes spatial orientation relative to gravity, and
    contributes to postural stability.
    """

    VOR_GAIN_BASELINE = 1.0  # nominal gain
    VOR_LEARNING_RATE = 0.05
    FLOC_CULAR_GAIN = 0.65
    GRAVITY_INTEGRATION_RATE = 0.04
    BALANCE_DECAY = 0.02

    def __init__(self):
        super().__init__(
            name="CerebellarFlocculonodularBalance",
            human_analog="Flocculonodular lobe (archicerebellum) — vestibulocerebellum",
            layer="subcortical",
        )
        self.state.setdefault("VOR_signal", 0.0)
        self.state.setdefault("balance_weight", 0.6)
        self.state.setdefault("spatial_orientation_factor", 0.5)
        self.state.setdefault("VOR_gain", 1.0)
        self.state.setdefault("gravity_vector", [0.0, -1.0, 0.0])
        self.state.setdefault("head_tilt_angle", 0.0)
        self.state.setdefault("nodular_activity", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        vestibular_input = input_data.get("vestibular_input", 0.0)
        otolith_input = input_data.get("otolith_input", 0.0)
        visual_slip = input_data.get("visual_slip", 0.0)
        head_movement = input_data.get("head_movement", 0.0)
        gravity_reference = input_data.get("gravity_reference", [0.0, -1.0, 0.0])
        angular_velocity = input_data.get("angular_velocity", 0.0)

        # --- VOR signal ---
        # The VOR is driven by vestibular (head movement) input
        # VOR_output = VOR_gain * head_velocity
        VOR_drive = head_movement * self.state["VOR_gain"]
        vestibular_contribution = angular_velocity * 0.4 * self.FLOC_CULAR_GAIN

        VOR_signal = max(0.0, min(1.0, VOR_drive + vestibular_contribution))

        # --- VOR gain adaptation ---
        # Visual slip = retinal error = desired correction to VOR
        # If visual slip > 0, VOR gain is wrong; adapt
        gain_correction = -visual_slip * self.VOR_LEARNING_RATE  # negative slip = gain too high
        new_gain = self.state["VOR_gain"] + gain_correction
        self.state["VOR_gain"] = max(0.3, min(2.0, new_gain))

        # --- Nodular activity ---
        # Nodulus processes otolith and low-frequency vestibular signals
        otolith_contribution = abs(otolith_input) * 0.35
        gravity_deviation = self._compute_gravity_deviation(
            self.state["gravity_vector"], gravity_reference
        )
        nodular = otolith_contribution + gravity_deviation * 0.3 + vestibular_input * 0.2
        self.state["nodular_activity"] = max(0.0, min(1.0, nodular))

        # --- Balance weight ---
        # Balance signal grows with vestibular activity and correct gravity model
        vestibular_balance = abs(vestibular_input) * 0.4
        gravity_quality = 1.0 - gravity_deviation
        balance_delta = (vestibular_balance + gravity_quality * 0.3) * self.BALANCE_DECAY
        new_balance = self.state["balance_weight"] + balance_delta
        self.state["balance_weight"] = max(0.2, min(0.95, new_balance))

        # --- Spatial orientation factor ---
        # Combines vestibular (head tilt), otolith (gravity direction),
        # and visual references to build an internal model of orientation
        head_tilt = abs(head_movement - otolith_input) * 0.5  # deviation from expected

        # Integrate gravity vector toward reference (slow learning)
        current_g = self.state["gravity_vector"]
        gx = current_g[0] + self.GRAVITY_INTEGRATION_RATE * (gravity_reference[0] - current_g[0])
        gy = current_g[1] + self.GRAVITY_INTEGRATION_RATE * (gravity_reference[1] - current_g[1])
        gz = current_g[2] + self.GRAVITY_INTEGRATION_RATE * (gravity_reference[2] - current_g[2])
        self.state["gravity_vector"] = [round(gx, 4), round(gy, 4), round(gz, 4)]

        # Spatial orientation is high when gravity model is accurate
        orientation_quality = 1.0 - gravity_deviation
        spatial_factor = max(0.0, min(1.0, orientation_quality * 0.8 + nodular * 0.2))
        self.state["spatial_orientation_factor"] = spatial_factor
        self.state["head_tilt_angle"] = head_tilt

        self.state["VOR_signal"] = VOR_signal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "VOR_signal": round(VOR_signal, 4),
            "balance_weight": round(self.state["balance_weight"], 4),
            "spatial_orientation_factor": round(spatial_factor, 4),
            "VOR_gain": round(self.state["VOR_gain"], 4),
            "head_tilt_angle": round(head_tilt, 4),
            "gravity_vector": self.state["gravity_vector"],
        }

    def _compute_gravity_deviation(self, current: list, reference: list) -> float:
        """Compute angular deviation between current and reference gravity vectors."""
        import math
        # Dot product of normalized vectors
        mag_cur = math.sqrt(sum(c**2 for c in current)) or 1.0
        mag_ref = math.sqrt(sum(r**2 for r in reference)) or 1.0
        dot = sum(c * r for c, r in zip(current, reference)) / (mag_cur * mag_ref)
        # Clamp to [-1, 1]
        dot = max(-1.0, min(1.0, dot))
        # Deviation in [0, 1]
        deviation = math.acos(dot) / math.pi
        return deviation

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

