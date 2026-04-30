"""
MediodorsalThalamicLoop — MD-PFC Loop, Working Memory, Cognitive Flexibility

NEURAL SUBSTRATE
================
The mediodorsal thalamus (MD) is a higher-order thalamic nucleus that
sits in the medial dorsal thalamus and is heavily reciprocally connected
with prefrontal cortex (PFC). MD has three principal subdivisions —
medial (magnocellular, MDmc), central (parvocellular, MDpc), and
lateral (densocellular, MDdc) — with distinct cortical and subcortical
connections. MD receives input from BLA (limbic), CeA, ventral pallidum,
substantia nigra reticulata (SNr), GPi (basal ganglia output), and
brainstem reticular nuclei, and reciprocates with mPFC, anterior
cingulate, and orbitofrontal cortex.

Unlike "first-order" relay thalamic nuclei (LGN, MGN, VPL, VL), which
relay sensory or motor signals to cortex, MD is a "higher-order"
thalamic nucleus that integrates cortical signals, transforms them
through trans-thalamic loops, and returns them to cortex. MD-PFC loops
support working memory maintenance — Bolkan et al. (2017, Nat Neurosci)
showed that optogenetic inhibition of MD-mPFC inputs disrupts working
memory; sustained MD activity is required for persistent PFC firing
during delay periods.

MD also enables cognitive flexibility — Schmitt et al. (2017, Nature)
showed that MD activity is required for rule switching in PFC. MD
gain control over PFC ensembles allows flexible reorganization of
cortical responses according to task demands. MD lesions produce
deficits in cognitive flexibility and working memory in humans
(thalamic stroke patients).

Limbic-MD subdivisions integrate amygdala/ventral striatum signals
with PFC cognitive processing, and may contribute to motivational
gating of cognitive control.

In {{AGENT_NAME}}'s substrate this provides the higher-order thalamic / cognitive
gain channel — supports working-memory-like maintenance of recent state
and supplies a slow context signal that PFC-equivalent integration
mechanisms can read.

KEY FINDINGS
============
1. MD-mPFC inputs maintain working memory — optogenetic inhibition
   during delay disrupts task performance — [Bolkan et al. 2017, Nat
    Neurosci 20:987-996, "Thalamic projections sustain prefrontal
    activity during working memory maintenance"]
2. MD enables cognitive flexibility — required for rule switching
   in PFC — [Schmitt et al. 2017, Nature 545:219-223, "Thalamic
    amplification of cortical connectivity sustains attentional
    control"]
3. MD is a higher-order thalamic nucleus integrating BLA, CeA, BG
   output, and brainstem signals; reciprocally connected with mPFC
   — [reviewed Pergola et al. 2018 Trends Neurosci 41:230;
    Mitchell Chakraborty 2013 Front Sys Neurosci]
4. MD lesions produce working memory and cognitive flexibility deficits
   in humans (thalamic stroke) — [Van der Werf et al. 2003 Cortex
    39:1047; reviewed Mitchell 2015 Brain Cogn]
5. Limbic-MD subdivisions integrate amygdala/ventral striatum signals
   with PFC; mediate motivational gating of cognitive control —
   [reviewed Saleem et al. 2014 J Comp Neurol 522:1641; Parnaudeau
    Bolkan Kellendonk 2018 Trends Neurosci 41:230]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- BasolateralAmygdala.bla_excitatory_drive
- CentralAmygdala.cem_output_drive
- GlobusPallidusOutput.gpi_output
- ThalamicReticularNucleus.attention_gating_strength
- VentralTegmentalDopamine.mpfc_da_drive
- WorkingMemoryProxy.maintained_active (optional; default False)
- AttentionTopDownProxy.attention_focus (optional; default 0.5)

OUTPUTS (to brain_runner enrichment)
=====================================
- md_drive (0.0-1.0): MD overall thalamic output
- md_pfc_loop_strength (0.0-1.0): MD↔PFC reverberant gain
- working_memory_support (0.0-1.0): persistent activity proxy
- cognitive_flexibility_index (0.0-1.0): readiness for rule switching
- limbic_md_drive (0.0-1.0): limbic subdivision output
- md_state (str): "quiet" | "wm_active" | "flexibility_engaged" | "limbic_gating"

brain_runner enrichment:
    md = all_results.get("MediodorsalThalamicLoop", {})
    if md:
        enrichments["brain_md_drive"] = md.get("md_drive", 0.3)
        enrichments["brain_md_pfc_loop"] = md.get("md_pfc_loop_strength", 0.3)
        enrichments["brain_working_memory"] = md.get("working_memory_support", 0.0)
        enrichments["brain_md_state"] = md.get("md_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class MediodorsalThalamicLoop(BrainMechanism):
    BASELINE_DRIVE = 0.30
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="MediodorsalThalamicLoop",
            human_analog="Mediodorsal thalamus higher-order PFC loop",
            layer="foundational",
        )
        self.state.setdefault("md_drive", self.BASELINE_DRIVE)
        self.state.setdefault("md_pfc_loop_strength", 0.30)
        self.state.setdefault("working_memory_support", 0.0)
        self.state.setdefault("cognitive_flexibility_index", 0.30)
        self.state.setdefault("limbic_md_drive", 0.20)
        self.state.setdefault("md_state", "quiet")
        self.state.setdefault("recent_loop", [])
        self.state.setdefault("tick_count", 0)

    def _md_drive_target(self, arousal: float, gpi: float, attention: float) -> float:
        """MD overall drive — gated by GPi (high GPi = thalamic suppression).
        Note: Inverse of GPi suppression; high GPi means more inhibition.
        """
        target = self.BASELINE_DRIVE + max(0.0, arousal - 0.5) * 0.3
        target -= max(0.0, gpi - 0.5) * 0.4  # GPi tonic suppression
        target += attention * 0.3
        return max(0.0, min(1.0, target))

    def _md_pfc_loop(self, md: float, mpfc_da: float, attention: float) -> float:
        """MD↔PFC reverberant loop strength.
        Sustained loop activity = working memory.
        """
        target = md * 0.5 + mpfc_da * 0.3 + attention * 0.2
        return max(0.0, min(1.0, target))

    def _working_memory_support(self, prev_loop: float, loop: float,
                                  wm_active: bool, attention: float) -> float:
        """Working memory support — accumulates with sustained loop."""
        if wm_active and loop > 0.40:
            target = max(prev_loop, loop) * 0.7 + attention * 0.3
        else:
            # Slow decay
            target = prev_loop * 0.85
        return max(0.0, min(1.0, target))

    def _cognitive_flexibility(self, md: float, attention: float, arousal: float) -> float:
        """Readiness for rule switching — Schmitt 2017."""
        target = 0.20 + md * 0.3 + attention * 0.3 + max(0.0, arousal - 0.5) * 0.2
        return max(0.0, min(1.0, target))

    def _limbic_md_drive(self, bla: float, cea: float, attention: float) -> float:
        """Limbic-MD subdivision output."""
        return min(1.0, bla * 0.4 + cea * 0.3 + attention * 0.2)

    def _classify_state(self, wm: float, flex: float, limbic: float, md: float) -> str:
        if wm > 0.50:
            return "wm_active"
        if limbic > 0.45:
            return "limbic_gating"
        if flex > 0.55:
            return "flexibility_engaged"
        if md < 0.20:
            return "quiet"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        bla = prior.get("BasolateralAmygdala", {})
        bla_drive = float(bla.get("bla_excitatory_drive", 0.0))

        cea = prior.get("CentralAmygdala", {})
        cea_out = float(cea.get("cem_output_drive", 0.0))

        gp = prior.get("GlobusPallidusOutput", {})
        gpi = float(gp.get("gpi_output", 0.50))

        trn = prior.get("ThalamicReticularNucleus", {})
        trn_att = float(trn.get("attention_gating_strength", 0.40))

        vta = prior.get("VentralTegmentalDopamine", {})
        mpfc_da = float(vta.get("mpfc_da_drive", 0.30))

        wm_proxy = prior.get("WorkingMemoryProxy", {})
        wm_active = bool(wm_proxy.get("maintained_active", False))

        att_proxy = prior.get("AttentionTopDownProxy", {})
        attention_focus = float(att_proxy.get("attention_focus", 0.5))

        # --- MD overall drive ---
        md_target = self._md_drive_target(tonic, gpi, attention_focus)
        prev_md = float(self.state.get("md_drive", self.BASELINE_DRIVE))
        new_md = self._smooth(prev_md, md_target)

        # --- MD-PFC loop ---
        loop_target = self._md_pfc_loop(new_md, mpfc_da, attention_focus)
        prev_loop = float(self.state.get("md_pfc_loop_strength", 0.30))
        new_loop = self._smooth(prev_loop, loop_target)

        # --- Working memory support ---
        prev_wm = float(self.state.get("working_memory_support", 0.0))
        new_wm = self._working_memory_support(prev_wm, new_loop, wm_active, attention_focus)

        # --- Cognitive flexibility ---
        flex = self._cognitive_flexibility(new_md, attention_focus, tonic)
        prev_flex = float(self.state.get("cognitive_flexibility_index", 0.30))
        new_flex = self._smooth(prev_flex, flex)

        # --- Limbic-MD ---
        limbic = self._limbic_md_drive(bla_drive, cea_out, attention_focus)
        prev_limbic = float(self.state.get("limbic_md_drive", 0.20))
        new_limbic = self._smooth(prev_limbic, limbic)

        # --- State ---
        state = self._classify_state(new_wm, new_flex, new_limbic, new_md)

        recent = list(self.state.get("recent_loop", []))
        recent.append(round(new_loop, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["md_drive"] = round(new_md, 4)
        self.state["md_pfc_loop_strength"] = round(new_loop, 4)
        self.state["working_memory_support"] = round(new_wm, 4)
        self.state["cognitive_flexibility_index"] = round(new_flex, 4)
        self.state["limbic_md_drive"] = round(new_limbic, 4)
        self.state["working_memory_active"] = (new_wm > 0.5)
        self.state["md_state"] = state
        self.state["working_memory_active"] = (new_wm > 0.5)
        self.state["loop_strength_ema"] = round(new_loop * 0.2 + float(self.state.get("loop_strength_ema", new_loop)) * 0.8, 4)
        self.state["md_drive_ema"] = round(new_md * 0.2 + float(self.state.get("md_drive_ema", new_md)) * 0.8, 4)
        self.state["recent_loop"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "md_drive": round(new_md, 4),
            "md_pfc_loop_strength": round(new_loop, 4),
            "working_memory_support": round(new_wm, 4),
            "cognitive_flexibility_index": round(new_flex, 4),
            "limbic_md_drive": round(new_limbic, 4),
            "md_state": state,
            "md_working_memory_active": (new_wm > 0.5),
            "loop_strength_ema": round(new_loop * 0.2 + float(self.state.get("loop_strength_ema", new_loop)) * 0.8, 4),
        }
