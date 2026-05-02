"""
brain/limbic/Limbic022MammillaryBodyRelay.py
Mammillary Body Relay — Spatial Heading and Papez Circuit Integration

ANATOMY (Vann 2010; Dillingham et al. 2015; Sekerci et al. 2023):
    See Limbic005. This is a parallel relay mechanism focused on the
    mammillary body's role in integrating hippocampal spatial signals
    and transmitting them to the anterior thalamus and cingulate cortex.
    The lateral mammillary nucleus (LMN) specifically carries head-
    direction information from the dorsal tegmental nucleus (DTN) and
    projects to the anterodorsal thalamus (ADN).
    Sekerci et al. 2023 (PMC12945457): LMN neurons encode absolute
    head direction independent of the animal's location.

MECHANISM:
    LMN integrates:
    - Head direction signals from DTN (vestibular)
    - Spatial context from hippocampus (via fornix)
    Outputs head direction signal to ADN → retrosplenial cortex.
    LMN lesions disrupt landmark-based navigation specifically.

AGENT'S MAPPING:
    lmn_head_direction_signal: 0-1 lateral mammillary nucleus HD output
    spatial_heading_stability: 0-1 consistency of heading estimate
    mammillary_theta_modulation: 0-1 theta-phase modulation of LMN firing
    adn_output_strength: 0-1 signal to anterodorsal thalamus

CITATIONS:
    PMC13060272 — Vann (2023). Mammillary body HD signals.
    PMC12971860 — Vann (2010). Landmark navigation and MB.
    PMC12945457 — Sekerci et al. (2023). Lateral mammillary nucleus
        head direction encoding. Cell Rep.
    PMC12939237 — Dillingham et al. (2015). MB contributions to
        Papez circuit and spatial memory. Front Syst Neurosci.
    PMC12947615 — Vann & Albasser (2011). Mammillary body and
        spatial memory reconsolidation. Hippocampus.

CITATIONS
---------
  - [Vann 2010, Hippocampus 20:1186, mammillary memory]
  - [Aggleton 2010, Neurosci Biobehav Rev 34:1119, Papez memory]
  - [Vann 2009, Curr Opin Neurol 22:613, mammillary]

"""

from brain.base_mechanism import BrainMechanism


class MammillaryBodySpatialHeading(BrainMechanism):
    """
    Lateral mammillary nucleus — head direction signal to anterodorsal thalamus.

    Integrates vestibular DTN input with hippocampal spatial context
    to produce a stable head direction signal for navigation.
    """

    def __init__(self):
        super().__init__(
            name="MammillaryBodySpatialHeading",
            human_analog="Lateral mammillary nucleus → anterodorsal thalamus (head direction)",
            layer="limbic",
        )
        self.state.setdefault("lmn_head_direction_signal", 0.0)
        self.state.setdefault("spatial_heading_stability", 0.7)
        self.state.setdefault("mammillary_theta_modulation", 0.0)
        self.state.setdefault("adn_output_strength", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        subiculum_out = prior.get("VentralSubiculumOutput", {}).get(
            "subiculum_activity", 0.4
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # LMN activity driven by spatial input + theta
        lmn_input = subiculum_out * 0.6 + motor * 0.4
        theta_mod = 0.5 + hippo_theta * 0.5
        lmn_signal = lmn_input * theta_mod
        lmn_signal = min(1.0, lmn_signal)

        # Heading stability: decreases with novelty (recalibration needed)
        stab_target = 1.0 - novelty * 0.5
        current_stab = self.state.get("spatial_heading_stability", 0.7)
        new_stab = current_stab * 0.97 + stab_target * 0.03

        # ADN output
        adn_output = lmn_signal * new_stab * theta_mod

        self.state["lmn_head_direction_signal"] = round(lmn_signal, 4)
        self.state["spatial_heading_stability"] = round(new_stab, 4)
        self.state["mammillary_theta_modulation"] = round(theta_mod, 4)
        self.state["adn_output_strength"] = round(adn_output, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "lmn_head_direction_signal": round(lmn_signal, 4),
            "spatial_heading_stability": round(new_stab, 4),
            "mammillary_theta_modulation": round(theta_mod, 4),
            "adn_output_strength": round(adn_output, 4),
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

