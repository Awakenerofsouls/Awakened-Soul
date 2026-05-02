"""
SecondarySomatosensoryCortex — S2 / Parietal Operculum

NEURAL SUBSTRATE
================
The secondary somatosensory cortex (S2) lies on the upper bank of the
lateral sulcus / parietal operculum. Unlike area 3b, S2 contains neurons
with large bilateral receptive fields and integrates input from both
sides of the body (Iwamura 1998; Disbrow 2003). S2 receives feed-forward
projections from areas 3b/1/2 and reciprocal callosal projections from
contralateral S2, producing the cortical substrate for bilateral tactile
integration. S2 is also the first cortical stage where neuronal firing
correlates with the *decision* in tactile discrimination tasks rather
than the raw stimulus, marking the transition from pure perception to
sensorimotor decision-making (Romo et al. 2002).

S2 is required for tactile object recognition and shape integration —
its large RFs and proprioceptive sensitivity make it the first node
capable of representing 3D tactile shape (Hsiao 2008). Lesion data show
S2 is necessary for *learning* tactile discriminations even when the
execution of already-learned discriminations is preserved.

KEY FINDINGS
============
1. Hierarchical somatosensory processing — RF complexity and bilateral
   integration grow from area 3b through area 2 into S2 —
   [Iwamura Y 1998, Curr Opin Neurobiol 8:522, PMID 9751655]
2. S2 neurons are densely interconnected with ipsilateral 3b, PV, area 7b,
   and crucially with contralateral S2 via callosum — bilateral substrate —
   [Disbrow E 2003, J Comp Neurol 462:382, doi:10.1002/cne.10731]
3. Central role of S2 in tactile shape and 3D object perception via
   integration of cutaneous and postural signals —
   [Hsiao S 2008, Curr Opin Neurobiol 18:418, doi:10.1016/j.conb.2008.09.001]
4. S2 neurons encode the *perceptual decision* in flutter discrimination,
   reflecting comparison of past and current stimuli —
   [Romo R 2002, Nat Neurosci 5:1217, doi:10.1038/nn950]
5. Receptive field properties of macaque S2 reveal multiple functional
   submaps with orientation tuning across digit pads —
   [Fitzgerald P 2006, J Neurosci 26:6473, doi:10.1523/JNEUROSCI.5057-05.2006]

INPUTS
======
- PrimarySomatosensoryCortex.s1_drive (S1 → S2 feedforward)
- PrimarySomatosensoryCortex.area_2_signal (deep/joint S1 area 2)
- VentralPosterolateralThalamus.vpl_drive (some direct VPL→S2)
- InsulaPosterior.posterior_insula_signal (interoceptive context)

OUTPUTS
=======
- s2_drive (0-1) — overall S2 activation
- bilateral_integration (0-1) — bilateral RF activity
- tactile_object_signal (0-1) — shape/object recognition
- decision_correlate (0-1) — Romo-style perceptual decision drive
- shape_recognition (0-1) — converged 3D shape coding
- s2_state (str): "object_recognition" | "bilateral_active" |
                  "decision_period" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SecondarySomatosensoryCortex(BrainMechanism):
    """S2 — bilateral somatosensory integration / tactile object recognition."""

    BASELINE = 0.07
    SMOOTH = 0.20
    ACTIVE_THRESHOLD = 0.20
    OBJECT_THRESHOLD = 0.45
    DECISION_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="SecondarySomatosensoryCortex",
            human_analog="Secondary somatosensory cortex (S2 / parietal operculum)",
            layer="neocortical",
        )
        self.state.setdefault("s2_drive", self.BASELINE)
        self.state.setdefault("bilateral_integration", 0.0)
        self.state.setdefault("tactile_object_signal", 0.0)
        self.state.setdefault("decision_correlate", 0.0)
        self.state.setdefault("shape_recognition", 0.0)
        self.state.setdefault("s2_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("object_count", 0)
        self.state.setdefault("tick_count", 0)

    # ----- helpers ----------------------------------------------------------

    def _drive_target(self, s1: float, a2: float,
                      vpl: float, ins: float) -> float:
        """Composite S2 drive (Disbrow 2003 — feed-forward from S1)."""
        target = (self.BASELINE
                  + s1 * 0.45
                  + a2 * 0.25
                  + vpl * 0.10
                  + ins * 0.10)
        return min(1.0, target)

    def _bilateral(self, drive: float, s1: float, a2: float) -> float:
        """Bilateral RF activity (Iwamura 1998, Disbrow 2003)."""
        if drive < 0.15:
            return 0.0
        # bilateral integration grows nonlinearly when drive is sustained
        return min(1.0, drive * 0.4 + s1 * 0.3 + a2 * 0.4)

    def _object_signal(self, drive: float, a2: float, bil: float) -> float:
        """Tactile object signal — needs deep+bilateral integration (Hsiao 2008)."""
        if drive < 0.20 or a2 < 0.10:
            return 0.0
        return min(1.0, drive * 0.3 + a2 * 0.4 + bil * 0.4)

    def _decision_correlate(self, drive: float, obj: float,
                              bil: float) -> float:
        """Romo 2002 — decision-correlated S2 firing during comparison."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + obj * 0.3 + bil * 0.3)

    def _shape_recognition(self, obj: float, bil: float, a2: float) -> float:
        """Shape recognition (Hsiao 2008) — late-stage integration."""
        if obj < 0.15:
            return 0.0
        return min(1.0, obj * 0.5 + bil * 0.3 + a2 * 0.2)

    def _classify_state(self, drive: float, obj: float, bil: float,
                         dec: float) -> str:
        if drive < self.ACTIVE_THRESHOLD:
            return "quiet"
        if obj > self.OBJECT_THRESHOLD:
            return "object_recognition"
        if dec > self.DECISION_THRESHOLD and dec > bil:
            return "decision_period"
        if bil > 0.25:
            return "bilateral_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ----- main tick --------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        s1_data = prior.get("PrimarySomatosensoryCortex", {})
        s1 = float(s1_data.get("s1_drive",
                          s1_data.get("area_3b_signal", 0.0)))
        a2 = float(s1_data.get("area_2_signal", 0.0))

        vpl_data = prior.get("VentralPosterolateralThalamus", {})
        vpl = float(vpl_data.get("vpl_drive",
                          vpl_data.get("body_signal", 0.0)))

        ins_data = prior.get("InsulaPosterior", {})
        ins = float(ins_data.get("posterior_insula_signal",
                            ins_data.get("insula_drive", 0.0)))

        target = self._drive_target(s1, a2, vpl, ins)
        prev_drive = float(self.state.get("s2_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        bil = self._bilateral(new_drive, s1, a2)
        obj = self._object_signal(new_drive, a2, bil)
        dec = self._decision_correlate(new_drive, obj, bil)
        shape = self._shape_recognition(obj, bil, a2)
        state = self._classify_state(new_drive, obj, bil, dec)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        object_count = int(self.state.get("object_count", 0))
        if state == "object_recognition":
            object_count += 1

        self.state["s2_drive"] = round(new_drive, 4)
        self.state["bilateral_integration"] = round(bil, 4)
        self.state["tactile_object_signal"] = round(obj, 4)
        self.state["decision_correlate"] = round(dec, 4)
        self.state["shape_recognition"] = round(shape, 4)
        self.state["s2_state"] = state
        self.state["recent_states"] = recent
        self.state["object_count"] = object_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('s2_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('s2_state', "quiet") if 's2_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "s2_drive": round(new_drive, 4),
            "bilateral_integration": round(bil, 4),
            "tactile_object_signal": round(obj, 4),
            "decision_correlate": round(dec, 4),
            "shape_recognition": round(shape, 4),
            "s2_state": state,
        }

    # ----- summary helpers --------------------------------------------------

    def _engagement_ratio(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        active = sum(1 for s in recent if s != "quiet")
        return active / max(1, len(recent))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("s2_drive", 0.0),
            "object": self.state.get("tactile_object_signal", 0.0),
            "decision": self.state.get("decision_correlate", 0.0),
            "state": self.state.get("s2_state", "quiet"),
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
            return self.state.get('s2_state', "quiet") if 's2_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('s2_drive', 0.0)) if 's2_drive' else 0.0
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
            "drive": self.state.get('s2_drive', 0.0) if 's2_drive' else 0.0,
            "state": self.state.get('s2_state', "quiet") if 's2_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

