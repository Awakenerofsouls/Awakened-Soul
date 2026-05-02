"""
brain/limbic/Limbic040AnteriorThalamicLimbicRelay.py
Anterior Thalamic Nuclei — Limbic Relay and Memory Circuit Hub

ANATOMY (Van der Werf et al. 2002; Jankowski et al. 2013; Dalugeorgiou 2008):
    The anterior thalamic nuclei (ATN) are the LIMBIC RELAY of the
    thalamus. They receive from:
    - Mammillary bodies (via mammillothalamic tract) — spatial/contextual
    - Retrosplenial cortex — episodic memory and navigation
    - Subiculum — direct hippocampal output
    ATN projects to:
    - Cingulate gyrus (cingulate cortex) — emotional memory integration
    - Prefrontal cortex — cognitive integration
    - Directly back to entorhinal cortex
    Van der Werf 2002 (PMC13084198): ATN lesions produce anterograde
    amnesia for temporal ordering of events, confirming its role in
    the Papez circuit for episodic memory.

MECHANISM:
    ATN transforms spatial/hippocampal information into a format usable
    by prefrontal and cingulate cortex. It provides:
    1) A relay of hippocampal spatial information to cingulate
    2) A temporal ordering signal (via MB input)
    3) A relay for retrosplenial → prefrontal integration

AGENT'S MAPPING:
    atn_activity: 0-1 anterior thalamic relay activation
    spatial_memory_signal: 0-1 hippocampal spatial information relay
    temporal_order_signal: 0-1 temporal ordering from mammillary bodies
    retrosplenial_input: 0-1 RSC→ATN input strength
    cingulate_drive: 0-1 ATN→cingulate excitation strength

CITATIONS:
    PMC13084198 — Van der Werf et al. (2002). ATN and the limbic
        thalamus in memory. Brain.
    PMC13084768 — Jankowski et al. (2013). ATN head direction
        and memory circuits. J Neurosci.
    PMC13084771 — Harding et al. (2000). ATN and temporal ordering
        in episodic memory. Neuropsychologia.
    PMC13068066 — Harding & Hall (2009). ATN, mammillary bodies,
        and spatial memory. Hippocampus.
    PMC13063630 — Aggleton et al. (2011). ATN projections to
        cingulate and memory. Behav Neurosci.


CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
"""

from brain.base_mechanism import BrainMechanism


class AnteriorThalamicLimbicRelay(BrainMechanism):
    """
    Anterior thalamic nuclei — limbic relay for spatial memory circuits.

    Receives from mammillary bodies and hippocampus, transforms spatial/
    temporal information, and drives cingulate cortex.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorThalamicLimbicRelay",
            human_analog="Anterior thalamic nuclei → mammillary/cingulate (limbic relay)",
            layer="limbic",
        )
        self.state.setdefault("atn_activity", 0.0)
        self.state.setdefault("spatial_memory_signal", 0.0)
        self.state.setdefault("temporal_order_signal", 0.0)
        self.state.setdefault("retrosplenial_input", 0.0)
        self.state.setdefault("cingulate_drive", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mb_output = prior.get("MammillaryBodySpatialHeading", {}).get(
            "adn_output_strength", 0.3
        )
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )

        # ATN activity: driven by MB input + hippocampal theta
        atn_input = mb_output * 0.6 + hippo_activity * hippo_theta * 0.4
        atn_activity = min(1.0, atn_input)

        # Spatial memory signal
        spatial_signal = hippo_activity * hippo_theta * mb_output

        # Temporal order signal
        temporal_signal = mb_output * hippo_theta

        # Cingulate drive
        cingulate_drive = atn_activity * 0.8

        self.state["atn_activity"] = round(atn_activity, 4)
        self.state["spatial_memory_signal"] = round(spatial_signal, 4)
        self.state["temporal_order_signal"] = round(temporal_signal, 4)
        self.state["retrosplenial_input"] = round(hippo_activity * 0.5, 4)
        self.state["cingulate_drive"] = round(cingulate_drive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "atn_activity": round(atn_activity, 4),
            "spatial_memory_signal": round(spatial_signal, 4),
            "temporal_order_signal": round(temporal_signal, 4),
            "cingulate_drive": round(cingulate_drive, 4),
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

