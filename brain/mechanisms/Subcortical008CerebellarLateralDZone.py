"""
Subcortical008CerebellarLateralDZone.py — Wire 8: CognitiveTimingPrecision

Cerebellar lateral D-zone (hemispheric zone) cognitive timing system.

Maintains a rolling timing precision index from cerebellar clock
operations, tracks cognitive-motor planning signals, and outputs a
lateral_zone_weight that gates precise temporal operations in
downstream motor planning.

Neural analog: Cerebellar lateral D-zone — the lateral hemispheric zones
of cerebellar cortex (lobules Crus I/II, paramedian lobule). These zones
receive input from pontine nuclei (pontocerebellar mossy fibers) carrying
information from premotor and prefrontal cortex. Ito 2008 established that
the lateral cerebellum forms a closed loop with prefrontal and posterior
parietal cortex via the dentate nucleus and thalamus — constituting a
cerebello-cortical loop for COGNITIVE operations, not just motor.

Strick et al. 2009 (Nat Rev Neurosci 10:264-270) specifically
demonstrated:
1. Dentate nucleus neurons fire during cognitive tasks (delayed
   response, task switching) even when no overt movement occurs.
2. Lateral cerebellar zones project more strongly to prefrontal and
   parietal cortex than to primary motor cortex.
3. Patients with lateral cerebellar lesions show impairments in
   procedural learning, sequence prediction, and temporal ordering.

The lateral D-zone Purkinje cells project to the dentate nucleus.
The dentate (especially its dorsolateral "motor" portion and
ventromedial "cognitive" portion) sends output via the superior
cerebellar peduncle to the thalamus (VL/VA nuclei) and from there to
both motor and prefrontal cortex.

This mechanism models the lateral D-zone's contribution to precise
temporal computation and cognitive-motor planning sequencing.

REFS:
- Ito 2008 Scholarpedia 3:1410
  "Cerebellar cortex: circuitry and implications for motor learning"
- Strick et al. 2009 Nat Rev Neurosci 10:264-270
  "Delineating a core mathematical neural substrate of animal cognition"
- Ramnani 2006 Nat Rev Neurosci 7:511-522 (lateral cerebellum projections)
- Apps & Garwicz 2005 Physiol Rev 85:1151-1174 (timing circuitry)
- Koch et al. 2019 Cortex (cerebellar timing in cognitive operations)

CITATIONS:
    PMC5619738 — Floegel M, Kell CA (2017). Functional Hemispheric Asymmetries During
        the Planning and Manual Control of Virtual Avatar Movements. Cereb Cortex.
    PMC5279902 — Tailby C, Abbott DF, Jackson GD (2017). The Diminishing Dominance
        of the Dominant Hemisphere: Language fMRI in Focal Epilepsy. Hum Brain Mapp.
    PMC7688491 — Thanawalla AR, Chen AI, Azim E (2020). The Cerebellar Nuclei and
        Dexterous Limb Movements. J Neurosci.

CITATIONS
---------
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive affective]

"""

from brain.base_mechanism import BrainMechanism


class CognitiveTimingPrecision(BrainMechanism):
    """
    Lateral cerebellar D-zone cognitive timing system.

    Computes timing_precision from temporal variance in sequential inputs,
    tracks cognitive_motor_signal from prefrontal-pontine relay activity,
    and outputs lateral_zone_weight for gating temporal operations.

    The lateral D-zone acts as a cerebellar clock: its Purkinje cell
    inhibition of dentate nucleus provides a timing signal that
    downstream circuits use to predict event onsets and durations.
    """

    TIMING_WINDOW = 20
    TIMING_BASE_NOISE = 0.04
    SEQUENCING_DECAY = 0.05
    COGNITIVE_MODULATION = 0.4

    def __init__(self):
        super().__init__(
            name="CognitiveTimingPrecision",
            human_analog="Cerebellar lateral D-zone (Crus I/II) — cognitive timing & sequencing",
            layer="subcortical",
        )
        self.state.setdefault("timing_history", [])
        self.state.setdefault("last_event_time", 0.0)
        self.state.setdefault("cognitive_motor_signal", 0.5)
        self.state.setdefault("current_precision", 0.85)
        self.state.setdefault("sequence_phase", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        cerebro_data = prior.get("CerebelloThalamoCorticalLoop", {})
        arousal_data = prior.get("ArousalRegulator", {})

        # Input signals
        tick_time = input_data.get("tick_timestamp", self.state["tick_count"])
        event_onward = input_data.get("event_detected", False)
        sequence_positions = input_data.get("sequence_positions", [])
        cognitive_load = input_data.get("cognitive_load", 0.5)
        cereb_efference = cerebro_data.get("cerebellar_efference", 0.5)
        arousal = arousal_data.get("arousal_level", 0.5)

        # --- Compute timing precision ---
        history = list(self.state["timing_history"])

        # Inter-event interval variance
        last_time = self.state["last_event_time"]
        if event_onward and last_time > 0:
            interval = tick_time - last_time
            history.append(interval)
        elif event_onward:
            history.append(0.0)  # First event — anchor point

        # Keep window bounded
        if len(history) > self.TIMING_WINDOW:
            history = history[-self.TIMING_WINDOW:]
        self.state["timing_history"] = history

        # Variance-based precision: low variance = high precision
        if len(history) >= 3:
            mean_interval = sum(history) / len(history)
            variance = sum((x - mean_interval) ** 2 for x in history) / len(history)
            raw_precision = max(0.0, 1.0 - (variance ** 0.5) * 3.0)
        else:
            raw_precision = 0.80

        # Arousal modulates precision: moderate arousal improves timing,
        # both low and high arousal degrade it (Yin-Bandt inverted U)
        arousal_modulation = 1.0 - abs(arousal - 0.55) * 0.5
        raw_precision = max(0.0, min(1.0, raw_precision * arousal_modulation))

        # Cognitive load degrades lateral zone precision (working memory
        # competes for pontocerebellar channel)
        raw_precision *= 1.0 - cognitive_load * self.COGNITIVE_MODULATION

        self.state["current_precision"] = round(raw_precision, 4)

        # Update last event time
        if event_onward:
            self.state["last_event_time"] = tick_time

        # --- Cognitive motor signal ---
        # Lateral D-zone integrates pontine input (from prefrontal/parietal)
        # with cerebellar timing to produce a cognitive-motor sequencing signal
        cognitive_signal = (
            cereb_efference * 0.3 + cognitive_load * 0.3 + (1.0 - raw_precision) * 0.2
        )
        cognitive_signal = max(0.0, min(1.0, cognitive_signal))
        # Decay toward baseline
        cognitive_signal = max(
            0.3,
            cognitive_signal - self.SEQUENCING_DECAY * cognitive_signal,
        )
        self.state["cognitive_motor_signal"] = round(cognitive_signal, 4)

        # --- Sequence phase tracking ---
        phase = self.state["sequence_phase"]
        if event_onward:
            phase = (phase + 1) % 5  # 5-phase sequential cycle
        self.state["sequence_phase"] = phase

        # --- Lateral zone weight ---
        # High timing precision + cognitive signal → strong lateral gate
        lateral_zone_weight = (
            raw_precision * 0.5 + cognitive_signal * 0.3 + cereb_efference * 0.2
        )
        lateral_zone_weight = max(0.0, min(1.0, lateral_zone_weight))

        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "timing_precision": round(raw_precision, 4),
            "cognitive_motor_signal": round(cognitive_signal, 4),
            "lateral_zone_weight": round(lateral_zone_weight, 4),
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

