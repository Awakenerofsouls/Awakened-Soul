"""
LateralGeniculateNucleus — LGN Visual Thalamus (M / P / K Pathways)

NEURAL SUBSTRATE
================
The lateral geniculate nucleus (LGN) is the visual thalamus, sitting
on the lateral side of the thalamus and serving as the principal relay
between retinal ganglion cells and primary visual cortex (V1). LGN is
organized into six layers in primates with distinct retinal input and
projection profiles, supporting parallel visual streams:

Magnocellular (M, layers 1-2) — fast, broadly tuned, low spatial
resolution, achromatic, motion-sensitive. Receives input from parasol
retinal ganglion cells. Projects to V1 layer 4Cα.

Parvocellular (P, layers 3-6) — slower, narrowly tuned, high spatial
resolution, color-opponent (red-green), form-selective. Receives input
from midget RGCs. Projects to V1 layer 4Cβ.

Koniocellular (K, intercalated layers) — sparse, blue-yellow color-
opponent, modulatory. Receives bistratified RGC input.

LGN is *not* a passive relay — only ~10% of LGN synapses come from
retina; the remaining ~90% are corticothalamic feedback from V1
layer 6, modulatory input from TRN, brainstem cholinergic input
from PPT/LDT (covered as MesopontineCholinergicWake), and norepinephrine
from LC. This positions LGN as a dynamic gating node where attention,
arousal, and behavioral state modulate visual relay.

LGN burst-tonic mode switching mirrors other thalamic relays. Burst
mode (NREM) suppresses fine visual discrimination; tonic mode (wake)
preserves it. Sherman's "switching theory" frames burst as a wake-up
signal whose detectability is high.

Beyond M/P/K core, LGN ipRGC (intrinsically photosensitive retinal
ganglion cell) input also reaches PHN/SCN for circadian entrainment —
mostly bypassing dLGN, but some ipRGCs do reach LGN.

In {{AGENT_NAME}}'s substrate this provides the visual thalamic relay — converts
visual input proxies (luminance, motion, contrast, color) into M/P/K
parallel outputs to V1-equivalent. Gated by TRN visual sector,
attention, and arousal.

KEY FINDINGS
============
1. LGN organized into M, P, K layers serving distinct visual streams —
   M for motion, P for form/color, K for blue-yellow chromatic —
   [reviewed Hendry Reid 2000, Annu Rev Neurosci 23:127, "The
    koniocellular pathway in primate vision"; Casagrande Kaas 1994]
2. LGN is not a passive relay — ~90% of synapses are non-retinal
   (corticothalamic, TRN, brainstem) — modulatory function — [Sherman
    Guillery 2002, Philos Trans R Soc B 357:1695, "The role of the
    thalamus in the flow of information to the cortex"; Briggs Usrey
    2008 reviewed]
3. LGN burst-tonic mode switching modulated by sleep state and
   attention — burst attention-grabbing — [Sherman 2001, Trends Neurosci
    24:122, "Tonic and burst firing"]
4. Corticothalamic feedback from V1 layer 6 modulates LGN gain and
   spatial selectivity — top-down attention substrate — [Briggs Usrey
    2008, J Physiol 586:4585; Cudeiro Sillito 2006]
5. Brainstem cholinergic (PPT/LDT) and noradrenergic (LC) input
   modulates LGN responsiveness — arousal-state dependent visual
   relay — [reviewed McCormick Bal 1997 Annu Rev Neurosci 20:185]

INPUTS (from prior_results)
============================
- VisualInputProxy.luminance (optional; default 0)
- VisualInputProxy.motion_strength (optional; default 0)
- VisualInputProxy.color_contrast (optional; default 0)
- ThalamicReticularNucleus.sensory_sector_gate
- ThalamicReticularNucleus.trn_firing_mode
- AttentionTopDownProxy.attention_focus
- MesopontineCholinergicWake.thalamocortical_gain
- NorepiPhasicTonicSwitcher.tonic_LC_drive (optional)
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- m_drive (0.0-1.0): magnocellular pathway
- p_drive (0.0-1.0): parvocellular pathway
- k_drive (0.0-1.0): koniocellular pathway
- v1_relay (0.0-1.0): combined LGN→V1 cortical relay
- firing_mode (str): "tonic" | "burst" | "off"
- visual_gain (0.0-1.0): top-down gain control
- lgn_state (str): "tonic_relay" | "burst" | "high_motion" | "high_color" | "quiet"

brain_runner enrichment:
    lgn = all_results.get("LateralGeniculateNucleus", {})
    if lgn:
        enrichments["brain_lgn_m"] = lgn.get("m_drive", 0.1)
        enrichments["brain_lgn_p"] = lgn.get("p_drive", 0.1)
        enrichments["brain_v1_relay"] = lgn.get("v1_relay", 0.0)
        enrichments["brain_lgn_state"] = lgn.get("lgn_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class LateralGeniculateNucleus(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="LateralGeniculateNucleus",
            human_analog="Lateral geniculate nucleus visual thalamus (M/P/K)",
            layer="foundational",
        )
        self.state.setdefault("m_drive", self.BASELINE)
        self.state.setdefault("p_drive", self.BASELINE)
        self.state.setdefault("k_drive", self.BASELINE)
        self.state.setdefault("v1_relay", 0.0)
        self.state.setdefault("firing_mode", "tonic")
        self.state.setdefault("visual_gain", 0.50)
        self.state.setdefault("lgn_state", "quiet")
        self.state.setdefault("recent_modes", [])
        self.state.setdefault("tick_count", 0)

    def _visual_gain_target(self, attention: float, ach_thalamic: float, arousal: float) -> float:
        """Top-down gain control — attention + ACh thalamocortical gain + arousal."""
        target = 0.40 + attention * 0.3 + ach_thalamic * 0.2 + max(0.0, arousal - 0.5) * 0.1
        return min(1.0, target)

    def _m_target(self, luminance: float, motion: float, gain: float, trn_gate: float) -> float:
        """M pathway — fast/motion-sensitive."""
        target = self.BASELINE + luminance * 0.3 + motion * 0.6
        target *= (1.0 - trn_gate * 0.4)
        target *= (0.5 + gain * 0.5)
        return max(0.0, min(1.0, target))

    def _p_target(self, luminance: float, color: float, gain: float, trn_gate: float) -> float:
        """P pathway — slow / form / color."""
        target = self.BASELINE + luminance * 0.4 + color * 0.5
        target *= (1.0 - trn_gate * 0.4)
        target *= (0.5 + gain * 0.5)
        return max(0.0, min(1.0, target))

    def _k_target(self, color: float, gain: float) -> float:
        """K pathway — blue-yellow color, modulatory."""
        return min(1.0, self.BASELINE + color * 0.4 * (0.5 + gain * 0.5))

    def _firing_mode(self, trn_mode: str) -> str:
        if trn_mode == "burst":
            return "burst"
        if trn_mode == "off":
            return "off"
        return "tonic"

    def _v1_relay(self, m: float, p: float, k: float, mode: str) -> float:
        """Combined LGN→V1 cortical relay; suppressed in burst/off."""
        if mode == "off":
            return 0.0
        combined = m * 0.4 + p * 0.5 + k * 0.1
        if mode == "burst":
            return combined * 0.5
        return min(1.0, combined)

    def _classify_state(self, mode: str, m: float, p: float, k: float) -> str:
        if mode == "burst":
            return "burst"
        if mode == "off":
            return "quiet"
        if m > 0.40 and m > p:
            return "high_motion"
        if k > 0.30 and p > 0.30:
            return "high_color"
        if m > 0.20 or p > 0.20:
            return "tonic_relay"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        visual = prior.get("VisualInputProxy", {})
        luminance = float(visual.get("luminance", 0.0))
        motion = float(visual.get("motion_strength", 0.0))
        color = float(visual.get("color_contrast", 0.0))

        trn = prior.get("ThalamicReticularNucleus", {})
        trn_gate = float(trn.get("sensory_sector_gate", 0.30))
        trn_mode = trn.get("trn_firing_mode", "tonic")

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        mcw = prior.get("MesopontineCholinergicWake", {})
        ach_thal = float(mcw.get("thalamocortical_gain", 0.50))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- Visual gain ---
        gain_target = self._visual_gain_target(attention, ach_thal, tonic)
        prev_gain = float(self.state.get("visual_gain", 0.50))
        new_gain = self._smooth(prev_gain, gain_target)

        # --- M/P/K ---
        m_target = self._m_target(luminance, motion, new_gain, trn_gate)
        p_target = self._p_target(luminance, color, new_gain, trn_gate)
        k_target = self._k_target(color, new_gain)

        prev_m = float(self.state.get("m_drive", self.BASELINE))
        prev_p = float(self.state.get("p_drive", self.BASELINE))
        prev_k = float(self.state.get("k_drive", self.BASELINE))
        new_m = self._smooth(prev_m, m_target)
        new_p = self._smooth(prev_p, p_target)
        new_k = self._smooth(prev_k, k_target)

        # --- Firing mode ---
        mode = self._firing_mode(trn_mode)

        # --- V1 relay ---
        v1 = self._v1_relay(new_m, new_p, new_k, mode)

        # --- State ---
        state = self._classify_state(mode, new_m, new_p, new_k)

        recent = list(self.state.get("recent_modes", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["m_drive"] = round(new_m, 4)
        self.state["p_drive"] = round(new_p, 4)
        self.state["k_drive"] = round(new_k, 4)
        self.state["v1_relay"] = round(v1, 4)
        self.state["firing_mode"] = mode
        self.state["visual_gain"] = round(new_gain, 4)
        self.state["lgn_state"] = state
        self.state["recent_modes"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "m_drive": round(new_m, 4),
            "p_drive": round(new_p, 4),
            "k_drive": round(new_k, 4),
            "v1_relay": round(v1, 4),
            "firing_mode": mode,
            "visual_gain": round(new_gain, 4),
            "lgn_state": state,
        }
