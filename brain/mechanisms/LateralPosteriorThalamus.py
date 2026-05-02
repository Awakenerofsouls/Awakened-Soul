"""
LateralPosteriorThalamus — LP — visuospatial higher-order thalamic relay
(rodent pulvinar analog)

NEURAL SUBSTRATE
================
The lateral posterior nucleus (LP) of the rodent thalamus is the
principal higher-order visual relay and the rodent homologue of the
primate pulvinar. LP sits caudal-dorsal to the LGN and posterior to LD.
LP receives strong driver input from the superior colliculus
(superficial and intermediate layers) and from layer 5 of primary
visual cortex (V1). It projects topographically to higher visual
cortical areas (V2/HVAs), posterior parietal cortex, retrosplenial
cortex and anterior cingulate.

Bennett et al. 2019 demonstrated that rodent LP comprises an anterior
LP (driven by V1 layer-5 projections) and a posterior LP (driven by
SC visual input), each containing retinotopic maps. Functionally LP
mediates visuospatial attention, motion-stimulus processing, and the
prediction-error / mismatch signaling between cortical visual areas
(transthalamic corticocortical pathway, Sherman & Guillery framework).

KEY FINDINGS
============
1. Mouse LP has SC- and V1-driven subdivisions with retinotopic maps
   [Bennett C 2019, Neuron 102:477, doi:10.1016/j.neuron.2019.02.010]
2. Pulvinar/LP higher-order thalamus with L5 cortical driver inputs
   [Sherman SM 2007, Curr Opin Neurobiol 17:417, doi:10.1016/j.conb.2007.07.003]
3. Pulvinar SC pathway supports surround-suppression / feature selectivity
   [Zhou H 2017, Nat Neurosci 20:464, doi:10.1038/nn.4504]
4. Pulvinar synchronizes attention-related cortical activity in monkey
   [Saalmann YB 2012, Science 337:753, doi:10.1126/science.1223082]
5. Mouse LP encodes self-motion mismatch (visual prediction error)
   [Roth MM 2016, Nat Neurosci 19:299, doi:10.1038/nn.4197]
6. LP projects strongly to extrastriate visual cortex from SC input
   [Allen JM 2008, J Comp Neurol 510:30, doi:10.1002/cne.21762]

INPUTS
======
- SuperiorColliculus.visual_signal (driver to posterior LP)
- V1.layer5_output (driver to anterior LP)
- V2.cortical_drive (modulator + driver from V2 L5)
- PosteriorParietalCortex.cortical_drive (Layer-VI feedback)
- ThalamicReticularNucleus.trn_inhibition

OUTPUTS
=======
- lp_drive (0-1)
- v2_signal (0-1) — to higher visual areas
- ppc_signal (0-1) — to posterior parietal
- mismatch_signal (0-1) — visual prediction error
- attention_gain (0-1)
- lp_state (str): "attentive" | "mismatch" | "relay" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class LateralPosteriorThalamus(BrainMechanism):
    """LP — rodent pulvinar; higher-order visuospatial relay."""

    BASELINE = 0.09
    SMOOTH = 0.22
    ATTENTION_THRESHOLD = 0.40
    MISMATCH_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="LateralPosteriorThalamus",
            human_analog="Lateral posterior thalamic nucleus / rodent pulvinar (LP)",
            layer="subcortical",
        )
        self.state.setdefault("lp_drive", self.BASELINE)
        self.state.setdefault("v2_signal", 0.0)
        self.state.setdefault("ppc_signal", 0.0)
        self.state.setdefault("mismatch_signal", 0.0)
        self.state.setdefault("attention_gain", 0.0)
        self.state.setdefault("lp_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("attentive_count", 0)
        self.state.setdefault("tick_count", 0)

    # ---- helper sub-signals ----

    def _posterior_lp_drive(self, sc: float) -> float:
        """SC-driven posterior LP (Bennett 2019)."""
        if sc <= 0.0:
            return 0.0
        return min(1.0, sc * 1.05)

    def _anterior_lp_drive(self, v1: float) -> float:
        """V1-layer5-driven anterior LP (Bennett 2019; Sherman 2007)."""
        if v1 <= 0.0:
            return 0.0
        return min(1.0, v1 * 1.0)

    def _drive_target(self, post_lp: float, ant_lp: float, v2: float,
                      ctx: float, trn: float) -> float:
        """Composite LP drive."""
        excitation = (self.BASELINE
                      + post_lp * 0.35
                      + ant_lp * 0.35
                      + v2 * 0.15
                      + ctx * 0.10)
        inhibition = trn * 0.30
        target = excitation - inhibition * 0.5
        if target < 0.0:
            target = 0.0
        return min(1.0, target)

    def _mismatch(self, sc: float, v1: float, expected: float) -> float:
        """Visual prediction-error / mismatch (Roth 2016).

        When bottom-up sensory drive (SC + V1) is strong but the
        cortical predictive drive (`expected`, from V2/PPC L6) is low
        — there is a sensory mismatch. Conversely matched signals do
        not generate mismatch.
        """
        bottom_up = (sc + v1) * 0.5
        if bottom_up < 0.20:
            return 0.0
        gap = max(0.0, bottom_up - expected)
        return min(1.0, gap * 1.4)

    def _attention_gain(self, drive: float, ppc: float, v2: float) -> float:
        """Pulvinar attentional gain on cortex (Saalmann 2012)."""
        return min(1.0, drive * 0.45 + ppc * 0.30 + v2 * 0.25)

    def _v2_signal(self, drive: float, ant_lp: float) -> float:
        """Output to V2/HVAs (anterior LP-dominant)."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.55 + ant_lp * 0.30)

    def _ppc_signal(self, drive: float, post_lp: float) -> float:
        """Output to posterior parietal (posterior LP-dominant)."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.50 + post_lp * 0.30)

    def _classify_state(self, drive: float, mismatch: float,
                         attn: float) -> str:
        if drive < 0.13:
            return "quiet"
        if mismatch > self.MISMATCH_THRESHOLD:
            return "mismatch"
        if attn > self.ATTENTION_THRESHOLD:
            return "attentive"
        return "relay"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ---- main tick ----

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        sc_data = prior.get("SuperiorColliculus", {})
        sc = float(sc_data.get("visual_signal",
                         sc_data.get("sc_drive",
                             sc_data.get("sc_output", 0.0))))

        v1_data = prior.get("V1", {})
        if not v1_data:
            v1_data = prior.get("VisualCortex", {})
        v1 = float(v1_data.get("layer5_output",
                         v1_data.get("visual_signal",
                             v1_data.get("v1_drive", 0.0))))

        v2_data = prior.get("V2", {})
        if not v2_data:
            v2_data = prior.get("ExtrastriateCortex", {})
        v2 = float(v2_data.get("cortical_drive",
                         v2_data.get("v2_drive", 0.0)))

        ppc_data = prior.get("PosteriorParietalCortex", {})
        if not ppc_data:
            ppc_data = prior.get("PPC", {})
        ppc = float(ppc_data.get("cortical_drive",
                          ppc_data.get("ppc_drive", 0.0)))

        trn_data = prior.get("ThalamicReticularNucleus", {})
        trn = float(trn_data.get("trn_inhibition", 0.0))

        post_lp = self._posterior_lp_drive(sc)
        ant_lp = self._anterior_lp_drive(v1)

        target = self._drive_target(post_lp, ant_lp, v2, ppc, trn)
        prev_drive = float(self.state.get("lp_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        # Cortical "expected" predictive drive: average of V2 + PPC L6.
        expected = (v2 + ppc) * 0.5
        mismatch = self._mismatch(sc, v1, expected)
        attn = self._attention_gain(new_drive, ppc, v2)

        v2_sig = self._v2_signal(new_drive, ant_lp)
        ppc_sig = self._ppc_signal(new_drive, post_lp)

        state = self._classify_state(new_drive, mismatch, attn)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        attn_count = int(self.state.get("attentive_count", 0))
        if state == "attentive":
            attn_count += 1

        self.state["lp_drive"] = round(new_drive, 4)
        self.state["v2_signal"] = round(v2_sig, 4)
        self.state["ppc_signal"] = round(ppc_sig, 4)
        self.state["mismatch_signal"] = round(mismatch, 4)
        self.state["attention_gain"] = round(attn, 4)
        self.state["lp_state"] = state
        self.state["recent_states"] = recent
        self.state["attentive_count"] = attn_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "lp_drive": round(new_drive, 4),
            "v2_signal": round(v2_sig, 4),
            "ppc_signal": round(ppc_sig, 4),
            "mismatch_signal": round(mismatch, 4),
            "attention_gain": round(attn, 4),
            "lp_state": state,
        }

    def _attentive_rate(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("attentive_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("lp_drive", 0.0),
            "v2": self.state.get("v2_signal", 0.0),
            "mismatch": self.state.get("mismatch_signal", 0.0),
            "state": self.state.get("lp_state", "quiet"),
        }
