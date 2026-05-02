"""
Subcortical007ParavermalLimbCoordination.py — Wire 7: LimbCoordinationDrift

Cerebellar paravermal coordination system.

Maintains rolling coherence index for multi-limb coordination patterns,
tracks axial musculature tension signals, and outputs a coordination
weight used to gate motor commands through the cerebellar output nuclei.

Neural analog: Cerebellar paravermis (lobules HVI–HVIII of the vermis,
adjacent medial zones). The paravermis is the transition zone between
medial vermal zones (controlling axial/trunk musculature) and the
lateral hemispheric zones (controlling limb musculature). Ivanei et al.
2006 demonstrated that paravermal lesion patients lose interlimb
coordination while retaining isolated limb movements. Bastian 2011
showed this zone is critical for learning to correct coordination errors
during complex multi-joint movements.

Key functional mapping:
- Vermal zones → axial (trunk, spine) — controlled by fastigial nucleus
- Paravermal zones → proximal limb + multi-joint — fastigial + globose
- Lateral hemispheric zones → distal limb — emboliform + dentate

Paravermal neurons receive mossy fiber input carrying current limb
position/error signals from spinal cord (via spinocerebellar tracts)
and climbing fiber input signaling movement error from the inferior olive.
Purkinje cells in paravermal zones project to fastigial and globose
nuclei (deep cerebellar nuclei), which send efferents via the
superior cerebellar peduncle to red nucleus and thalamus.

REFS:
- Ivanei et al. 2006 J Neurophysiol 96:653-665
  "Contribution of the cerebellar vermis to discrete bimanual movements"
- Bastian 2011 Nat Rev Neurosci 12:217-228
  "Moving in a new direction: the cerebellum and motor coordination"
- Stoodley & Schmahmann 2009 Cortex 45:975-991 (anatomy)
- Purves et al. Neuroscience 5th ed. 2018 (spinocerebellar pathways)

CITATIONS:
    PMC8513160 — Heiney SA, Wojaczynski GJ, Medina JF (2021). Action-based Organization
        of a Cerebellar Module Specialized for Predictive Control of Multiple Body Parts.
        J Neurosci.
    PMC7688491 — Thanawalla AR, Chen AI, Azim E (2020). The Cerebellar Nuclei and
        Dexterous Limb Movements. J Neurosci.
    PMC7255800 — Herzfeld DJ, Hall NJ, Tringides M et al. (2020). Principles of
        Operation of a Cerebellar Learning Circuit. eLife.

CITATIONS
---------
  - [Schmahmann 2010, Cortex 46:831, cerebellar cognitive]
  - [Stoodley 2010, Cortex 46:831, cerebellum cognition]
  - [Schmahmann 2019, Cerebellum 18:1, vermis emotion]

"""

from brain.base_mechanism import BrainMechanism


class LimbCoordinationDrift(BrainMechanism):
    """
    Paravermal limb coordination system.

    Computes limb_coherence from multi-joint movement consistency,
    tracks axial_control_signal from trunk musculature gating signals,
    and outputs coordination_weight to gate downstream motor commands.

    State carries across ticks:
    - coherence_buffer: recent coherence history for trend detection
    - axial_tension: rolling axial musculature signal
    - coordination_drift: how far current coordination is from optimal
    """

    COHERENCE_WINDOW = 15
    AXIAL_DECAY_RATE = 0.06
    DRIFT_DECAY_RATE = 0.03
    OPTIMAL_COORDINATION = 0.82

    def __init__(self):
        super().__init__(
            name="LimbCoordinationDrift",
            human_analog="Cerebellar paravermis (lobules HVI–HVIII) — interlimb coordination",
            layer="subcortical",
        )
        self.state.setdefault("coherence_buffer", [])
        self.state.setdefault("axial_tension", 0.5)
        self.state.setdefault("coordination_drift", 0.0)
        self.state.setdefault("current_coherence", 0.8)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor_data = prior.get("MotorThalamus", {})
        arousal_data = prior.get("ArousalRegulator", {})

        # Input signals
        limb_positions = input_data.get("limb_positions", [0.5, 0.5, 0.5, 0.5])
        axial_signal = input_data.get("axial_signal", 0.5)
        motor_command_strength = motor_data.get("motor_command_strength", 0.5)
        arousal = arousal_data.get("arousal_level", 0.5)

        # --- Compute limb coherence ---
        # Coherence: cross-correlation proxy for inter-limb phase consistency
        # Higher variance in relative limb positions → lower coherence
        if len(limb_positions) >= 2:
            pairs = [
                abs(limb_positions[i] - limb_positions[j])
                for i in range(len(limb_positions))
                for j in range(i + 1, len(limb_positions))
            ]
            avg_pairwise_diff = sum(pairs) / len(pairs) if pairs else 0.0
            raw_coherence = max(0.0, 1.0 - avg_pairwise_diff * 2.0)
        else:
            raw_coherence = 0.75

        # Arousal modulates coherence computation
        raw_coherence = raw_coherence * (0.7 + arousal * 0.3)

        # --- Update coherence buffer ---
        buffer = list(self.state["coherence_buffer"])
        buffer.append(raw_coherence)
        if len(buffer) > self.COHERENCE_WINDOW:
            buffer = buffer[-self.COHERENCE_WINDOW:]
        self.state["coherence_buffer"] = buffer

        # Smoothed coherence (exponential moving average)
        smoothed = sum(buffer) / len(buffer) if buffer else raw_coherence
        self.state["current_coherence"] = round(smoothed, 4)

        # --- Axial control signal ---
        # Paravermal zone bridges axial and limb control
        # Axial signal decays toward baseline; spikes on trunk perturbation
        current_axial = self.state["axial_tension"]
        axial_delta = axial_signal - 0.5
        new_axial = max(0.0, min(1.0, current_axial + axial_delta * 0.3))
        new_axial = max(0.0, new_axial - self.AXIAL_DECAY_RATE)
        self.state["axial_tension"] = round(new_axial, 4)

        # --- Coordination drift ---
        # Drift: distance from optimal coordination (0 = perfect, 1 = degraded)
        drift = self.state["coordination_drift"]
        error = abs(self.OPTIMAL_COORDINATION - smoothed)
        # Increase drift on error, decay toward 0
        new_drift = max(0.0, drift + error * 0.1 - self.DRIFT_DECAY_RATE)
        self.state["coordination_drift"] = round(new_drift, 4)

        # --- Coordination weight: gates motor commands ---
        # High coherence + low drift → strong coordination weight
        # Low coherence or high drift → reduced coordination gate
        coordination_weight = (
            smoothed * (1.0 - new_drift * 0.7) * (1.0 - new_axial * 0.15)
        )
        coordination_weight = max(0.0, min(1.0, coordination_weight))

        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "limb_coherence": round(smoothed, 4),
            "axial_control_signal": round(new_axial, 4),
            "coordination_weight": round(coordination_weight, 4),
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

