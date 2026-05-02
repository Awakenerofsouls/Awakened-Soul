"""
NucleusOfDiagonalBandVertical — vDBB / Septohippocampal Cholinergic+GABAergic

NEURAL SUBSTRATE
================
The vertical limb of the diagonal band of Broca (vDBB) is part of the
medial septum-diagonal band (MS-DBB) complex. Together with the medial
septum, vDBB hosts cholinergic, GABAergic, and glutamatergic projection
neurons that drive the hippocampal theta rhythm. vDBB GABAergic
parvalbumin neurons are theta-bursting pacemakers; cholinergic neurons
provide tonic ACh modulation of hippocampal CA1, CA3, DG.

MS-DBB lesion abolishes hippocampal theta and severely impairs spatial
memory (Mizumori 1990). The cholinergic component supports hippocampal
plasticity; the GABAergic component drives the rhythm itself
(Hangya 2009 — PV-GABAergic septal cells are theta pacemakers).

KEY FINDINGS
============
1. Diagonal band of Broca contains cholinergic + GABAergic neurons
   projecting to hippocampus; key septohippocampal pathway —
   [Mesulam 1983, Neuroscience 10:1185, PMID 6320048]
2. MS-DBB lesion abolishes hippocampal theta rhythm + severely impairs
   spatial memory in Morris water maze —
   [Mizumori 1990, Brain Res 528:12, PMID 2245327]
3. PV+ GABAergic MS-DBB neurons are theta pacemakers; firing precedes
   hippocampal theta cycle —
   [Hangya 2009, J Neurosci 29:8094, doi:10.1523/JNEUROSCI.5665-08.2009]
4. Cholinergic vDBB→hippocampus modulation increases CA1 plasticity
   and supports learning —
   [Solari 2018, Eur J Neurosci 48:2199, doi:10.1111/ejn.13838]
5. Optogenetic activation of MS-DBB cholinergic neurons induces theta
   and improves spatial memory performance —
   [Vandecasteele 2014, PNAS 111:13535, doi:10.1073/pnas.1411233111]

INPUTS
======
- BrainstemReticular.arousal_drive (or ArousalRegulator.tonic_level)
- LateralHabenula.lhab_drive (anti-arousal)
- HippocampalCA3.ca3_output (recurrent feedback)

OUTPUTS
=======
- vdbb_drive (0-1)
- theta_signal (0-1) — hippocampal theta pacing
- ach_modulation (0-1) — cholinergic drive
- hippocampal_plasticity_signal (0-1)
- vdbb_state (str): "theta_pacing" | "ach_high" | "rest" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class NucleusOfDiagonalBandVertical(BrainMechanism):
    """vDBB — septohippocampal pacemaker."""

    BASELINE = 0.10
    SMOOTH = 0.20
    THETA_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="NucleusOfDiagonalBandVertical",
            human_analog="Vertical diagonal band of Broca",
            layer="limbic",
        )
        self.state.setdefault("vdbb_drive", self.BASELINE)
        self.state.setdefault("theta_signal", 0.0)
        self.state.setdefault("ach_modulation", 0.0)
        self.state.setdefault("hippocampal_plasticity_signal", 0.0)
        self.state.setdefault("vdbb_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, arousal: float, lhab: float, ca3: float) -> float:
        """vDBB drive (Mesulam 1983)."""
        target = (self.BASELINE
                  + arousal * 0.55
                  - lhab * 0.20
                  + ca3 * 0.15)
        return max(0.0, min(1.0, target))

    def _theta_pacing(self, drive: float, arousal: float) -> float:
        """PV-GABAergic theta pacing (Hangya 2009)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.6 + arousal * 0.4)

    def _ach_modulation(self, drive: float, arousal: float) -> float:
        """Cholinergic tonic modulation (Vandecasteele 2014)."""
        return min(1.0, drive * 0.5 + arousal * 0.4)

    def _plasticity_signal(self, ach: float, theta: float) -> float:
        """Hippocampal plasticity facilitation (Solari 2018)."""
        return min(1.0, ach * 0.6 + theta * 0.4)

    def _classify_state(self, drive: float, theta: float, ach: float) -> str:
        if drive < 0.20:
            return "quiet"
        if theta > self.THETA_THRESHOLD:
            return "theta_pacing"
        if ach > 0.30:
            return "ach_high"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ar_data = prior.get("ArousalRegulator", {})
        if not ar_data:
            ar_data = prior.get("BrainstemReticular", {})
        arousal = float(ar_data.get("tonic_level",
                            ar_data.get("arousal_drive", 0.0)))

        lhab_data = prior.get("LateralHabenula", {})
        lhab = float(lhab_data.get("lhab_drive",
                            lhab_data.get("aversive_signal", 0.0)))

        ca3_data = prior.get("HippocampalCA3", {})
        if not ca3_data:
            ca3_data = prior.get("HippocampalCA3Dorsal", {})
        ca3 = float(ca3_data.get("ca3_output",
                          ca3_data.get("dca3_drive", 0.0)))

        target = self._drive_target(arousal, lhab, ca3)
        prev_drive = float(self.state.get("vdbb_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        theta = self._theta_pacing(new_drive, arousal)
        ach = self._ach_modulation(new_drive, arousal)
        plasticity = self._plasticity_signal(ach, theta)

        state = self._classify_state(new_drive, theta, ach)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vdbb_drive"] = round(new_drive, 4)
        self.state["theta_signal"] = round(theta, 4)
        self.state["ach_modulation"] = round(ach, 4)
        self.state["hippocampal_plasticity_signal"] = round(plasticity, 4)
        self.state["vdbb_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('vdbb_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('vdbb_state', "quiet") if 'vdbb_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "vdbb_drive": round(new_drive, 4),
            "theta_signal": round(theta, 4),
            "theta_drive": round(theta, 4),  # alias
            "ach_modulation": round(ach, 4),
            "hippocampal_plasticity_signal": round(plasticity, 4),
            "vdbb_state": state,
        }

    def _learning_window_strength(self) -> float:
        """ACh + theta opens learning window (Solari 2018)."""
        return float(self.state.get("hippocampal_plasticity_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("vdbb_drive", 0.0),
            "theta": self.state.get("theta_signal", 0.0),
            "ach": self.state.get("ach_modulation", 0.0),
            "state": self.state.get("vdbb_state", "quiet"),
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
            return self.state.get('vdbb_state', "quiet") if 'vdbb_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('vdbb_drive', 0.0)) if 'vdbb_drive' else 0.0
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
            "drive": self.state.get('vdbb_drive', 0.0) if 'vdbb_drive' else 0.0,
            "state": self.state.get('vdbb_state', "quiet") if 'vdbb_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

