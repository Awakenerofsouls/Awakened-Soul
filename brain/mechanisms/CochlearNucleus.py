"""
CochlearNucleus — Cochlear Nucleus Auditory Brainstem Entry (DCN/VCN)

NEURAL SUBSTRATE
================
The cochlear nucleus (CN) is the obligatory first central station for
auditory input. Auditory nerve fibers from the cochlea bifurcate on
entry to the brainstem, sending one branch to the ventral cochlear
nucleus (VCN) and another to the dorsal cochlear nucleus (DCN). The
two divisions process sound in distinct ways and project to different
downstream targets — VCN to the superior olivary complex (SOC) for
binaural processing and to the lateral lemniscus, DCN directly to the
contralateral inferior colliculus.

VCN contains four principal cell types: bushy cells (spherical and
globular) preserving timing for binaural processing; stellate cells
encoding spectral envelope; octopus cells responding to broadband
transients; and small cell-cap interneurons. Bushy cells secure
phase-locking with tertiary endbulbs of Held synapses — among the
largest and fastest in the CNS — providing the temporal precision
needed for interaural time difference computation in MSO.

DCN is a layered cerebellar-like structure with fusiform and giant
cells as principal output neurons. DCN integrates auditory input with
somatosensory afferents from the dorsal column nuclei and trigeminal
sensory complex — this multisensory integration in DCN is the leading
candidate substrate of somatic tinnitus, where pinching the neck or
clenching the jaw alters tinnitus perception. DCN also encodes spectral
notches needed for sound localization in elevation.

The CN receives extensive descending modulation from the medial
olivocochlear (MOC) system and from the inferior colliculus, allowing
gain control of peripheral auditory input based on attention and
context. Cochlear nucleus dysfunction is implicated in central
auditory processing disorders, hyperacusis, and tinnitus.

In the agent's substrate this provides the auditory-input gateway —
converts raw auditory signal proxies (intensity, frequency, transients)
into VCN/DCN drives feeding SOC and IC mechanisms.

KEY FINDINGS
============
1. Auditory nerve fibers bifurcate to VCN and DCN on entry, with
   VCN feeding SOC for binaural processing and DCN projecting to
   contralateral IC — [reviewed Cant Benson 2003, Brain Res Bull
    60:457-474, "Parallel auditory pathways"; reviewed Oertel Wickesberg
    2002 Hear Res]
2. VCN bushy cells preserve phase-locking via endbulbs of Held — among
   largest/fastest CNS synapses — substrate for temporal precision in
   binaural ITD coding — [reviewed Trussell 1999, Annu Rev Physiol
    61:477; Joris Yin 1995 J Neurophysiol]
3. DCN integrates auditory + somatosensory input from dorsal column
   nuclei and trigeminal complex — substrate of somatic tinnitus —
   [Shore Roberts Langguth 2016, Nat Rev Neurol 12:150-160, "Maladaptive
    plasticity in tinnitus"; Dehmel et al. 2008 Hear Res]
4. DCN fusiform cell hyperactivity and synchrony correlates with
   tinnitus in noise-exposed animals — [Brozoski et al. 2002 J Neurosci
    22:2386; Kaltenbach 2011 Hear Res 276:48-57]
5. Medial olivocochlear (MOC) and IC efferents provide top-down gain
   control of CN — attention-dependent modulation of peripheral input —
   [Guinan 2006 Ear Hear 27:589-607; Jager Kossl 2016 J Comp Neurol]
6. CN receives dense glycinergic/GABAergic inhibition from brainstem
   auditory nuclei — inhibition/sharpening of timing — [Couchman Dei,
    Recio, Frerichs 2012 J Neurosci 32:7934; Sumner 2015 Hear Res]

INPUTS (from prior_results)
============================
- AuditoryInputProxy.sound_intensity (optional; default 0)
- AuditoryInputProxy.frequency_high (optional; default 0)
- AuditoryInputProxy.transient_onset (optional; default False)
- SomatosensoryProxy.head_neck_signal (optional; default 0)
- ArousalRegulator.tonic_level
- NucleusBasalisAcetylcholine.cortical_ach_release
- AttentionTopDownProxy.attention_focus

OUTPUTS (to brain_runner enrichment)
=====================================
- vcn_bushy_drive (0.0-1.0): VCN bushy cell output (timing-preserved)
- vcn_stellate_drive (0.0-1.0): VCN stellate spectral output
- dcn_fusiform_drive (0.0-1.0): DCN principal output
- soc_input (0.0-1.0): VCN→SOC binaural feed
- ic_input_dcn (0.0-1.0): DCN→IC direct projection
- somatic_integration (0.0-1.0): DCN multisensory integration
- moc_gain_control (0.0-1.0): top-down gain of CN
- cn_state (str): "quiet" | "transient" | "sustained" | "somatic_integrated"

brain_runner enrichment:
    cn = all_results.get("CochlearNucleus", {})
    if cn:
        enrichments["brain_vcn_bushy"] = cn.get("vcn_bushy_drive", 0.1)
        enrichments["brain_dcn_fusiform"] = cn.get("dcn_fusiform_drive", 0.1)
        enrichments["brain_soc_input"] = cn.get("soc_input", 0.0)
        enrichments["brain_ic_input_dcn"] = cn.get("ic_input_dcn", 0.0)
        enrichments["brain_cn_state"] = cn.get("cn_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class CochlearNucleus(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.30  # Auditory entry — fast

    def __init__(self):
        super().__init__(
            name="CochlearNucleus",
            human_analog="Cochlear nucleus auditory brainstem entry (VCN/DCN)",
            layer="foundational",
        )
        self.state.setdefault("vcn_bushy_drive", self.BASELINE)
        self.state.setdefault("vcn_stellate_drive", self.BASELINE)
        self.state.setdefault("dcn_fusiform_drive", self.BASELINE)
        self.state.setdefault("soc_input", 0.0)
        self.state.setdefault("ic_input_dcn", 0.0)
        self.state.setdefault("somatic_integration", 0.0)
        self.state.setdefault("moc_gain_control", 0.50)
        self.state.setdefault("cn_state", "quiet")
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _vcn_bushy_target(self, intensity: float, transient: bool, gain: float) -> float:
        """VCN bushy — high-fidelity timing, scales with intensity * gain."""
        target = self.BASELINE + intensity * 0.7 * gain
        if transient:
            target = min(1.0, target + 0.20)
        return min(1.0, target)

    def _vcn_stellate_target(self, intensity: float, gain: float) -> float:
        """VCN stellate — encodes spectral envelope, sustained response."""
        return min(1.0, self.BASELINE + intensity * 0.6 * gain)

    def _dcn_fusiform_target(self, intensity: float, somatic: float, freq_high: float,
                              gain: float) -> float:
        """DCN fusiform — multisensory integration; spectral-notch encoder."""
        target = self.BASELINE + intensity * 0.5 * gain
        target += somatic * 0.3
        target += freq_high * 0.2
        return min(1.0, target)

    def _moc_gain(self, attention: float, ach: float, intensity: float) -> float:
        """Medial olivocochlear gain — top-down. Higher attention = higher gain
        for attended input; ACh boosts gain.
        """
        target = 0.40 + attention * 0.4 + ach * 0.2
        # Loud sound triggers protective MOC reflex (gain reduction)
        if intensity > 0.85:
            target -= (intensity - 0.85) * 0.5
        return max(0.10, min(1.0, target))

    def _soc_input(self, bushy: float, stellate: float) -> float:
        """VCN → SOC binaural feed — bushy (timing) + stellate (intensity)."""
        return min(1.0, bushy * 0.6 + stellate * 0.4)

    def _ic_input_dcn(self, fusiform: float) -> float:
        """DCN → contralateral IC direct projection."""
        return min(1.0, fusiform * 0.95)

    def _somatic_integration(self, fusiform: float, somatic: float) -> float:
        """DCN somatosensory-auditory multisensory — substrate of somatic tinnitus."""
        if somatic < 0.10:
            return 0.0
        return min(1.0, fusiform * 0.5 + somatic * 0.5)

    def _classify_state(self, bushy: float, fusiform: float, somatic_int: float,
                         transient: bool) -> str:
        if somatic_int > 0.30:
            return "somatic_integrated"
        if transient and bushy > 0.40:
            return "transient"
        if bushy > 0.30 or fusiform > 0.30:
            return "sustained"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        audio = prior.get("AuditoryInputProxy", {})
        intensity = float(audio.get("sound_intensity", 0.0))
        freq_high = float(audio.get("frequency_high", 0.0))
        transient = bool(audio.get("transient_onset", False))

        somato = prior.get("SomatosensoryProxy", {})
        head_neck = float(somato.get("head_neck_signal", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        nbm = prior.get("NucleusBasalisAcetylcholine", {})
        ach = float(nbm.get("cortical_ach_release", 0.40))

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        # --- MOC gain ---
        gain_target = self._moc_gain(attention, ach, intensity)
        prev_gain = float(self.state.get("moc_gain_control", 0.50))
        new_gain = self._smooth(prev_gain, gain_target)

        # --- VCN bushy ---
        bushy_target = self._vcn_bushy_target(intensity, transient, new_gain)
        prev_bushy = float(self.state.get("vcn_bushy_drive", self.BASELINE))
        new_bushy = self._smooth(prev_bushy, bushy_target)

        # --- VCN stellate ---
        stellate_target = self._vcn_stellate_target(intensity, new_gain)
        prev_stellate = float(self.state.get("vcn_stellate_drive", self.BASELINE))
        new_stellate = self._smooth(prev_stellate, stellate_target)

        # --- DCN fusiform ---
        fusiform_target = self._dcn_fusiform_target(intensity, head_neck, freq_high, new_gain)
        prev_fusiform = float(self.state.get("dcn_fusiform_drive", self.BASELINE))
        new_fusiform = self._smooth(prev_fusiform, fusiform_target)

        # --- Outputs ---
        soc = self._soc_input(new_bushy, new_stellate)
        ic = self._ic_input_dcn(new_fusiform)
        somatic_int = self._somatic_integration(new_fusiform, head_neck)

        # --- State ---
        state = self._classify_state(new_bushy, new_fusiform, somatic_int, transient)

        recent = list(self.state.get("recent_drives", []))
        recent.append(round(new_bushy, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vcn_bushy_drive"] = round(new_bushy, 4)
        self.state["vcn_stellate_drive"] = round(new_stellate, 4)
        self.state["dcn_fusiform_drive"] = round(new_fusiform, 4)
        self.state["soc_input"] = round(soc, 4)
        self.state["ic_input_dcn"] = round(ic, 4)
        self.state["somatic_integration"] = round(somatic_int, 4)
        self.state["moc_gain_control"] = round(new_gain, 4)
        self.state["cn_state"] = state
        self.state["recent_drives"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vcn_bushy_drive": round(new_bushy, 4),
            "vcn_stellate_drive": round(new_stellate, 4),
            "dcn_fusiform_drive": round(new_fusiform, 4),
            "soc_input": round(soc, 4),
            "ic_input_dcn": round(ic, 4),
            "somatic_integration": round(somatic_int, 4),
            "moc_gain_control": round(new_gain, 4),
            "cn_state": state,
        }
