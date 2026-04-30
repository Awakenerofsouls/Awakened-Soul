"""
PrimarySomatosensoryCortex — S1 / Postcentral Gyrus

NEURAL SUBSTRATE
================
The primary somatosensory cortex (S1) occupies the postcentral gyrus and
comprises four cytoarchitectonic subfields, Brodmann areas 3a, 3b, 1, and
2. Area 3b receives the dense projection from VPL/VPM thalamus and is
considered the primate "S1 proper" (cutaneous representation), area 3a
processes proprioception from muscle spindles, area 1 handles texture
and rapid adaptation features, and area 2 represents deep pressure and
joint kinematics with larger receptive fields. Together the four strips
generate four parallel somatotopic body maps — the Penfield homunculus.

Within each S1 subfield, the columnar organization first described by
Mountcastle in cat (Mountcastle 1957) groups neurons sharing modality
and location into ~300-500 µm vertical units that are the canonical
"cortical columns". Magnification of the digit, lip, and tongue
representations reflects the density of peripheral receptors and the
behavioral importance of those body parts (Penfield & Boldrey 1937).

KEY FINDINGS
============
1. Neurons in cat somatic cortex are grouped into vertical columns sharing
   modality preference and receptive-field location — first physiological
   evidence for columnar cortical architecture —
   [Mountcastle V 1957, J Neurophysiol 20:408, PMID 13439410]
2. Direct cortical stimulation in awake neurosurgical patients produces a
   distorted somatotopic map (the homunculus) of the human postcentral
   and precentral gyrus —
   [Penfield W 1937, Brain 60:389, doi:10.1093/brain/60.4.389]
3. The four anterior parietal architectonic fields (3a, 3b, 1, 2) each
   contain a separate, parallel representation of the body, with distinct
   receptor-class inputs —
   [Kaas J 1979, Science 204:521, doi:10.1126/science.107591]
4. Hierarchical processing within S1: receptive-field complexity grows
   from area 3b to area 2, with bilateral integration emerging in area 2 —
   [Iwamura Y 1998, Curr Opin Neurobiol 8:522, PMID 9751655]
5. Tactile stimulation drives orderly population responses in area 3b that
   support tactile orientation discrimination at perceptual threshold —
   [Bensmaia S 2008, J Neurosci 28:776, PMID 18199777]

INPUTS
======
- VentralPosterolateralThalamus.vpl_drive (cutaneous/proprio body)
- VentralPosteromedialThalamus.vpm_drive (face/oral)
- DorsalColumnNuclei.dcn_signal (lemniscal arrival)
- TrigeminalSensoryComplex.trigeminal_drive (face Vth)

OUTPUTS
=======
- s1_drive (0-1) — overall S1 activation
- area_3b_signal (0-1) — cutaneous/koniocortex
- area_3a_signal (0-1) — proprioceptive
- area_1_signal (0-1) — texture/rapid-adapting
- area_2_signal (0-1) — joint/deep, bilateral
- homunculus_focus (str) — most-engaged body part token
- column_engagement (0-1) — Mountcastle column drive
- s1_state (str): "tactile_active" | "proprio_active" |
                  "fine_discrimination" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PrimarySomatosensoryCortex(BrainMechanism):
    """S1 — postcentral gyrus, four-strip body map, cortical columns."""

    BASELINE = 0.08
    SMOOTH = 0.22
    ACTIVE_THRESHOLD = 0.22
    FINE_THRESHOLD = 0.55
    BODY_PARTS = ("hand", "face", "trunk", "leg", "lip", "tongue")

    def __init__(self):
        super().__init__(
            name="PrimarySomatosensoryCortex",
            human_analog="Primary somatosensory cortex (S1, Brodmann 1/2/3)",
            layer="neocortical",
        )
        self.state.setdefault("s1_drive", self.BASELINE)
        self.state.setdefault("area_3b_signal", 0.0)
        self.state.setdefault("area_3a_signal", 0.0)
        self.state.setdefault("area_1_signal", 0.0)
        self.state.setdefault("area_2_signal", 0.0)
        self.state.setdefault("homunculus_focus", "none")
        self.state.setdefault("column_engagement", 0.0)
        self.state.setdefault("s1_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ----- helper methods ---------------------------------------------------

    def _drive_target(self, vpl: float, vpm: float,
                      dcn: float, trig: float) -> float:
        """Pooled S1 drive (Kaas 1979 — VPL/VPM koniocortical core)."""
        target = (self.BASELINE
                  + vpl * 0.40
                  + vpm * 0.20
                  + dcn * 0.20
                  + trig * 0.10)
        return min(1.0, target)

    def _area_3b(self, drive: float, vpl: float, vpm: float,
                 dcn: float) -> float:
        """Area 3b — cutaneous koniocortex (Kaas 1979)."""
        if drive < 0.10:
            return 0.0
        body = max(vpl, vpm)
        return min(1.0, drive * 0.5 + body * 0.4 + dcn * 0.2)

    def _area_3a(self, drive: float, vpl: float, dcn: float) -> float:
        """Area 3a — muscle spindle / proprioception (Iwamura 1998)."""
        if drive < 0.10:
            return 0.0
        # 3a depends most on deep proprioceptive afferents (DCN proprio)
        return min(1.0, drive * 0.4 + dcn * 0.5 + vpl * 0.2)

    def _area_1(self, drive: float, area_3b: float) -> float:
        """Area 1 — rapid-adapting / texture; downstream of 3b."""
        if area_3b < 0.10:
            return 0.0
        return min(1.0, drive * 0.3 + area_3b * 0.7)

    def _area_2(self, drive: float, area_1: float,
                area_3a: float) -> float:
        """Area 2 — deep, joint, bilateral integration (Iwamura 1998)."""
        if drive < 0.12:
            return 0.0
        return min(1.0, drive * 0.3 + area_1 * 0.4 + area_3a * 0.3)

    def _column_engagement(self, drive: float, a3b: float,
                            a1: float) -> float:
        """Mountcastle 1957 — vertical columnar drive proxy."""
        return min(1.0, drive * 0.5 + a3b * 0.3 + a1 * 0.2)

    def _homunculus_focus(self, vpl: float, vpm: float,
                           trig: float) -> str:
        """Penfield 1937 — pick the dominant body region."""
        if max(vpl, vpm, trig) < 0.10:
            return "none"
        if vpm > vpl and vpm > trig:
            return "lip"  # VPM = oral/face — lip has the largest cortical area
        if trig > vpl and trig > vpm:
            return "face"
        # vpl-dominant: roughly distinguish hand vs trunk vs leg by magnitude
        if vpl > 0.55:
            return "hand"
        if vpl > 0.30:
            return "trunk"
        return "leg"

    def _classify_state(self, drive: float, a3b: float,
                         a3a: float, a1: float) -> str:
        if drive < self.ACTIVE_THRESHOLD:
            return "quiet"
        if a1 > self.FINE_THRESHOLD or a3b > self.FINE_THRESHOLD:
            return "fine_discrimination"
        if a3a > a3b:
            return "proprio_active"
        return "tactile_active"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ----- main tick --------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vpl_data = prior.get("VentralPosterolateralThalamus", {})
        vpl = float(vpl_data.get("vpl_drive",
                          vpl_data.get("body_signal", 0.0)))

        vpm_data = prior.get("VentralPosteromedialThalamus", {})
        vpm = float(vpm_data.get("vpm_drive",
                          vpm_data.get("face_signal", 0.0)))

        dcn_data = prior.get("DorsalColumnNuclei", {})
        dcn = float(dcn_data.get("dcn_signal",
                          dcn_data.get("dcn_drive", 0.0)))

        trig_data = prior.get("TrigeminalSensoryComplex", {})
        trig = float(trig_data.get("trigeminal_drive",
                            trig_data.get("trig_signal", 0.0)))

        target = self._drive_target(vpl, vpm, dcn, trig)
        prev_drive = float(self.state.get("s1_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        a3b = self._area_3b(new_drive, vpl, vpm, dcn)
        a3a = self._area_3a(new_drive, vpl, dcn)
        a1 = self._area_1(new_drive, a3b)
        a2 = self._area_2(new_drive, a1, a3a)
        col = self._column_engagement(new_drive, a3b, a1)
        focus = self._homunculus_focus(vpl, vpm, trig)
        state = self._classify_state(new_drive, a3b, a3a, a1)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["s1_drive"] = round(new_drive, 4)
        self.state["area_3b_signal"] = round(a3b, 4)
        self.state["area_3a_signal"] = round(a3a, 4)
        self.state["area_1_signal"] = round(a1, 4)
        self.state["area_2_signal"] = round(a2, 4)
        self.state["homunculus_focus"] = focus
        self.state["column_engagement"] = round(col, 4)
        self.state["s1_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "s1_drive": round(new_drive, 4),
            "area_3b_signal": round(a3b, 4),
            "area_3a_signal": round(a3a, 4),
            "area_1_signal": round(a1, 4),
            "area_2_signal": round(a2, 4),
            "homunculus_focus": focus,
            "column_engagement": round(col, 4),
            "s1_state": state,
        }

    # ----- summary helpers --------------------------------------------------

    def _dominant_subfield(self) -> str:
        a3b = float(self.state.get("area_3b_signal", 0.0))
        a3a = float(self.state.get("area_3a_signal", 0.0))
        a1 = float(self.state.get("area_1_signal", 0.0))
        a2 = float(self.state.get("area_2_signal", 0.0))
        vals = {"3b": a3b, "3a": a3a, "1": a1, "2": a2}
        best = max(vals.items(), key=lambda kv: kv[1])
        if best[1] < 0.05:
            return "none"
        return best[0]

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("s1_drive", 0.0),
            "subfield": self._dominant_subfield(),
            "focus": self.state.get("homunculus_focus", "none"),
            "state": self.state.get("s1_state", "quiet"),
        }
