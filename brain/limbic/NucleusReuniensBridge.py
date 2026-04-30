"""
NucleusReuniensBridge -- Re Thalamus / Hippocampus-mPFC Bidirectional Bridge

NEURAL SUBSTRATE
================
The nucleus reuniens (Re) is a midline thalamic nucleus sitting in the
ventral midline that has emerged in recent years as a critical node
for hippocampus-prefrontal cortex (mPFC) communication. Re is uniquely
positioned: it receives input from mPFC and projects bidirectionally
to ventral hippocampal CA1 and to mPFC. This makes it the principal
trans-thalamic relay enabling mPFC-hippocampal coordination needed for
working memory, cognitive flexibility, contextual fear, and consolidation.

The Vertes/Hoover/Cassel work has established Re as essential for
spatial working memory and PFC-dependent contextual fear discrimination.
Re lesions impair delayed nonmatch-to-position tasks and degrade
discrimination of safe vs threat contexts (Hallock et al. 2016; Layfield
Patton Hallock Griffin 2015). Re also supports mPFC-driven hippocampal
coordination during memory consolidation: Re projections to dorsal CA1
gate slow-wave-coupled cortico-hippocampal dialogues during NREM.

Re contains glutamatergic projection neurons that synchronize their
activity with mPFC theta and slow oscillations. Re activity gates
trans-thalamic information flow -- when Re is silenced, mPFC and
hippocampal activity decouple. Re neurons also exhibit complex spike
patterns coupled to both PFC and hippocampal rhythms.

The closely related rhomboid nucleus (Rh, dorsal to Re) has overlapping
function and is sometimes considered jointly. Re also projects to
amygdala (BLA), supporting fear-extinction-related mPFC-BLA-hippocampus
coordination.

In Nova's substrate this provides the hippocampus-mPFC trans-thalamic
bridge -- combines mPFC drive (proxy via attention/working memory) with
hippocampal output (CA1 → mPFC relay) and emits a Re drive supporting
working memory and cognitive integration.

KEY FINDINGS
============
1. Nucleus reuniens is essential for spatial working memory -- lesions
   impair delayed-nonmatch tasks dependent on PFC-hippocampus
   integration -- [Hallock Wang Griffin 2016, J Neurosci 36:8372-8389,
    "Ventral midline thalamus is critical for hippocampal-prefrontal
    synchrony and spatial working memory"]
2. Re supports PFC-dependent contextual fear discrimination -- Re
   silencing degrades safe vs threat context distinction --
   [Ramanathan Jin Giustino Payne Maren 2018, Cell Rep 22:1141-1153,
    "Prefrontal projections to the thalamic nucleus reuniens
    mediate fear extinction"]
3. Re gates HPC-PFC theta coherence -- silencing Re decouples HPC and
   mPFC oscillatory activity -- [Hallock 2016 J Neurosci]
4. Re→ ventral CA1 projection mediates trans-thalamic information
   transfer; activity-coupled to mPFC theta -- [Cassel et al. 2013
    Prog Neurobiol 111:34, "The reuniens and rhomboid nuclei: neuro-
    anatomy, electrophysiological characteristics and behavioral
    implications"]
5. Re lesions disrupt slow-wave-coupled hippocampal-cortical dialogue
   during NREM consolidation -- [Latchoumane Ngo Born Shin 2017 Neuron
    95:424; reviewed Pereira de Vasconcelos Cassel 2015]

INPUTS (from prior_results)
============================
- HippocampalCA1Output.ca1_pyramidal_drive
- HippocampalCA1Output.ca1_mpfc_relay
- HippocampalCA1Output.swr_active
- MediodorsalThalamicLoop.md_pfc_loop_strength
- MediodorsalThalamicLoop.working_memory_support
- MedialSeptumTheta.theta_active
- MedialSeptumTheta.theta_amplitude
- AttentionTopDownProxy.attention_focus
- WorkingMemoryProxy.maintained_active

OUTPUTS (to brain_runner enrichment)
=====================================
- re_drive (0.0-1.0): nucleus reuniens output
- hpc_pfc_coherence (0.0-1.0): trans-thalamic coupling
- ventral_ca1_drive (0.0-1.0): Re → vCA1 projection
- mpfc_drive (0.0-1.0): Re → mPFC projection
- bla_drive (0.0-1.0): Re → BLA fear-extinction projection
- working_memory_bridge (0.0-1.0): WM-supporting bridge activity
- re_state (str): "wm_bridge" | "fear_discrim" | "consolidation_bridge" | "quiet"

brain_runner enrichment:
    re = all_results.get("NucleusReuniensBridge", {})
    if re:
        enrichments["brain_re_drive"] = re.get("re_drive", 0.2)
        enrichments["brain_hpc_pfc_coherence"] = re.get("hpc_pfc_coherence", 0.0)
        enrichments["brain_re_wm_bridge"] = re.get("working_memory_bridge", 0.0)
        enrichments["brain_re_state"] = re.get("re_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class NucleusReuniensBridge(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="NucleusReuniensBridge",
            human_analog="Nucleus reuniens HPC-mPFC trans-thalamic bridge",
            layer="foundational",
        )
        self.state.setdefault("re_drive", self.BASELINE)
        self.state.setdefault("hpc_pfc_coherence", 0.0)
        self.state.setdefault("ventral_ca1_drive", 0.0)
        self.state.setdefault("mpfc_drive", 0.0)
        self.state.setdefault("bla_drive", 0.0)
        self.state.setdefault("working_memory_bridge", 0.0)
        self.state.setdefault("re_state", "quiet")
        self.state.setdefault("re_burst_mode", "tonic")
        self.state.setdefault("recent_coherence", [])
        self.state.setdefault("tick_count", 0)

    def _re_drive_target(self, ca1: float, md_loop: float, attention: float,
                         theta_active: bool) -> float:
        """Re drive -- driven by CA1 + MD/PFC inputs + attention."""
        target = self.BASELINE + ca1 * 0.3 + md_loop * 0.3 + attention * 0.2
        if theta_active:
            target += 0.10
        return min(1.0, target)

    def _hpc_pfc_coherence(self, re: float, theta_active: bool, theta_amp: float,
                             swr_active: bool = False) -> float:
        """Trans-thalamic HPC-PFC coupling -- Hallock 2016 mechanism.
        SWR during NREM: coherence is maintained even without theta.
        """
        if not theta_active:
            if swr_active:
                return min(1.0, re * 0.6)  # SWR preserves coherence
            return re * 0.3  # weak residual
        return min(1.0, re * 0.5 + theta_amp * 0.5)

    def _ventral_ca1_drive(self, re: float, theta_active: bool) -> float:
        """Re → ventral CA1 projection."""
        if theta_active:
            return min(1.0, re * 0.95)
        return re * 0.6

    def _mpfc_drive(self, re: float, ca1_mpfc: float) -> float:
        """Re → mPFC projection (and mPFC → Re feedback)."""
        return min(1.0, re * 0.7 + ca1_mpfc * 0.3)

    def _bla_drive(self, re: float, valence: float, threat: bool) -> float:
        """Re → BLA fear-extinction projection (Ramanathan 2018)."""
        # Engaged in extinction context (low threat / safe context discrimination)
        return min(1.0, re * 0.4 + valence * 0.3)

    def _wm_bridge(self, re: float, wm: float, coherence: float) -> float:
        """Working memory bridge support -- sustained during WM tasks."""
        if wm < 0.20:
            return 0.0
        return min(1.0, re * 0.5 + coherence * 0.5)

    def _classify_state(self, wm_bridge: float, swr: bool, coherence: float, re: float) -> str:
        if swr and (coherence > 0.30 or wm_bridge > 0.10):
            return "consolidation_bridge"
        if wm_bridge > 0.30:
            return "wm_bridge"
        if coherence > 0.40:
            return "fear_discrim"
        if re < 0.25:
            return "quiet"
        return "quiet"


    def _re_thalamic_burst_mode(self, theta_active: bool, coherence: float) -> str:
        """Re firing mode -- theta-coupled during active processing,
        burst during quiet/immobility states.
        """
        if theta_active and coherence > 0.30:
            return "theta_entrained"
        if coherence < 0.15:
            return "burst_quiet"
        return "tonic"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ca1 = prior.get("HippocampalCA1Output", {})
        ca1_drive = float(ca1.get("ca1_pyramidal_drive", 0.20))
        ca1_mpfc = float(ca1.get("ca1_mpfc_relay", 0.0))
        swr = bool(ca1.get("swr_active", False))

        md = prior.get("MediodorsalThalamicLoop", {})
        md_loop = float(md.get("md_pfc_loop_strength", 0.30))
        wm = float(md.get("working_memory_support", 0.0))

        ms = prior.get("MedialSeptumTheta", {})
        theta_active = bool(ms.get("theta_active", False))
        theta_amp = float(ms.get("theta_amplitude", 0.0))

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        threat = bool(valence.get("threat_signal", False))

        # --- Re drive ---
        re_target = self._re_drive_target(ca1_drive, md_loop, attention, theta_active)
        prev_re = float(self.state.get("re_drive", self.BASELINE))
        new_re = self._smooth(prev_re, re_target)

        # --- Coherence ---
        coh = self._hpc_pfc_coherence(new_re, theta_active, theta_amp, swr)
        prev_coh = float(self.state.get("hpc_pfc_coherence", 0.0))
        new_coh = self._smooth(prev_coh, coh)

        # --- Outputs ---
        vca1 = self._ventral_ca1_drive(new_re, theta_active)
        mpfc = self._mpfc_drive(new_re, ca1_mpfc)
        bla = self._bla_drive(new_re, valence_intensity, threat)
        wm_bridge = self._wm_bridge(new_re, wm, new_coh)

        # --- Burst mode ---
        burst_mode = self._re_thalamic_burst_mode(theta_active, new_coh)

        # --- State ---
        state = self._classify_state(wm_bridge, swr, new_coh, new_re)

        recent = list(self.state.get("recent_coherence", []))
        recent.append(round(new_coh, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["re_drive"] = round(new_re, 4)
        self.state["hpc_pfc_coherence"] = round(new_coh, 4)
        self.state["ventral_ca1_drive"] = round(vca1, 4)
        self.state["mpfc_drive"] = round(mpfc, 4)
        self.state["bla_drive"] = round(bla, 4)
        self.state["working_memory_bridge"] = round(wm_bridge, 4)
        self.state["re_burst_mode"] = burst_mode
        self.state["re_state"] = state
        self.state["recent_coherence"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "re_drive": round(new_re, 4),
            "hpc_pfc_coherence": round(new_coh, 4),
            "ventral_ca1_drive": round(vca1, 4),
            "mpfc_drive": round(mpfc, 4),
            "bla_drive": round(bla, 4),
            "working_memory_bridge": round(wm_bridge, 4),
            "re_state": state,
            "re_burst_mode": burst_mode,
        }
