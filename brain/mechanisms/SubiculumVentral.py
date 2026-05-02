"""
SubiculumVentral — vSub / Affective Hippocampal Output

NEURAL SUBSTRATE
================
Ventral subiculum (vSub) is the principal output of the ventral
hippocampus, projecting to nucleus accumbens, BNST, hypothalamus,
amygdala, and mPFC. Critical for HPA-axis regulation: ventral subicular
lesions abolish the contextual stress response (Herman 1995). vSub is a
key node integrating contextual valence with autonomic output —
"context goes into vCA1/vSub and stress hormones come out."

Behaviorally, vSub modulates anxiety and HPA reactivity, and serves as
the main path by which contextual learning influences motivated behavior
(via NAc) and stress (via PVN).

KEY FINDINGS
============
1. Ventral subiculum projects to NAc, BNST, hypothalamus, amygdala —
   distinct affective output target set —
   [Groenewegen 1987, Neuroscience 23:103, PMID 3683859]
2. vSub lesions abolish contextual HPA-axis stress response; necessary
   for psychogenic stress integration —
   [Herman 1995, Neuroendocrinology 61:180, PMID 7753337]
3. vSub→NAc projection drives motivated behavior; selective optogenetic
   activation increases approach to reward —
   [Britt 2012, Neuron 76:790, doi:10.1016/j.neuron.2012.09.040]
4. vSub→mPFC projection critical for fear extinction; pathway-specific —
   [Marek 2018, Neuropsychopharmacology 43:680, doi:10.1038/npp.2017.131]
5. vSub neurons encode anxiogenic context; selective vSub silencing
   reduces anxiety in EPM —
   [Kjelstrup 2002, PNAS 99:10825, doi:10.1073/pnas.152112399]

INPUTS
======
- HippocampalCA1Ventral.vca1_drive
- LateralEntorhinalCortex.lec_drive (or EntorhinalCortexGridCells)
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- vsub_drive (0-1)
- nac_drive_signal (0-1)
- bnst_drive_signal (0-1)
- hpa_axis_drive (0-1)
- mpfc_extinction_signal (0-1)
- vsub_state (str): "stress_active" | "reward_drive" | "extinction" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SubiculumVentral(BrainMechanism):
    """vSub — affective hippocampal output / HPA gateway."""

    BASELINE = 0.10
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="SubiculumVentral",
            human_analog="Ventral subiculum (HPA gateway)",
            layer="limbic",
        )
        self.state.setdefault("vsub_drive", self.BASELINE)
        self.state.setdefault("nac_drive_signal", 0.0)
        self.state.setdefault("bnst_drive_signal", 0.0)
        self.state.setdefault("hpa_axis_drive", 0.0)
        self.state.setdefault("mpfc_extinction_signal", 0.0)
        self.state.setdefault("vsub_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, vca1: float, lec: float, intensity: float) -> float:
        """vSub drive (Groenewegen 1987)."""
        target = (self.BASELINE
                  + vca1 * 0.50
                  + lec * 0.20
                  + intensity * 0.15)
        return min(1.0, target)

    def _nac_signal(self, drive: float, sign: int, intensity: float) -> float:
        """vSub→NAc reward drive (Britt 2012)."""
        appetitive = max(0.0, sign * intensity)
        if appetitive < 0.10:
            return drive * 0.30  # baseline projection
        return min(1.0, drive * 0.5 + appetitive * 0.5)

    def _bnst_signal(self, drive: float, sign: int, intensity: float) -> float:
        """vSub→BNST anxiety drive (Kjelstrup 2002)."""
        aversive = max(0.0, -sign * intensity)
        if aversive < 0.10:
            return 0.0
        return min(1.0, drive * 0.5 + aversive * 0.5)

    def _hpa_axis(self, drive: float, aversive: float) -> float:
        """vSub→PVN HPA drive (Herman 1995)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + aversive * 0.6)

    def _mpfc_extinction(self, drive: float, sign: int) -> float:
        """vSub→mPFC fear extinction (Marek 2018)."""
        if sign >= 0:
            return drive * 0.30
        return min(1.0, drive * 0.6)

    def _classify_state(self, drive: float, sign: int, intensity: float,
                          hpa: float) -> str:
        if drive < 0.20:
            return "quiet"
        if hpa > 0.40:
            return "stress_active"
        if sign > 0 and intensity > 0.30:
            return "reward_drive"
        if sign < 0 and intensity > 0.30:
            return "extinction"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vca1_data = prior.get("HippocampalCA1Ventral", {})
        if not vca1_data:
            vca1_data = prior.get("HippocampalCA1", {})
        vca1 = float(vca1_data.get("vca1_drive",
                            vca1_data.get("ca1_output", 0.0)))

        lec_data = prior.get("LateralEntorhinalCortex", {})
        if not lec_data:
            lec_data = prior.get("EntorhinalCortexGridCells", {})
        lec = float(lec_data.get("lec_drive",
                          lec_data.get("ec_output", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))
        aversive = max(0.0, -sign * intensity)

        target = self._drive_target(vca1, lec, intensity)
        prev_drive = float(self.state.get("vsub_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        nac = self._nac_signal(new_drive, sign, intensity)
        bnst = self._bnst_signal(new_drive, sign, intensity)
        hpa = self._hpa_axis(new_drive, aversive)
        mpfc = self._mpfc_extinction(new_drive, sign)

        state = self._classify_state(new_drive, sign, intensity, hpa)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vsub_drive"] = round(new_drive, 4)
        self.state["nac_drive_signal"] = round(nac, 4)
        self.state["bnst_drive_signal"] = round(bnst, 4)
        self.state["hpa_axis_drive"] = round(hpa, 4)
        self.state["mpfc_extinction_signal"] = round(mpfc, 4)
        self.state["vsub_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('vsub_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('vsub_state', "quiet") if 'vsub_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "vsub_drive": round(new_drive, 4),
            "sub_drive": round(new_drive, 4),  # alias
            "nac_drive_signal": round(nac, 4),
            "bnst_drive_signal": round(bnst, 4),
            "hpa_axis_drive": round(hpa, 4),
            "mpfc_extinction_signal": round(mpfc, 4),
            "vsub_state": state,
        }

    def _stress_load_index(self, recent: list) -> float:
        """Sustained HPA engagement = chronic stress (Herman 1995)."""
        if not recent:
            return 0.0
        win = recent[-50:]
        s = sum(1 for x in win if x == "stress_active")
        return s / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("vsub_drive", 0.0),
            "nac": self.state.get("nac_drive_signal", 0.0),
            "hpa": self.state.get("hpa_axis_drive", 0.0),
            "state": self.state.get("vsub_state", "quiet"),
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
            return self.state.get('vsub_state', "quiet") if 'vsub_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('vsub_drive', 0.0)) if 'vsub_drive' else 0.0
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
            "drive": self.state.get('vsub_drive', 0.0) if 'vsub_drive' else 0.0,
            "state": self.state.get('vsub_state', "quiet") if 'vsub_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

