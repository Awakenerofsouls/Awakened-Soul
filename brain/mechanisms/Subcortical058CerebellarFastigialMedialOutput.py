"""
Subcortical058CerebellarFastigialMedialOutput.py — Wire 58: Fastigial Output

Neural substrate: Fastigial nucleus (medial deep cerebellar nucleus).

The fastigial nucleus (FN) is the most medial of the three deep
cerebellar nuclei (DCN). It receives input from the vermal cortex
(Purkinje cells of vermal zones), from the vestibular nuclei, and
from the spinal cord via the vestibulospinal tract. It is the
output nucleus for the vestibulocerebellum (archicerebellum) and
contributes to axial posture, proximal muscle control, and gravity-
based postural adjustments.

Dow 1942 established the comparative anatomy of the fastigial nucleus
across species. Wilson et al. 1980s confirmed that the FN is the
primary DCN output for axial/postural motor control. Asanuma &
Watts 1996 mapped the descending projections: FN sends excitatory
(bulbospinal) fibers to the medial medullary reticular formation
and to the vestibular nuclei — directly influencing axial and
proximal limb muscles.

KEY RESEARCH FINDINGS:
1. Axial posture and proximal control. The FN controls axial and
   proximal muscles — the large muscles of the trunk and the
   proximal limb that are responsible for posture, balance, and
   whole-body orientation. This is distinct from the interposed
   nuclei which control distal limb movement, and the dentate
   nucleus which controls distal manipulation.

2. Efferent projections. Batton et al. 1983: FN projects via the
   juxtarestiform body to: (a) vestibular nuclei (lateral and
   medial VN), (b) pontine and medullary reticular formation,
   (c) contralateral FN (via interpositus), (d) spinal cord via
   the vestibulospinal and reticulospinal tracts. The FN is
   the cerebellar source of vestibulocerebellar output.

3. Gravity compensation. The FN implements automatic postural
   adjustments to maintain balance against gravity. Purkinje
   cells from the vermis (lobules VII-IX) fire to oppose
   gravitational torque — FN receives this and generates
   corrective output to extensor muscles. When FN is damaged,
   animals show "ventral shifting" — tendency to fall forward
   (Asanuma 1983).

4. Proximal muscle weighting. Parker et al. 2018: FN neurons have
   larger receptive fields than interposed or dentate neurons,
   reflecting the broad muscle group control needed for axial
   posture. Receptive fields often span multiple joints and
   include bilateral components.

5. Synchronization with vestibular input. The FN synchronizes
   with vestibular nuclei to maintain postural tone. During
   VOR-modulated head movement, FN neurons modulate their
   firing to maintain the appropriate extensor tone for the
   current head position (Wilson 1998).

6. Oculomotor function. The FN also contributes to eye movement
   control via its projections to the vestibular nuclei and
   inferior olive. FN lesions produce "opsoclonus" — involuntary
   saccadic oscillations (Kornhuber 1970s). FN coordinates
   the gaze-holding function.

7. Medial vs. lateral DCN distinction. The medial FN is distinct
   from the interposed nuclei (middle DCN) in both connectivity
   and function. Interposed = distal limb, FN = axial/proximal/
   postural. The dentate = cognitive/motor coordination.

8. Fastigial output as "posture signal." In cerebellar models,
   the FN output can be interpreted as the "posture command" —
   the signal that maintains baseline muscle tone for the current
   body configuration against gravity.

OUTPUTS:
  fastigial_output: float 0-1 — net fastigial DCN activation
  axial_posture_signal: float 0-1 — strength of axial posture command
  proximal_muscle_weight: float 0-1 — weighting of proximal vs distal control

INPUTS:
  vermal_Purkinje_input: Purkinje cell firing from vermal cortex
  vestibular_spinal_input: vestibular nucleus input
  gravity_perturbation: unexpected tilt/acceleration
  axial_motor_command: cortical/other command for axial movement
  reticulospinal_activity: brainstem postural control signal

CITATIONS:
    PMC4112144 — Catanzaro MF, Miller DJ, Cotter LA et al. (2014). Integration of
        Vestibular and Gastrointestinal Inputs by Cerebellar Fastigial Nucleus
        Neurons. J Neurophysiol.
    PMC4853849 — Zhang XY, Wang JJ, Zhu JN (2016). Cerebellar Fastigial Nucleus:
        From Anatomic Construction to Physiological Functions. CNS Neurosci Ther.


CITATIONS
---------
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive affective]
"""

from brain.base_mechanism import BrainMechanism


class CerebellarFastigialMedialOutput(BrainMechanism):
    """
    Fastigial nucleus (medial DCN) — axial posture, proximal control.

    Receives vermal cerebellar input, generates vestibular and
    reticulospinal output for axial/postural muscle control.
    Implements gravity compensation and proximal body stabilization.
    """

    FN_RESTING_OUTPUT = 0.40  # baseline tonic output for posture
    VERMAL_GAIN = 0.70
    VESTIBULAR_GAIN = 0.50
    GRAVITY_COMPENSATION_GAIN = 0.40
    PROXIMAL_WEIGHTING = 0.75  # FN is biased toward proximal control
    POSTURAL_DECAY = 0.03

    def __init__(self):
        super().__init__(
            name="CerebellarFastigialMedialOutput",
            human_analog="Fastigial nucleus (medial DCN) — vestibulocerebellum, axial posture",
            layer="subcortical",
        )
        self.state.setdefault("fastigial_output", 0.0)
        self.state.setdefault("axial_posture_signal", 0.5)
        self.state.setdefault("proximal_muscle_weight", 0.75)
        self.state.setdefault("gravity_compensation_strength", 0.0)
        self.state.setdefault("postural_tone", 0.5)
        self.state.setdefault("vestibular_coupling", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        vermal_Purkinje = input_data.get("vermal_Purkinje_input", 0.5)
        vestibular_spinal = input_data.get("vestibular_spinal_input", 0.3)
        gravity_perturbation = input_data.get("gravity_perturbation", 0.0)
        axial_motor_command = input_data.get("axial_motor_command", 0.0)
        reticulospinal = input_data.get("reticulospinal_activity", 0.3)

        # --- Fastigial output computation ---
        # FN output = baseline (postural tone) + vermal inhibition (disinhibition)
        # + vestibular + axial command - gravity perturbation
        # High vermal input → less inhibition on FN → more output
        vermal_disinhibition = (vermal_Purkinje - 0.5) * 2.0 * self.VERMAL_GAIN
        vestibular_contribution = vestibular_spinal * self.VESTIBULAR_GAIN
        axial_contribution = axial_motor_command * 0.35

        # Reticulospinal input directly modulates FN output (brainstem state)
        reticular_modulation = (reticulospinal - 0.5) * 0.25

        raw_output = (
            self.FN_RESTING_OUTPUT
            + vermal_disinhibition
            + vestibular_contribution
            + axial_contribution
            + reticular_modulation
            - abs(gravity_perturbation) * self.GRAVITY_COMPENSATION_GAIN * 0.5
        )
        fastigial_output = max(0.0, min(1.0, raw_output))

        # --- Axial posture signal ---
        # The posture signal is the FN output specifically for axial muscles
        # It maintains baseline tone (postural tone) + corrective adjustments
        corrective = abs(gravity_perturbation) * self.GRAVITY_COMPENSATION_GAIN
        # Corrective force opposes perturbation direction
        axial_posture_signal = self.state["postural_tone"] + corrective - abs(gravity_perturbation) * 0.3
        axial_posture_signal = max(0.2, min(1.0, axial_posture_signal))

        # --- Gravity compensation ---
        # FN automatically generates anti-gravity output
        if abs(gravity_perturbation) > 0.3:
            compensation = min(0.3, abs(gravity_perturbation) * 0.5)
            self.state["gravity_compensation_strength"] = min(
                1.0, self.state["gravity_compensation_strength"] + compensation
            )
        else:
            self.state["gravity_compensation_strength"] *= (1.0 - self.POSTURAL_DECAY)

        # --- Postural tone ---
        # Baseline tonic output for postural maintenance
        new_tone = self.state["postural_tone"] * 0.9 + axial_posture_signal * 0.1
        self.state["postural_tone"] = max(0.3, min(0.9, new_tone))

        # --- Vestibular coupling ---
        # FN synchronizes with vestibular nuclei for postural stability
        vestibular_coupling = abs(vestibular_spinal - vermal_Purkinje)
        new_coupling = self.state["vestibular_coupling"] * 0.85 + vestibular_coupling * 0.15
        self.state["vestibular_coupling"] = max(0.0, min(1.0, new_coupling))

        # --- Proximal muscle weight ---
        # FN is biased toward proximal/axial control vs distal
        # Proximal weight increases when gravity perturbation is high
        if abs(gravity_perturbation) > 0.4:
            proximal_delta = 0.02
            self.state["proximal_muscle_weight"] = min(
                0.95, self.state["proximal_muscle_weight"] + proximal_delta
            )
        else:
            self.state["proximal_muscle_weight"] *= 0.998

        self.state["fastigial_output"] = fastigial_output
        self.state["axial_posture_signal"] = axial_posture_signal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "fastigial_output": round(fastigial_output, 4),
            "axial_posture_signal": round(axial_posture_signal, 4),
            "proximal_muscle_weight": round(self.state["proximal_muscle_weight"], 4),
            "gravity_compensation_strength": round(self.state["gravity_compensation_strength"], 4),
            "postural_tone": round(self.state["postural_tone"], 4),
            "vestibular_coupling": round(self.state["vestibular_coupling"], 4),
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

