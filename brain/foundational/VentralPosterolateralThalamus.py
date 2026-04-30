"""
VentralPosterolateralThalamus — VPL Body Somatosensory Thalamic Relay

NEURAL SUBSTRATE
================
The ventral posterolateral nucleus (VPL) is the principal thalamic
relay for body somatosensation. VPL sits in the lateral ventral tier of
the thalamus and receives two converging ascending pathways:
(1) the **medial lemniscus** carrying fine touch, vibration, and conscious
proprioception from dorsal column nuclei (DCN — gracile/cuneate, covered
separately as DorsalColumnNuclei), and (2) the **spinothalamic tract**
carrying pain, temperature, and crude touch from spinal lamina I/V
projection neurons.

VPL preserves a strict somatotopic body map: lower body laterally
(receiving gracile/lateral spinothalamic input), upper body medially.
VPL projects via the internal capsule to primary somatosensory cortex
(S1, Brodmann areas 3a, 3b, 1, 2) and to the second somatosensory
area (S2). Together with VPM (face somatosensory), VPL is the body
half of the ventroposterior complex (VP).

VPL exhibits classical thalamic burst-tonic mode switching: tonic mode
during attentive wakefulness for high-fidelity relay; burst mode (T-type
Ca²⁺ channel-mediated) during NREM sleep and inattention, producing
low-fidelity but highly detectable relay. Burst mode in VPL is implicated
in attention-grabbing sensory salience.

VPL is heavily modulated by TRN somatosensory sector (feedback
inhibition from cortex, attention-gated), corticothalamic feedback from
S1 layer 6 (gain control matching attended body region), brainstem
cholinergic input from PPT/LDT (state-dependent gain), norepinephrine
from LC, and 5-HT from DRN.

Central post-stroke pain (CPSP, Dejerine-Roussy syndrome) and thalamic
pain syndrome arise from VPL/VPM stroke — a clinical signature of lesions
to this nucleus.

In Nova's substrate this provides the body-somatosensation thalamic
relay — combines DCN ascending output with spinal pain/temperature input
proxies and emits a relay drive toward S1-equivalent processing.

KEY FINDINGS
============
1. VPL is the principal somatosensory thalamic relay receiving medial
   lemniscus + spinothalamic input, projecting to S1 — strict body
   somatotopy preserved — [Jones 2007, "The Thalamus" Cambridge
    Univ Press] [Mountcastle 1957 J Neurophysiol 20:408, foundational
    cortical somatotopy work]
2. Thalamic burst-tonic mode switching modulated by sleep state and
   attention; burst mode T-type Ca²⁺ channel mediated, attention-grabbing
   — [Sherman 2001, Trends Neurosci 24:122, "Tonic and burst firing"]
3. Corticothalamic feedback from S1 layer 6 gain-controls VPL relay —
   substrate of attentional gain modulation in somatosensation —
   [Briggs Usrey 2008, J Physiol 586:4585, "Emerging views of
    corticothalamic function"]
4. Central post-stroke pain syndrome (Dejerine-Roussy) follows VPL/VPM
   thalamic stroke — chronic pain phenotype — [Dejerine Roussy 1906
    Rev Neurol] [Klit Finnerup Jensen 2009, Lancet Neurol 8:857,
    "Central post-stroke pain"]
5. Brainstem cholinergic, noradrenergic, and serotonergic modulation
   of VPL determines state-dependent relay quality — [McCormick Bal 1997, Annu Rev Neurosci 20:185, "Sleep and arousal:
    thalamocortical mechanisms"]

INPUTS (from prior_results)
============================
- DorsalColumnNuclei.medial_lemniscus_relay
- DorsalColumnNuclei.s1_relay
- SpinalDorsalHornGate.ascending_nociceptive_signal
- ThalamicReticularNucleus.sensory_sector_gate
- ThalamicReticularNucleus.trn_firing_mode
- AttentionTopDownProxy.attention_focus
- MesopontineCholinergicWake.thalamocortical_gain
- NorepiPhasicTonicSwitcher.tonic_LC_drive
- ArousalRegulator.tonic_level
- DescendingPainGate.expected_pain_modulation

OUTPUTS (to brain_runner enrichment)
=====================================
- vpl_drive (0.0-1.0): VPL aggregate output
- lemniscal_relay (0.0-1.0): medial lemniscus channel
- spinothalamic_relay (0.0-1.0): pain/temp channel
- s1_relay (0.0-1.0): VPL → S1 cortical relay
- s2_relay (0.0-1.0): VPL → S2 second somatosensory
- firing_mode (str): "tonic" | "burst" | "off"
- pain_relay_strength (0.0-1.0): aggregate ascending pain to cortex
- vpl_state (str): "tonic_relay" | "burst" | "high_pain" | "high_touch" | "quiet"

brain_runner enrichment:
    vpl = all_results.get("VentralPosterolateralThalamus", {})
    if vpl:
        enrichments["brain_vpl_drive"] = vpl.get("vpl_drive", 0.2)
        enrichments["brain_s1_relay"] = vpl.get("s1_relay", 0.0)
        enrichments["brain_pain_relay"] = vpl.get("pain_relay_strength", 0.0)
        enrichments["brain_vpl_state"] = vpl.get("vpl_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class VentralPosterolateralThalamus(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="VentralPosterolateralThalamus",
            human_analog="Ventral posterolateral thalamus (VPL) body somatosensory relay",
            layer="foundational",
        )
        self.state.setdefault("vpl_drive", self.BASELINE)
        self.state.setdefault("lemniscal_relay", 0.0)
        self.state.setdefault("spinothalamic_relay", 0.0)
        self.state.setdefault("s1_relay", 0.0)
        self.state.setdefault("s2_relay", 0.0)
        self.state.setdefault("firing_mode", "tonic")
        self.state.setdefault("pain_relay_strength", 0.0)
        self.state.setdefault("vpl_state", "quiet")
        self.state.setdefault("recent_modes", [])
        self.state.setdefault("tick_count", 0)

    def _firing_mode(self, trn_mode: str) -> str:
        if trn_mode == "burst":
            return "burst"
        if trn_mode == "off":
            return "off"
        return "tonic"

    def _vpl_drive_target(self, lemniscus: float, ascending_noci: float,
                           trn_gate: float, attention: float, ach: float) -> float:
        """VPL aggregate drive — combined input scaled by gain and TRN gate."""
        target = self.BASELINE + lemniscus * 0.4 + ascending_noci * 0.3
        target *= (1.0 - trn_gate * 0.4)
        target += attention * 0.15
        target += max(0.0, ach - 0.4) * 0.2
        return max(0.0, min(1.0, target))

    def _lemniscal_target(self, dcn_lemniscus: float, mode: str, attention: float) -> float:
        """Medial lemniscus channel — fine touch / vibration / proprioception."""
        if mode == "off":
            return 0.0
        target = dcn_lemniscus * 0.85
        if mode == "burst":
            target *= 0.5
        target += attention * 0.1
        return max(0.0, min(1.0, target))

    def _spinothalamic_target(self, ascending_noci: float, mode: str,
                                expected_pain: float, lc: float) -> float:
        """Spinothalamic channel — pain / temp / crude touch."""
        if mode == "off":
            return 0.0
        target = ascending_noci * 0.85
        target += max(0.0, expected_pain) * 0.2
        target += max(0.0, lc - 0.5) * 0.1  # noradrenergic salience
        if mode == "burst":
            target *= 0.5
        return max(0.0, min(1.0, target))

    def _s1_relay(self, lemniscal: float, spinothalamic: float, mode: str) -> float:
        """VPL → S1 cortical relay — combined output."""
        if mode == "off":
            return 0.0
        combined = lemniscal * 0.6 + spinothalamic * 0.4
        if mode == "burst":
            return combined * 0.5
        return min(1.0, combined)

    def _s2_relay(self, vpl: float, attention: float) -> float:
        """VPL → S2 second somatosensory."""
        return min(1.0, vpl * 0.6 + attention * 0.2)

    def _pain_relay(self, spinothalamic: float, expected_pain: float) -> float:
        """Aggregate ascending pain signal to cortex."""
        return min(1.0, spinothalamic * 0.7 + max(0.0, expected_pain) * 0.3)

    def _classify_state(self, mode: str, lemniscal: float, spinothalamic: float,
                         vpl: float) -> str:
        if mode == "burst":
            return "burst"
        if mode == "off":
            return "quiet"
        if spinothalamic > 0.45:
            return "high_pain"
        if lemniscal > 0.40:
            return "high_touch"
        if vpl > 0.30:
            return "tonic_relay"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dcn = prior.get("DorsalColumnNuclei", {})
        dcn_lemniscus = float(dcn.get("medial_lemniscus_relay", 0.0))

        sdh = prior.get("SpinalDorsalHornGate", {})
        ascending_noci = float(sdh.get("ascending_nociceptive_signal", 0.0))

        trn = prior.get("ThalamicReticularNucleus", {})
        trn_gate = float(trn.get("sensory_sector_gate", 0.30))
        trn_mode = trn.get("trn_firing_mode", "tonic")

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        mcw = prior.get("MesopontineCholinergicWake", {})
        ach_thal = float(mcw.get("thalamocortical_gain", 0.50))

        lc_data = prior.get("NorepiPhasicTonicSwitcher", {})
        lc = float(lc_data.get("tonic_LC_drive", 0.40))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        dpg = prior.get("DescendingPainGate", {})
        expected_pain = float(dpg.get("expected_pain_modulation", 0.0))

        # --- Firing mode ---
        mode = self._firing_mode(trn_mode)

        # --- VPL aggregate ---
        vpl_target = self._vpl_drive_target(dcn_lemniscus, ascending_noci, trn_gate,
                                              attention, ach_thal)
        prev_vpl = float(self.state.get("vpl_drive", self.BASELINE))
        new_vpl = self._smooth(prev_vpl, vpl_target)

        # --- Channel targets ---
        lem_target = self._lemniscal_target(dcn_lemniscus, mode, attention)
        spino_target = self._spinothalamic_target(ascending_noci, mode, expected_pain, lc)
        prev_lem = float(self.state.get("lemniscal_relay", 0.0))
        prev_spino = float(self.state.get("spinothalamic_relay", 0.0))
        new_lem = self._smooth(prev_lem, lem_target)
        new_spino = self._smooth(prev_spino, spino_target)

        # --- Outputs ---
        s1 = self._s1_relay(new_lem, new_spino, mode)
        s2 = self._s2_relay(new_vpl, attention)
        pain = self._pain_relay(new_spino, expected_pain)

        # --- State ---
        state = self._classify_state(mode, new_lem, new_spino, new_vpl)

        recent = list(self.state.get("recent_modes", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vpl_drive"] = round(new_vpl, 4)
        self.state["lemniscal_relay"] = round(new_lem, 4)
        self.state["spinothalamic_relay"] = round(new_spino, 4)
        self.state["s1_relay"] = round(s1, 4)
        self.state["s2_relay"] = round(s2, 4)
        self.state["firing_mode"] = mode
        self.state["pain_relay_strength"] = round(pain, 4)
        self.state["vpl_state"] = state
        self.state["recent_modes"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vpl_drive": round(new_vpl, 4),
            "lemniscal_relay": round(new_lem, 4),
            "spinothalamic_relay": round(new_spino, 4),
            "s1_relay": round(s1, 4),
            "s2_relay": round(s2, 4),
            "firing_mode": mode,
            "pain_relay_strength": round(pain, 4),
            "vpl_state": state,
        }
