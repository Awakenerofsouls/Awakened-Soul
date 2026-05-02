"""
PrePresubiculum — PrPS / Presubicular Head-Direction Cells

NEURAL SUBSTRATE
================
The presubiculum (specifically the dorsal/superficial layer often termed
"prepresubiculum" or postsubiculum in rodent literature) is the primary
cortical site of head-direction (HD) cell activity. Taube 1990
discovered HD cells here — neurons that fire when the head points in a
specific allocentric direction, independent of location.

Anatomically: receives anterior thalamic nucleus (ATN) head-direction
input, lateral mammillary body input, and projects to medial entorhinal
cortex (MEC). HD information from PrPS is essential for grid-cell
formation in MEC (Winter 2015 — bilateral PrPS lesion abolishes MEC
grid cells).

KEY FINDINGS
============
1. Head-direction cells in postsubiculum/presubiculum fire when head
   points in specific allocentric direction; classical discovery —
   [Taube 1990, J Neurosci 10:420, PMID 2303851]
2. Lesion of presubiculum abolishes grid-cell signal in medial
   entorhinal cortex; HD input necessary for grid formation —
   [Winter 2015, Curr Biol 25:1187, doi:10.1016/j.cub.2015.03.016]
3. HD signal is generated in lateral mammillary nucleus, relayed to ATN,
   and emerges as cortical signal in postsubiculum —
   [Stackman 1997, J Neurosci 17:4349, PMID 9151751]
4. Pharmacological inactivation of presubiculum disrupts spatial
   navigation despite intact place cells —
   [Calton 2003, J Neurosci 23:9719, PMID 14586059]
5. Layer 3 PrPS pyramidal cells project directly to MEC layer 3
   stellate/pyramidal cells where they shape grid coding —
   [Boccara 2010, Nat Neurosci 13:987, doi:10.1038/nn.2602]

INPUTS
======
- AnteriorThalamicPapez.atn_drive (or anterior_thalamic_drive)
- VestibularNuclei.angular_velocity_signal
- LateralMammillaryNucleus.hd_signal (optional)

OUTPUTS
=======
- prps_drive (0-1)
- head_direction_signal (0-1)
- mec_grid_input (0-1)
- allocentric_compass_signal (0-1)
- prps_state (str): "hd_active" | "compass_locked" | "drift" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PrePresubiculum(BrainMechanism):
    """PrPS — head-direction cell layer."""

    BASELINE = 0.10
    SMOOTH = 0.20
    LOCK_THRESHOLD = 0.45

    def __init__(self):
        super().__init__(
            name="PrePresubiculum",
            human_analog="Pre/postsubiculum (head-direction)",
            layer="limbic",
        )
        self.state.setdefault("prps_drive", self.BASELINE)
        self.state.setdefault("head_direction_signal", 0.0)
        self.state.setdefault("mec_grid_input", 0.0)
        self.state.setdefault("allocentric_compass_signal", 0.0)
        self.state.setdefault("prps_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("compass_trace", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, atn: float, vest: float, mam: float) -> float:
        """PrPS drive (Stackman 1997)."""
        target = (self.BASELINE
                  + atn * 0.45
                  + vest * 0.25
                  + mam * 0.15)
        return min(1.0, target)

    def _hd_signal(self, drive: float, atn: float) -> float:
        """HD cell activity (Taube 1990)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.5 + atn * 0.5)

    def _mec_input(self, drive: float, hd: float) -> float:
        """PrPS→MEC grid input (Winter 2015)."""
        return min(1.0, drive * 0.4 + hd * 0.6)

    def _compass(self, hd: float, prev_compass: float, vest: float) -> float:
        """Allocentric compass — integrates angular velocity (Calton 2003)."""
        # Compass updates with HD signal but is dampened by motion
        return min(1.0, prev_compass * 0.85 + hd * 0.20 + vest * 0.10)

    def _classify_state(self, drive: float, hd: float,
                         compass: float, vest: float) -> str:
        if drive < 0.20:
            return "quiet"
        if vest > 0.50 and compass < 0.30:
            return "drift"
        if compass > self.LOCK_THRESHOLD:
            return "compass_locked"
        if hd > 0.30:
            return "hd_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        atn_data = prior.get("AnteriorThalamicPapez", {})
        if not atn_data:
            atn_data = prior.get("AnteriorThalamicNucleus", {})
        atn = float(atn_data.get("atn_drive",
                          atn_data.get("anterior_thalamic_drive", 0.0)))

        vest_data = prior.get("VestibularNuclei", {})
        vest = float(vest_data.get("angular_velocity_signal",
                            vest_data.get("vestibular_drive", 0.0)))

        mam_data = prior.get("LateralMammillaryNucleus", {})
        if not mam_data:
            mam_data = prior.get("MammillaryBody", {})
        mam = float(mam_data.get("hd_signal",
                          mam_data.get("mam_drive", 0.0)))

        target = self._drive_target(atn, vest, mam)
        prev_drive = float(self.state.get("prps_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        hd = self._hd_signal(new_drive, atn)
        mec_in = self._mec_input(new_drive, hd)
        prev_compass = float(self.state.get("compass_trace", 0.0))
        compass = self._compass(hd, prev_compass, vest)

        state = self._classify_state(new_drive, hd, compass, vest)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["prps_drive"] = round(new_drive, 4)
        self.state["head_direction_signal"] = round(hd, 4)
        self.state["mec_grid_input"] = round(mec_in, 4)
        self.state["allocentric_compass_signal"] = round(compass, 4)
        self.state["compass_trace"] = round(compass, 4)
        self.state["prps_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('prps_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('prps_state', "quiet") if 'prps_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "prps_drive": round(new_drive, 4),
            "head_direction_signal": round(hd, 4),
            "mec_grid_input": round(mec_in, 4)
            ,
            "allocentric_compass_signal": round(compass, 4),
            "prps_state": state,
        }

    def _grid_support_strength(self) -> float:
        """MEC grid support = HD * compass stability (Winter 2015)."""
        return float(self.state.get("mec_grid_input", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("prps_drive", 0.0),
            "hd": self.state.get("head_direction_signal", 0.0),
            "compass": self.state.get("allocentric_compass_signal", 0.0),
            "state": self.state.get("prps_state", "quiet"),
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
        if not recent:
            return self.state.get('prps_state', "quiet") if 'prps_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('prps_drive', 0.0)) if 'prps_drive' else 0.0
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

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "drive": self.state.get('prps_drive', 0.0) if 'prps_drive' else 0.0,
            "state": self.state.get('prps_state', "quiet") if 'prps_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

