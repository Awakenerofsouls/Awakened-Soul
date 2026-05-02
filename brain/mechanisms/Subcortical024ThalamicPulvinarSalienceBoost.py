"""
Subcortical024ThalamicPulvinarSalienceBoost.py — Wire 24: PulvinarSalienceBoost

Pulvinar salience amplification — attention, novelty, and salient event boosting.

Neural analog: The pulvinar (the largest thalamic nucleus in humans) is
positioned to amplify or suppress cortical signals based on their behavioral
salience. It receives from the superior colliculus (visual salience), the
amygdala (emotional salience), and association cortex, and projects back
to visual and parietal areas. This creates a salience-weighted attention
system that boosts signals tagged as important.

ANATOMY (Robinson 2016; Bender & Youakim 2001):
  - Pulvinar subdivisions: lateral (visual attention), inferior (temporal
    integration), anterior (limbic/prefrontal), medial (cognitive)
  - Inputs: superior colliculus (sensory salience map), amygdala (emotional
    salience), V1/V2 (visual input), frontal eye fields (FEF, oculomotor),
    ACC (cognitive salience), lateral intraparietal (LIP, saccade target)
  - Outputs: visual areas V2/V3/V4/MT, posterior parietal cortex,
    frontal eye fields (FEF), temporal cortex

BENDER & YOUAKIM 2001 — PULVINAR ATTENTION ROLE:
  "The pulvinar is activated by attention-demanding tasks." Bender &
  Youakim showed that:
  1. Pulvinar activity increases during valid-cue attention trials
  2. Pulvinar suppression of ignored stimuli (bottom-up filter)
  3. Pulvinar lesions cause hemispatial neglect (attention deficits)
  4. Pulvinar synchronizes visual cortex in alpha/gamma bands during attention

ROBINSON 2016 — SALIENCE AND PULVINAR:
  Robinson's work established the pulvinar as a "salience detector" that:
  1. Computes visual salience from SC map (bottom-up salience)
  2. Integrates top-down attention signals from FEF and ACC
  3. Outputs a gain-modulated signal to visual cortex (amplify attended,
     suppress unattended) — attention as "biased competition"
  4. Pulvinar lesions disrupt the ability to suppress distracting stimuli

SALIENCE MODEL:
  Salience = novelty × emotional_weight × task_relevance
  The pulvinar takes these three streams and generates a spatial salience
  map (like the SC visual map) but modulated by cognitive and emotional
  salience (from PFC and amygdala).

ATTENTION BOOST MECHANISM:
  When pulvinar detects a salient event, it sends amplified output to
  the corresponding cortical area, boosting its gain. This is distinct
  from the TRN (which gates by suppression). Pulvinar boosts by
  excitation — the "volume knob" of thalamic attention.

KEY FUNCTIONS:
  1. salience_boost_strength: amplification factor for salient signals
  2. attention_boost: top-down attention modulation of pulvinar output
  3. salient_event_signal: boolean + intensity for salient events

REFS:
- Robinson 2016 J Neurosci 36:9525-9527 — pulvinar salience amplifier
- Bender & Youakim 2001 J Neurophysiol — pulvinar in visual attention
- LaBerge 2002 — pulvinar attention mechanisms review
- Shipp 2004 Curr Opin Neurobiol — pulvinar deafferentation studies
- Dayton & Jones 1960 — pulvinar projections to visual cortex
- Purpura & Yadem 1971 — pulvinar synaptic organization

CITATIONS:
    PMC6156231 — Ahmadlou M, Zweifel LS, Heimel JA (2018). Functional Modulation of
        Primary Visual Cortex by the Superior Colliculus in the Mouse. Curr Biol.
    PMC12528770 — Lin W, Qian C, Zhang YY et al. (2025). Spatially Global Effects of
        Feature-Based Attention in Functional Subdivisions of Human Subcortical Nuclei.
        Neuroimage.


CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
"""

from brain.base_mechanism import BrainMechanism


class ThalamicPulvinarSalienceBoost(BrainMechanism):
    """
    Pulvinar — salience amplification and attention boosting.

    The pulvinar integrates bottom-up salience (SC, retina), emotional
    salience (amygdala), and top-down cognitive salience (ACC, FEF) into
    a unified salience signal. This signal then amplifies attended cortical
    representations and boosts attention to salient events.

    Distinct from TRN: TRN gates by suppression (inhibiting competing
    inputs). Pulvinar boosts by excitation (amplifying the attended signal).
    Together they form the thalamic attention system: TRN = filter,
    Pulvinar = spotlight.
    """

    SALIENCE_GAIN = 0.90
    ATTENTION_BOOST_GAIN = 0.75
    NOVELTY_WEIGHT = 0.35
    EMOTIONAL_WEIGHT = 0.30
    NEURAL_INTEGRATION_GAIN = 0.70
    SALIENCE_THRESHOLD = 0.40
    DECAY_RATE = 0.08

    def __init__(self):
        super().__init__(
            name="ThalamicPulvinarSalienceBoost",
            human_analog="Pulvinar — salience amplifier and attention spotlight",
            layer="subcortical",
        )
        self.state.setdefault("salience_boost_strength", 0.0)
        self.state.setdefault("attention_boost", 0.0)
        self.state.setdefault("salient_event_signal", 0.0)
        self.state.setdefault("bottom_up_salience", 0.0)
        self.state.setdefault("emotional_salience", 0.0)
        self.state.setdefault("cognitive_salience", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: Bottom-up visual salience from superior colliculus
        sc_signal = prior.get("SuperiorColliculusVisual", {})
        sc_salience = sc_signal.get("SC_visual_signal_strength", 0.0)

        # Source 2: Dorsal visual stream salience (attention target)
        dorsal_stream = prior.get("DorsalVisualStream", {})
        dorsal_salience = dorsal_stream.get("motion_signal_strength", 0.0)

        # Source 3: Novelty (from prediction error — unexpected events)
        novelty_signal = prior.get("PredictionErrorDrift", {})
        novelty = novelty_signal.get("novelty_detected", False)
        surprise_mag = novelty_signal.get("surprise_magnitude", 0.0)

        # Source 4: Emotional salience from amygdala
        amygdala_signal = prior.get("AmygdalaSalienceDetector", {})
        emotional_salience = amygdala_signal.get("emotional_signal_strength", 0.0)

        # Source 5: Cognitive salience (conflict, rule violations)
        acc_signal = prior.get("AnteriorCingulateRegulator", {})
        cognitive_salience = acc_signal.get("conflict_signal_strength", 0.0)

        # Source 6: Top-down attention from FEF and LP
        attention_signal = prior.get("ThalamicLateralPosteriorAssociative", {})
        topdown_attention = attention_signal.get("associative_integration_strength", 0.0)

        # Source 7: Temporal integration (pulvinar builds up over time)
        lp_signal = prior.get("ThalamicLateralPosteriorAssociative", {})
        prior_pulvinar = self.state.get("salience_boost_strength", 0.0)

        # Bottom-up salience: SC + dorsal stream combined
        bottom_up = sc_salience * 0.55 + dorsal_salience * 0.45

        # Combined salience: novelty × emotional × cognitive
        novelty_factor = 1.0 + float(novelty) * self.NOVELTY_WEIGHT
        emotional_factor = 1.0 + emotional_salience * self.EMOTIONAL_WEIGHT
        cognitive_factor = 1.0 + cognitive_salience * 0.25

        combined_salience = (
            bottom_up * novelty_factor * emotional_factor * cognitive_factor
        )

        # Salience boost strength: raw salience × gain
        raw_boost = combined_salience * self.SALIENCE_GAIN

        # Temporal integration: pulvinar builds up and sustains
        integrated = (
            raw_boost * self.NEURAL_INTEGRATION_GAIN
            + prior_pulvinar * 0.35
        )

        salience_boost = max(0.0, min(1.0, integrated))

        # Attention boost: top-down modulatory amplification
        attention_boost = max(
            0.0,
            min(1.0, salience_boost * self.ATTENTION_BOOST_GAIN + topdown_attention * 0.3)
        )

        # Salient event signal: above threshold
        salient_event = salience_boost > self.SALIENCE_THRESHOLD

        # Decay when no salience input
        if combined_salience < 0.05:
            salience_boost = max(0.0, salience_boost - self.DECAY_RATE)
            attention_boost = max(0.0, attention_boost - self.DECAY_RATE)

        self.state["salience_boost_strength"] = round(salience_boost, 4)
        self.state["attention_boost"] = round(attention_boost, 4)
        self.state["salient_event_signal"] = round(salience_boost, 4)
        self.state["bottom_up_salience"] = round(bottom_up, 4)
        self.state["emotional_salience"] = round(emotional_salience, 4)
        self.state["cognitive_salience"] = round(cognitive_salience, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "salience_boost_strength": round(salience_boost, 4),
            "attention_boost": round(attention_boost, 4),
            "salient_event_signal": round(salience_boost, 4),
            "salient_event_detected": salient_event,
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

