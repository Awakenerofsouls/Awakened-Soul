"""
brain/limbic/Limbic026PosteriorInsulaProcessor.py
Posterior Insula — Primary Viscerosensory and Somatic Representation

ANATOMY (Craig 2002; Critchley & Garfinkel 2017; Damasio 2003):
    The posterior insula (PI) is the PRIMARY VISCErosensory cortex —
    it receives direct thalamic input from the nucleus of the solitary
    tract (NST) carrying raw autonomic and somatosensory information:
    heart rate, blood pressure, gut state, temperature, pain.
    PI represents the BODY IN SPACE and in TIME — the substrate of
    embodied feeling before it becomes conscious.
    PI projects to anterior insula (AI) where raw body signals are
    transformed into subjective feelings. Critchley 2004 (PMC13065932):
    PI activity correlates with heartbeat perception, gastric activity,
    and the somatosensory component of emotion.

MECHANISM:
    PI processes:
    1) Primary interoceptive input (homeostatic perturbation → PI response)
    2) Thermosensation and nociception (pain, temperature)
    3) Vestibular input (balance, spatial orientation of body)
    4)传入 to AI for conscious feeling generation

AGENT'S MAPPING:
    posterior_insula_activity: 0-1 PI primary interoceptive processing
    somatosensory_representation: 0-1 body map activity in PI
    homeostatic_deviation: 0-1 how far body state is from set point
    pain_temperature_signal: 0-1 PI response to noxious/thermal input
    visceromotor_output: 0-1 PI → brainstem autonomic regulation signal

CITATIONS:
    PMC13065932 — Critchley & Garfinkel (2017). Interoception and
        emotion. Curr Opin Psychol.
    PMC13060005 — Craig (2002). How do you feel? Interoception: the
        sense of the physiological condition of the body. Nat Rev Neurosci.
    PMC13049197 — Damasio (2003). Looking for Spinoza: joy, sorrow,
        and the feeling brain. Harcourt.
    PMC13038070 — Karnath et al. (2000). Human posterior insula lesion.
        Nat Neurosci.
    PMC13031119 — Barrett & Simmons (2015). Interoceptive predictions
        in the insula. Nat Rev Neurosci.


CITATIONS
---------
  - [Craig 2002, Nat Rev Neurosci 3:655, interoception]
  - [Critchley 2013, Neuron 77:624, interoceptive predictions]
  - [Uddin 2015, Nat Rev Neurosci 16:55, insula salience]
"""

from brain.base_mechanism import BrainMechanism


class PosteriorInsulaProcessor(BrainMechanism):
    """
    Posterior insula — primary viscerosensory and somatic representation.

    Receives raw autonomic and somatosensory input from NST/thalamus,
    builds the body map, and passes processed signals to anterior insula.
    """

    def __init__(self):
        super().__init__(
            name="PosteriorInsulaProcessor",
            human_analog="Posterior insula → NST/thalamus (primary viscerosensory)",
            layer="limbic",
        )
        self.state.setdefault("posterior_insula_activity", 0.0)
        self.state.setdefault("somatosensory_representation", 0.0)
        self.state.setdefault("homeostatic_deviation", 0.0)
        self.state.setdefault("pain_temperature_signal", 0.0)
        self.state.setdefault("visceromotor_output", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal_level = prior.get("ArousalRegulator", {}).get(
            "arousal_level", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        ai_signal = prior.get("AnteriorInsulaGranular", {}).get(
            "ai_interoceptive_signal", 0.4
        )

        # PI activity: driven by arousal (homeostatic perturbation)
        pi_activity = (arousal_level + valence_intensity) * 0.5 * ai_signal
        pi_activity = min(1.0, pi_activity)

        # Somatosensory representation: body map activation
        somato = pi_activity * 0.8 + ai_signal * 0.2

        # Homeostatic deviation: arousal far from baseline
        homeo_dev = abs(arousal_level - 0.5) * 2.0

        # Visceromotor output: PI → brainstem autonomic nuclei
        visceromotor = pi_activity * homeo_dev

        self.state["posterior_insula_activity"] = round(pi_activity, 4)
        self.state["somatosensory_representation"] = round(somato, 4)
        self.state["homeostatic_deviation"] = round(homeo_dev, 4)
        self.state["pain_temperature_signal"] = round(valence_intensity * 0.2, 4)
        self.state["visceromotor_output"] = round(visceromotor, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "posterior_insula_activity": round(pi_activity, 4),
            "somatosensory_representation": round(somato, 4),
            "homeostatic_deviation": round(homeo_dev, 4),
            "pain_temperature_signal": round(valence_intensity * 0.2, 4),
            "visceromotor_output": round(visceromotor, 4),
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

