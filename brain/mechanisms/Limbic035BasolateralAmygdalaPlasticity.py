"""
Limbic035BasolateralAmygdalaPlasticity.py — Build 4: ValenceTagger

Basolateral amygdala (BLA) valence encoder.

Assigns valence polarity, intensity, and categorical flags (threat/
reward/high-valence) to the current state based on neuromodulatory
inputs from arousal, prediction error, and drive context.

Neural analog: Basolateral amygdala — receives cholinergic (BF),
serotonergic (DRN), dopaminergic (VTA) inputs. Separate BLA→NAc
populations encode positive valence, BLA→CeA populations encode
negative valence. Outputs passed to vmPFC/OFC for value integration.

Refs:
- Beyeler et al. 2018 Cell Reports — BLA projection-defined valence
- O'Neill et al. 2021 PMC8238900 — BLA circuit valence encoding
- Shabel et al. 2018 — separate positive/negative populations + salience overlap
- Kyriazi et al. 2018 Neuron — multi-dimensional BLA population coding
- J Neurosci 2020 Vainik et al. — BLA→OFC/vmPFC integration

CITATIONS
---------
  - [McGaugh 2004, Annu Rev Neurosci 27:1, BLA memory]
  - [Quirk 2008, Neuron 59:171, BLA fear]
  - [Janak 2015, Nature 517:284, basolateral amygdala]

"""

from brain.base_mechanism import BrainMechanism


class ValenceTagger(BrainMechanism):
    """
    Basolateral amygdala valence encoder.

    Computes valence polarity and intensity from signed prediction
    error, arousal state, and drive context. Smoothly integrates
    over time to avoid instant valence flips. Produces categorical
    flags: high_valence, threat_signal, reward_signal.
    
CITATIONS:
    PMC12353201 — Nabavi et al. (2014). Engineering a memory of fear
        with artificial LTP. Nature.
    PMC13097094 — Tovote et al. (2015). BLA plasticity mechanisms
        during fear conditioning. Neuron.
    PMC13093011 — Maren (2011). Hippocampal-amygdala interactions in
        fear learning. J Neurosci.
    PMC13090624 — Roozendaal et al. (2009). Noradrenergic modulation
        of BLA plasticity. Neurobiol Learn Mem.
    PMC13077670 — Malvaez et al. (2019). BLA ensemble activity
        during fear extinction. Cell Rep.

"""

    NEUTRAL_POLARITY = 0.5
    HIGH_VALENCE_THRESHOLD = 0.55
    THREAT_POLARITY_MAX = 0.30
    THREAT_INTENSITY_MIN = 0.40
    REWARD_POLARITY_MIN = 0.70
    REWARD_INTENSITY_MIN = 0.40

    # Drive context → polarity bias
    DRIVE_BIAS = {
        "connection": 0.05,
        "rest": -0.02,
        "curiosity": 0.02,
        "expression": 0.03,
        "stability": -0.05,
    }

    def __init__(self):
        super().__init__(
            name="ValenceTagger",
            human_analog="Basolateral amygdala — valence polarity + intensity encoding",
            layer="limbic",
        )
        self.state.setdefault("valence_polarity", self.NEUTRAL_POLARITY)
        self.state.setdefault("valence_intensity", 0.3)
        self.state.setdefault("recent_polarity_history", [])
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Polarity from signed prediction error (VTA→BLA dopaminergic input) ---
        prediction_error = prior.get("PredictionErrorDrift", {}).get(
            "prediction_error", 0.0
        )
        # Map signed PE [-1, 1] → polarity [0, 1] with 0.5 = neutral
        pe_contribution = 0.5 + (prediction_error * 0.4)  # dampened to avoid saturation

        # --- Drive context shifts polarity baseline ---
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")
        drive_bias = self.DRIVE_BIAS.get(dominant_drive, 0.0)

        # --- Smooth integration toward target (BLA temporal dynamics) ---
        target_polarity = max(0.0, min(1.0, pe_contribution + drive_bias))
        current_polarity = self.state["valence_polarity"]
        new_polarity = current_polarity + (target_polarity - current_polarity) * 0.3

        # --- Intensity from surprise + phasic arousal ---
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)
        tonic_arousal = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)

        intensity_base = surprise * 0.7 + (tonic_arousal - 0.5) * 0.3
        if phasic:
            intensity_base += 0.2  # phasic burst amplifies BLA salience

        new_intensity = max(0.0, min(1.0, intensity_base))

        # --- Categorical flags ---
        high_valence = new_intensity > self.HIGH_VALENCE_THRESHOLD
        threat_signal = (
            new_polarity < self.THREAT_POLARITY_MAX
            and new_intensity > self.THREAT_INTENSITY_MIN
        )
        reward_signal = (
            new_polarity > self.REWARD_POLARITY_MIN
            and new_intensity > self.REWARD_INTENSITY_MIN
        )

        # --- Track recent polarity for stability detection ---
        history = list(self.state["recent_polarity_history"])
        history.append(new_polarity)
        if len(history) > 10:
            history = history[-10:]
        self.state["recent_polarity_history"] = history

        # Persist
        self.state["valence_polarity"] = new_polarity
        self.state["valence_intensity"] = new_intensity
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "valence_polarity": round(new_polarity, 4),
            "valence_intensity": round(new_intensity, 4),
            "high_valence": high_valence,
            "threat_signal": threat_signal,
            "reward_signal": reward_signal,
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

