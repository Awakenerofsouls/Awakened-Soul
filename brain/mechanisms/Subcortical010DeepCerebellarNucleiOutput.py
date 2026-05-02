"""
Subcortical010DeepCerebellarNucleiOutput.py — Wire 10: CerebellarOutputGate

Deep Cerebellar Nuclei (DCN) collective output mechanism.

Models the integrated output of all four deep cerebellar nuclei as a
single cerebellar_output_signal, with separate motor and cognitive
command strength outputs reflecting their distinct downstream targets.

Neural analog: Deep Cerebellar Nuclei (DCN) — four nuclei embedded in
the cerebellar white matter, receiving Purkinje cell inhibition from all
zones of cerebellar cortex and sending efferent projections outward:

1. FASTIGIAL NUCLEUS (medial):
   - Receives: vermal zone Purkinje cells
   - Projects: to spinal cord (vestibulospinal, reticulospinal tracts)
   - Function: axial/postural control, whole-body coordination
   - Efferent: primarily to brainstem reticular formation

2. GLOBOSE NUCLEUS (interposed-anterior, medial):
   - Receives: paravermal zone Purkinje cells
   - Projects: to red nucleus (magnocellular division)
   - Function: interlimb coordination, error correction
   - Efferent: rubropsinal tract → contralateral limb control

3. EMBOLIFORM NUCLEUS (interposed-posterior, lateral):
   - Receives: paravermal/lateral boundary Purkinje cells
   - Projects: to red nucleus (parvocellular division) → thalamus VL
   - Function: precise timing of distal limb movements

4. DENTATE NUCLEUS (lateral, largest):
   - Receives: lateral hemispheric zone Purkinje cells
   - Projects: to VL/VA thalamus → motor and prefrontal cortex
   - Function: motor planning, cognitive sequencing, timing
   - Efferent: superior cerebellar peduncle (see Subcortical011)

Purves et al. Neuroscience 5th ed. 2018 describes DCN as "the sole
output neurons of the cerebellum" — all motor and cognitive cerebellar
signals pass through these nuclei before entering the SCP.

DCN neurons are intrinsically auto-rhythmic: even after Purkinje cell
inhibition is removed, DCN neurons fire spontaneously at ~20-40 Hz.
This intrinsic pacemaking provides the cerebellar clock's baseline
timing signal. Purkinje inhibition modulates this baseline to encode
movement error and timing adjustments.

This mechanism aggregates DCN output from all four nuclei:
- cerebellar_output_signal: the unified cerebellar command
- motor_command_strength: fastigial + globose + emboliform contribution
- cognitive_command_strength: dentate contribution to prefrontal loops

REFS:
- Purves et al. Neuroscience 5th ed. 2018, Oxford UP (DCN anatomy)
- Ito 2008 Scholarpedia 3:1410
- Stoodley & Schmahmann 2009 Cortex 45:975-991
- Apps & Garwicz 2005 Physiol Rev 85:1151-1174
- Ramnani 2006 Nat Rev Neurosci 7:511-522

CITATIONS:
    PMC8273235 — Kakei S, Manto M, Tanaka H et al. (2021). Pathophysiology of
        Cerebellar Tremor: The Forward Model-Related Tremor. Front Neurol.
    PMC10556200 — Fanning A, Kuo SH (2024). Clinical Heterogeneity of Essential
        Tremor: Understanding Neural Substrates of Action Tremor Subtypes.
    PMC8513160 — Heiney SA, Wojaczynski GJ, Medina JF (2021). Action-based Organization
        of a Cerebellar Module Specialized for Predictive Control. J Neurosci.


CITATIONS
---------
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive affective]
"""

from brain.base_mechanism import BrainMechanism


class CerebellarOutputGate(BrainMechanism):
    """
    Deep Cerebellar Nuclei collective output gateway.

    Integrates output from all four DCN nuclei:
    - Fastigial: axial/postural
    - Globose: interlimb coordination
    - Emboliform: precise timing
    - Dentate: cognitive/motor planning

    Outputs:
    - cerebellar_output_signal: unified output
    - motor_command_strength: motor-channel DCN contribution
    - cognitive_command_strength: dentate-channel DCN contribution
    """

    DCN_INTRINSIC_FREQ = 0.65  # Baseline DCN firing rate
    PURKINJE_INHIBITION_GAIN = 0.7
    MOTOR_COGNITIVE_MIX = 0.55  # Baseline motor proportion

    def __init__(self):
        super().__init__(
            name="CerebellarOutputGate",
            human_analog="Deep Cerebellar Nuclei (fastigial + globose + emboliform + dentate)",
            layer="subcortical",
        )
        self.state.setdefault("cerebellar_output_signal", 0.6)
        self.state.setdefault("motor_command_strength", 0.5)
        self.state.setdefault("cognitive_command_strength", 0.5)
        self.state.setdefault("purkinje_inhibition", 0.0)
        self.state.setdefault("dcn_baseline", self.DCN_INTRINSIC_FREQ)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        paraverm_data = prior.get("LimbCoordinationDrift", {})
        lateral_data = prior.get("CognitiveTimingPrecision", {})
        split_data = prior.get("DentateOutputSplit", {})
        arousal_data = prior.get("ArousalRegulator", {})

        # Input signals
        purkinje_inhibition = input_data.get("purkinje_inhibition", 0.0)
        cerebellar_input = input_data.get("cerebellar_input_strength", 0.6)
        motor_active = input_data.get("motor_active", False)
        cognitive_load = input_data.get("cognitive_load", 0.5)
        arousal = arousal_data.get("arousal_level", 0.5)

        # From prior mechanisms
        coordination_weight = paraverm_data.get("coordination_weight", 0.8)
        timing_precision = lateral_data.get("timing_precision", 0.85)
        cognitive_output = split_data.get("cognitive_output", 0.5)
        motor_output = split_data.get("motor_output", 0.5)

        # --- Purkinje inhibition effect ---
        # Purkinje cells fire at ~1-10 Hz during movement, tonically inhibiting DCN.
        # Error signals increase Purkinje firing → stronger inhibition → DCN
        # output suppressed = less commanded movement. Purkinje pause (climbing
        # fiber burst) → disinhibition → DCN fires strongly = movement correction.
        self.state["purkinje_inhibition"] = purkinje_inhibition
        inhibition_effect = purkinje_inhibition * self.PURKINJE_INHIBITION_GAIN

        # --- Motor command strength (fastigial + globose + emboliform) ---
        # These nuclei drive motor output: postural, limb, precise movement
        fastigial_contribution = coordination_weight * 0.35
        globose_contribution = coordination_weight * timing_precision * 0.35
        emboliform_contribution = (
            (0.6 if motor_active else 0.3) * timing_precision * 0.3
        )
        motor_base = fastigial_contribution + globose_contribution + emboliform_contribution

        # Arousal modulation on motor command
        motor_arousal = 1.0 - abs(arousal - 0.6) * 0.4
        motor_raw = motor_base * motor_arousal + motor_output * 0.25
        motor_command_strength = max(0.0, min(1.0, motor_raw))

        # --- Cognitive command strength (dentate) ---
        # Dentate drives cognitive sequencing, timing predictions, planning
        dentate_cognitive = (
            cognitive_output * 0.4
            + timing_precision * 0.3
            + cognitive_load * 0.3
        )
        # Dentate suppressed by strong motor commands (competition for thalamic channel)
        dentate_suppression = motor_command_strength * 0.2 if motor_active else 0.0
        cognitive_raw = dentate_cognitive - dentate_suppression
        cognitive_command_strength = max(0.0, min(1.0, cognitive_raw))

        # --- Unified cerebellar output signal ---
        # DCN intrinsic pacemaking + cerebellar_input - Purkinje inhibition
        dcn_intrinsic = self.state["dcn_baseline"]
        cerebellar_output_signal = (
            dcn_intrinsic * 0.3
            + cerebellar_input * 0.4
            - inhibition_effect * 0.3
        )
        cerebellar_output_signal = max(0.0, min(1.0, cerebellar_output_signal))

        # --- DCN baseline update (slow plasticity) ---
        # DCN baseline slowly shifts toward the commanded output (intrinsic adaptation)
        new_baseline = (
            self.DCN_INTRINSIC_FREQ * 0.8
            + cerebellar_output_signal * 0.2
        )
        self.state["dcn_baseline"] = round(new_baseline, 4)

        self.state["cerebellar_output_signal"] = round(cerebellar_output_signal, 4)
        self.state["motor_command_strength"] = round(motor_command_strength, 4)
        self.state["cognitive_command_strength"] = round(cognitive_command_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cerebellar_output_signal": round(cerebellar_output_signal, 4),
            "motor_command_strength": round(motor_command_strength, 4),
            "cognitive_command_strength": round(cognitive_command_strength, 4),
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

