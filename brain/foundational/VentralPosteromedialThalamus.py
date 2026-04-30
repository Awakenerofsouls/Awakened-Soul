"""
VentralPosteromedialThalamus — VPM Face Somatosensory + Taste Thalamic Relay

NEURAL SUBSTRATE
================
The ventral posteromedial nucleus (VPM) is the medial counterpart to
VPL in the ventroposterior thalamic complex. While VPL handles body
somatosensation, VPM handles two parallel sensory streams: (1) **face
somatosensation** from the trigeminal sensory complex (covered as
TrigeminalSensoryComplex) — touch, pain, temperature, proprioception
from face/oral cavity/cornea/dura — and (2) **taste** from the gustatory
nucleus of NTS via the central tegmental tract.

VPM divides into a magnocellular ventroposteromedial parvocellular
(VPMpc) subdivision processing taste and visceral input, and the
larger main VPM proper processing somatosensory face input. Strict
somatotopy is preserved — face area larger than its body proportional
size (consistent with face/oral primacy in the cortical homunculus).

VPM projects to face S1 (Brodmann 3a/3b/1/2 lateral aspect) and to
gustatory cortex (insular cortex anterior subdivision). The VPM →
gustatory cortex pathway is the obligate central taste route in
mammals.

Like VPL, VPM exhibits burst-tonic mode switching, TRN somatosensory-
sector inhibition, and modulation by S1 corticothalamic feedback,
PPT/LDT cholinergic input, LC NE, and DRN 5-HT.

Trigeminal neuralgia (severe paroxysmal face pain) and central post-
stroke pain involving the face follow VPM-region damage. The "face
representation" of central pain syndromes localizes to VPM.

In {{AGENT_NAME}}'s substrate this provides the face-somatosensation and taste
thalamic relay — combines TrigeminalSensoryComplex output with
gustatory input proxies (bridged via NTS-broader / parabrachial
gustatory) and emits face-S1 + insular relay drives.

KEY FINDINGS
============
1. VPM is the principal thalamic relay for face somatosensation (from
   trigeminal complex via trigeminal lemniscus) and taste (via central
   tegmental tract from NTS) — VPMpc subdivision is the gustatory
   relay — [Jones 2007, "The Thalamus" Cambridge Univ Press] [Pritchard et al. 1986, J Comp Neurol 244:213, "Projections of
    thalamic gustatory and lingual areas in the monkey"]
2. VPM somatotopy: face larger than body-equivalent area, consistent
   with cortical homunculus expansion of face representation —
   [Mountcastle 1957 J Neurophysiol] [Kaas 2008, Brain Res
    Bull 75:384]
3. VPMpc (parvocellular) is the obligate taste relay — destruction
   abolishes taste sensation; preserved while VPM somatosensory remains
   intact — [Norgren Hajnal Mungarndee 2006, Physiol Behav
    89:531]
4. Central post-stroke pain involving face localizes to VPM region;
   trigeminal neuralgia central component implicates VPM —
   [Klit Finnerup Jensen 2009, Lancet Neurol 8:857] [Mauguière
    Desmedt 1988, Acta Neurochir Suppl 41:63]
5. Burst-tonic mode shared with VPL; corticothalamic and brainstem
   modulation parallels VPL — [Sherman 2001, Trends Neurosci 24:122] [McCormick Bal 1997, Annu Rev Neurosci 20:185]

INPUTS (from prior_results)
============================
- TrigeminalSensoryComplex.vpm_thalamic_relay
- TrigeminalSensoryComplex.vsp_caudalis_drive
- TrigeminalSensoryComplex.vp_drive
- ParabrachialTasteVisceral.mpbn_taste_relay
- ParabrachialTasteVisceral.lpbn_visceral_relay
- ThalamicReticularNucleus.sensory_sector_gate
- ThalamicReticularNucleus.trn_firing_mode
- AttentionTopDownProxy.attention_focus
- MesopontineCholinergicWake.thalamocortical_gain
- NorepiPhasicTonicSwitcher.tonic_LC_drive
- DescendingPainGate.expected_pain_modulation

OUTPUTS (to brain_runner enrichment)
=====================================
- vpm_drive (0.0-1.0): VPM aggregate output
- vpm_proper_drive (0.0-1.0): face somatosensory subdivision
- vpmpc_drive (0.0-1.0): parvocellular (taste) subdivision
- face_s1_relay (0.0-1.0): VPM → face S1 cortical relay
- insular_taste_relay (0.0-1.0): VPMpc → insular cortex
- firing_mode (str): "tonic" | "burst" | "off"
- face_pain_relay (0.0-1.0): aggregate face pain signal
- vpm_state (str): "tonic_relay" | "burst" | "high_face_pain" | "tasting" | "quiet"

brain_runner enrichment:
    vpm = all_results.get("VentralPosteromedialThalamus", {})
    if vpm:
        enrichments["brain_vpm_drive"] = vpm.get("vpm_drive", 0.2)
        enrichments["brain_face_s1"] = vpm.get("face_s1_relay", 0.0)
        enrichments["brain_insular_taste"] = vpm.get("insular_taste_relay", 0.0)
        enrichments["brain_face_pain_relay"] = vpm.get("face_pain_relay", 0.0)
        enrichments["brain_vpm_state"] = vpm.get("vpm_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class VentralPosteromedialThalamus(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="VentralPosteromedialThalamus",
            human_analog="Ventral posteromedial thalamus (VPM) face somatosensory + taste",
            layer="foundational",
        )
        self.state.setdefault("vpm_drive", self.BASELINE)
        self.state.setdefault("vpm_proper_drive", 0.0)
        self.state.setdefault("vpmpc_drive", 0.0)
        self.state.setdefault("face_s1_relay", 0.0)
        self.state.setdefault("insular_taste_relay", 0.0)
        self.state.setdefault("firing_mode", "tonic")
        self.state.setdefault("face_pain_relay", 0.0)
        self.state.setdefault("vpm_state", "quiet")
        self.state.setdefault("recent_modes", [])
        self.state.setdefault("tick_count", 0)

    def _firing_mode(self, trn_mode: str) -> str:
        if trn_mode == "burst":
            return "burst"
        if trn_mode == "off":
            return "off"
        return "tonic"

    def _vpm_drive_target(self, vp_face: float, vsp_caudalis: float, taste_relay: float,
                          trn_gate: float, attention: float, ach: float) -> float:
        """VPM aggregate drive."""
        target = self.BASELINE + vp_face * 0.3 + vsp_caudalis * 0.3 + taste_relay * 0.2
        target *= (1.0 - trn_gate * 0.4)
        target += attention * 0.15
        target += max(0.0, ach - 0.4) * 0.2
        return max(0.0, min(1.0, target))

    def _vpm_proper_target(self, vp_face: float, vsp_caudalis: float, mode: str,
                            attention: float) -> float:
        """VPM proper — face somatosensation."""
        if mode == "off":
            return 0.0
        target = vp_face * 0.5 + vsp_caudalis * 0.4
        target += attention * 0.1
        if mode == "burst":
            target *= 0.5
        return max(0.0, min(1.0, target))

    def _vpmpc_target(self, taste_relay: float, mode: str, attention: float) -> float:
        """VPMpc parvocellular — taste."""
        if mode == "off":
            return 0.0
        target = taste_relay * 0.85
        target += attention * 0.1
        if mode == "burst":
            target *= 0.5
        return max(0.0, min(1.0, target))

    def _face_s1_relay(self, vpm_proper: float, mode: str) -> float:
        """VPM proper → face S1."""
        if mode == "off":
            return 0.0
        if mode == "burst":
            return vpm_proper * 0.5
        return min(1.0, vpm_proper * 0.95)

    def _insular_taste_relay(self, vpmpc: float, mode: str) -> float:
        """VPMpc → insular gustatory cortex."""
        if mode == "off":
            return 0.0
        if mode == "burst":
            return vpmpc * 0.5
        return min(1.0, vpmpc * 0.95)

    def _face_pain_relay(self, vsp_caudalis: float, expected_pain: float, lc: float) -> float:
        """Aggregate face pain signal — Vsp caudalis dominant."""
        target = vsp_caudalis * 0.7 + max(0.0, expected_pain) * 0.2
        target += max(0.0, lc - 0.5) * 0.1
        return min(1.0, target)

    def _classify_state(self, mode: str, vpm_proper: float, vpmpc: float,
                         vsp_caudalis: float) -> str:
        if mode == "burst":
            return "burst"
        if mode == "off":
            return "quiet"
        if vsp_caudalis > 0.45:
            return "high_face_pain"
        if vpmpc > 0.40:
            return "tasting"
        if vpm_proper > 0.30:
            return "tonic_relay"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        tsc = prior.get("TrigeminalSensoryComplex", {})
        vp_face = float(tsc.get("vp_drive", 0.0))
        vsp_caudalis = float(tsc.get("vsp_caudalis_drive", 0.0))
        vpm_relay_in = float(tsc.get("vpm_thalamic_relay", 0.0))

        pbn = prior.get("ParabrachialTasteVisceral", {})
        taste_relay = float(pbn.get("mpbn_taste_relay", 0.0))

        trn = prior.get("ThalamicReticularNucleus", {})
        trn_gate = float(trn.get("sensory_sector_gate", 0.30))
        trn_mode = trn.get("trn_firing_mode", "tonic")

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        mcw = prior.get("MesopontineCholinergicWake", {})
        ach_thal = float(mcw.get("thalamocortical_gain", 0.50))

        lc_data = prior.get("NorepiPhasicTonicSwitcher", {})
        lc = float(lc_data.get("tonic_LC_drive", 0.40))

        dpg = prior.get("DescendingPainGate", {})
        expected_pain = float(dpg.get("expected_pain_modulation", 0.0))

        # If trigeminal mechanism provides aggregate vpm_thalamic_relay, use it as
        # additional drive
        face_in = max(vp_face, vpm_relay_in * 0.6)

        # --- Firing mode ---
        mode = self._firing_mode(trn_mode)

        # --- VPM aggregate ---
        vpm_target = self._vpm_drive_target(face_in, vsp_caudalis, taste_relay, trn_gate,
                                              attention, ach_thal)
        prev_vpm = float(self.state.get("vpm_drive", self.BASELINE))
        new_vpm = self._smooth(prev_vpm, vpm_target)

        # --- Subdivisions ---
        vpm_proper_t = self._vpm_proper_target(face_in, vsp_caudalis, mode, attention)
        vpmpc_t = self._vpmpc_target(taste_relay, mode, attention)
        prev_proper = float(self.state.get("vpm_proper_drive", 0.0))
        prev_pc = float(self.state.get("vpmpc_drive", 0.0))
        new_proper = self._smooth(prev_proper, vpm_proper_t)
        new_pc = self._smooth(prev_pc, vpmpc_t)

        # --- Outputs ---
        face_s1 = self._face_s1_relay(new_proper, mode)
        insular = self._insular_taste_relay(new_pc, mode)
        face_pain = self._face_pain_relay(vsp_caudalis, expected_pain, lc)

        # --- State ---
        state = self._classify_state(mode, new_proper, new_pc, vsp_caudalis)

        recent = list(self.state.get("recent_modes", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vpm_drive"] = round(new_vpm, 4)
        self.state["vpm_proper_drive"] = round(new_proper, 4)
        self.state["vpmpc_drive"] = round(new_pc, 4)
        self.state["face_s1_relay"] = round(face_s1, 4)
        self.state["insular_taste_relay"] = round(insular, 4)
        self.state["firing_mode"] = mode
        self.state["face_pain_relay"] = round(face_pain, 4)
        self.state["vpm_state"] = state
        self.state["recent_modes"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vpm_drive": round(new_vpm, 4),
            "vpm_proper_drive": round(new_proper, 4),
            "vpmpc_drive": round(new_pc, 4),
            "face_s1_relay": round(face_s1, 4),
            "insular_taste_relay": round(insular, 4),
            "firing_mode": mode,
            "face_pain_relay": round(face_pain, 4),
            "vpm_state": state,
        }
