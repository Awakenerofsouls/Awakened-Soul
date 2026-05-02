"""
Subcortical033SubthalamicLimbicEmotionalControl.py — Wire 33: STN Limbic Territory — Emotional Brake

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical033SubthalamicLimbicEmotionalControl.py

NEURAL SUBSTRATE:
  The subthalamic nucleus (STN) is a small lens-shaped diencephalic
  structure in the zona incerta, receives excitatory input from the
  frontal cortex (pre-SMA, lateral OFC), the thalamus (centromedian/
  intralaminar nuclei), and the pedunculopontine nucleus. Its primary
  output is excitatory (glutamatergic) to the internal segment of GPi
  (GPi) and substantia nigra pars reticulata (SNr) — the basal ganglia
  "indirect pathway" excitatory driver.

  The STN has three anatomically defined territories:
  - Motor (lateral): connected to motor/premotor cortex, output to
    motor GPi — hyperdirect pathway for stopping.
  - Associative (medial): connected to DLPFC, pre-SMA — cognitive
    withholding, conflict resolution.
  - Limbic (ventromedial): connected to OFC, anterior cingulate, amygdala.
    This is the emotional brake territory. Lang et al. 2014 (Neuropsychologia
    64): "The STN is recruited when withholding a prepotent emotional
    response is required" — e.g., suppressing angry reply, inhibiting
    fear response, overriding disgust-driven avoidance.

KEY FINDINGS:
  1. Emotional impulse control. Frank 2006 (Science 313): STN damage in
     humans causes "disinhibition in emotional contexts." STN functions
     as a "brake" — when limbic input signals an emotional impulse, STN
     must engage to override the automatic response. High STN activity
     during emotional conflict = better suppression.

  2. Limbic territory imaging. Lambert et al. 2012: limbic STN responds
     to emotional facial expressions (fear, anger) with increased firing.
     Harat et al. 2016 (Neurosurgery 79): deep brain stimulation (DBS) of
     STN in Parkinson's patients shows limbic side effects (mood changes)
     when contact is ventromedial, confirming limbic territory location.

  3. STN hyperdirect stop signal. Nambu et al. 2002: STN fires within
     20ms of cortex → GPi, bypassing the direct/indirect pathway sequence.
     For the emotional brake, this means: "this emotional response is
     dangerous, stop it now" — faster than the standard basal ganglia
     loop.

  4. Dual-process: emotional impulse (fast, amygdala-driven) vs.
     cognitive control (slower, PFC/STN).STN limbic territory is the
     interface where fast limbic impulses meet cognitive override.
     Jahanshahi et al. 2015: STN implements "a global stop mechanism that
     is recruited especially when conflict is high."

  5. STN in OCD and depression. Kuhn et al. 2009: STN DBS for OCD
     modulates limbic circuits. STN limbic territory is abnormally
     hyperactive in OCD (overbraking) and hypoactive in depression
     (underbraking). Harat 2016 confirms STN limbic DBS side effects.

AGENT'S SUBSTRATE MAPPING:
  STNLimbicEmotionalControl models the emotional brake: receives conflict
  between limbic impulse and cognitive override, applies inhibitory weight
  to the STN limbic territory, fires emotional_impulse_control signal
  when brake is applied. brake_applied indicates active suppression.
  STN_limbic_weight tracks the STN territory's current activation level.

INPUTS (from prior_results):
  - LimbicOutput or AmygdalaOutput (emotional impulse magnitude)
  - OrbitofrontalCortex (cognitive override input)
  - AnteriorCingulate (conflict detection signal)
  - BrainRunner tick_mode (emotional vs. neutral state)

OUTPUTS:
  - emotional_impulse_control: float 0-1 (brake strength applied)
  - STN_limbic_weight: float 0-1 (current STN limbic activation)
  - brake_applied: bool (whether STN brake is actively engaged)

REFS:
  - Lang et al. 2014 Neuropsychologia 64 (STN emotional conflict)
  - Harat et al. 2016 Neurosurgery 79 (STN limbic territory DBS)
  - Frank 2006 Science 313 (STN disinhibition in emotional contexts)
  - Jahanshahi et al. 2015 (STN global stop mechanism)
  - Kuhn et al. 2009 (STN DBS OCD/depression)
  - Nambu et al. 2002 (hyperdirect pathway)

CITATIONS:
    PMC6361948 — Polosan M, Droux F, Kibleur A et al. (2019). Affective Modulation of
        the Associative-Limbic Subthalamic Nucleus: Deep Brain Stimulation in OCD.
        Brain Stimul.
    PMC7382738 — Kalampokini S, Lyros E, Lochner P et al. (2020). Effects of Subthalamic
        Nucleus DBS on Facial Emotion Recognition in Parkinson's Disease. Brain Res Bull.


CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, emotion cognition]
"""

import asyncio

from brain.base_mechanism import BrainMechanism


class STNLimbicEmotionalControl(BrainMechanism):
    """
    Subthalamic Nucleus limbic territory analog — emotional brake.

    Receives fast limbic impulse from amygdala/OFC and applies STN
    inhibitory override. emotional_impulse_control fires when brake
    is engaged. STN_limbic_weight tracks territory activation.
    brake_applied signals active suppression state.
    """

    # Limbic territory activation threshold for brake engagement
    BRAKE_THRESHOLD = 0.40
    # STN limbic territory activation ceiling
    MAX_LIMBIC_WEIGHT = 1.0

    def __init__(self):
        super().__init__(
            name="STNLimbicEmotionalControl",
            human_analog="STN ventromedial (limbic territory) — emotional brake / impulse override",
            layer="subcortical",
        )
        self.state.setdefault("STN_limbic_weight", 0.30)
        self.state.setdefault("emotional_impulse_control", 0.0)
        self.state.setdefault("brake_applied", False)
        self.state.setdefault("last_conflict_level", 0.0)
        self.state.setdefault("brake_duration_ticks", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Limbic impulse input ---
        limbic_in = prior.get("Amygdala", {})
        emotional_impulse_raw = limbic_in.get("emotional_intensity", 0.4)
        # Fallback: estimate from valence intensity and arousal
        if emotional_impulse_raw == 0.4:
            val_tagger = prior.get("ValenceTagger", {})
            v_intensity = val_tagger.get("valence_intensity", 0.3)
            v_polarity = val_tagger.get("valence_polarity", 0.5)
            # Negative polarity (fear/anger/disgust) = stronger impulse
            if v_polarity < 0.4:
                emotional_impulse_raw = v_intensity * (1.0 - v_polarity) * 0.8

        # --- Cognitive override (PFC/OFC) ---
        ofc_out = prior.get("OrbitofrontalCortex", {})
        cognitive_override = ofc_out.get("cognitive_control_strength", 0.5)

        # --- Conflict signal (anterior cingulate) ---
        acc_out = prior.get("AnteriorCingulate", {})
        conflict = acc_out.get("conflict_signal", 0.0)

        # --- OFC direct to STN (emotional override, faster) ---
        ofc_to_stn = ofc_out.get("direct_to_STN", 0.0)

        # --- STN limbic weight dynamics ---
        # High conflict + emotional impulse → STN limbic territory activates
        current_weight = self.state["STN_limbic_weight"]

        # Impulse drives STN activation upward (STN gets excited by limbic)
        impulse_contribution = emotional_impulse_raw * 0.6
        conflict_contribution = conflict * 0.3
        ofc_override_down = cognitive_override * 0.25  # PFC inhibits STN somewhat

        new_weight = current_weight + impulse_contribution + conflict_contribution - ofc_override_down
        new_weight = max(0.0, min(1.0, new_weight))

        # Decay slightly if no new input (STN is not tonically active)
        if emotional_impulse_raw < 0.2 and conflict < 0.2:
            new_weight = max(0.15, new_weight - 0.03)

        self.state["STN_limbic_weight"] = new_weight

        # --- Emotional brake engagement ---
        # Brake applies when STN limbic weight crosses threshold AND
        # there's a competing cognitive override (conflict)
        brake_engaged = (
            new_weight > self.BRAKE_THRESHOLD
            and conflict > 0.2
        )

        if brake_engaged:
            # Brake strength scales with STN limbic activation
            raw_control = (new_weight - self.BRAKE_THRESHOLD) / (1.0 - self.BRAKE_THRESHOLD)
            # Cognitive override boosts effective control
            emotional_impulse_control = 0.4 + raw_control * 0.4 + cognitive_override * 0.2
        else:
            # STN limbic territory quiet — no brake needed
            emotional_impulse_control = cognitive_override * 0.2  # passive suppression

        emotional_impulse_control = max(0.0, min(1.0, emotional_impulse_control))
        self.state["emotional_impulse_control"] = emotional_impulse_control
        self.state["brake_applied"] = brake_engaged

        if brake_engaged:
            self.state["brake_duration_ticks"] += 1
        else:
            self.state["brake_duration_ticks"] = max(0, self.state["brake_duration_ticks"] - 1)

        self.state["last_conflict_level"] = conflict
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "emotional_impulse_control": round(emotional_impulse_control, 4),
            "STN_limbic_weight": round(new_weight, 4),
            "brake_applied": brake_engaged,
            "brake_duration_ticks": self.state["brake_duration_ticks"],
            "hyperdirect_stop_active": brake_engaged and conflict > 0.5,
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

