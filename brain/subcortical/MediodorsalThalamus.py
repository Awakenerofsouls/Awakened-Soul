"""
MediodorsalThalamus — MD — prefrontal/limbic working-memory hub

NEURAL SUBSTRATE
================
The mediodorsal thalamus (MD) is the principal "limbic-association"
thalamic nucleus and the canonical thalamic partner of medial PFC. MD
has three subdivisions in rodents: medial (parvocellular, mPFC-projecting),
lateral (multiform, OFC/cingulate-projecting), and central. MD shares
reciprocal corticothalamic connectivity with mPFC and OFC, and receives
input from basolateral amygdala (BLA), ventral pallidum, and substantia
nigra pars reticulata. Its primary outputs target prefrontal cortex
layers 1 and 3 — the canonical apical-tuft loop that supports persistent
delay activity.

Bolkan et al. 2017 demonstrated, with pathway-specific optogenetic
inhibition, that MD-to-mPFC projections are necessary for working memory
maintenance during delays, and mPFC-to-MD projections are necessary for
subsequent choice. Schmitt et al. 2017 showed that MD does not relay
categorical information but rather amplifies cortico-cortical
connectivity to sustain rule representations during attentional control.

KEY FINDINGS
============
1. MD-mPFC pathway sustains prefrontal activity during WM delays
   [Bolkan SS 2017, Nat Neurosci 20:987, doi:10.1038/nn.4568]
2. MD amplifies cortical connectivity to sustain rule-based attention
   [Schmitt LI 2017, Nature 545:219, doi:10.1038/nature22073]
3. MD lesions impair flexible decision-making / working memory
   [Parnaudeau S 2013, Neuron 77:1151, doi:10.1016/j.neuron.2013.01.038]
4. MD encodes adaptive behavioral choice via prefrontal feedback
   [Mitchell AS 2014, Trends Neurosci 37:264, doi:10.1016/j.tins.2014.03.008]
5. MD receives strong BLA input shaping value-laden decisions
   [Krettek JE 1977, J Comp Neurol 171:157, doi:10.1002/cne.901710204]
6. MD central role in cognitive flexibility / cognitive control
   [Halassa MM 2018, Trends Cogn Sci 22:951, doi:10.1016/j.tics.2018.08.011]

INPUTS
======
- BasalAmygdala / BasolateralAmygdala.amyg_drive
- VentralPallidum.vp_output (limbic basal-ganglia)
- SubstantiaNigraReticulata.snr_output (GABAergic)
- PrelimbicCortex / mPFC.cortical_drive (Layer-VI feedback)
- ThalamicReticularNucleus.trn_inhibition

OUTPUTS
=======
- md_drive (0-1)
- pfc_layer1_signal (0-1)
- working_memory_signal (0-1) — persistent delay activity
- rule_amplification_signal (0-1)
- flexibility_signal (0-1)
- md_state (str): "wm_maintain" | "rule_amplify" | "relay" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class MediodorsalThalamus(BrainMechanism):
    """MD — prefrontal/limbic working-memory thalamic hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    WM_THRESHOLD = 0.40
    RULE_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="MediodorsalThalamus",
            human_analog="Mediodorsal thalamic nucleus (MD)",
            layer="subcortical",
        )
        self.state.setdefault("md_drive", self.BASELINE)
        self.state.setdefault("pfc_layer1_signal", 0.0)
        self.state.setdefault("working_memory_signal", 0.0)
        self.state.setdefault("rule_amplification_signal", 0.0)
        self.state.setdefault("flexibility_signal", 0.0)
        self.state.setdefault("md_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("wm_count", 0)
        self.state.setdefault("tick_count", 0)
        # Persistent activity proxy — slow integrator of MD drive
        self.state.setdefault("delay_integrator", 0.0)

    # ---- helper sub-signals ----

    def _bg_inhibition(self, vp: float, snr: float) -> float:
        """Limbic basal-ganglia inhibition on MD."""
        return min(1.0, 0.6 * max(vp, snr) + 0.4 * (vp + snr) * 0.5)

    def _amygdala_drive(self, amyg: float) -> float:
        """BLA input — value-laden / affective drive (Krettek 1977)."""
        return min(1.0, amyg * 0.95)

    def _drive_target(self, amyg: float, ctx: float, bg: float,
                      trn: float) -> float:
        """Composite MD drive."""
        excitation = (self.BASELINE
                      + amyg * 0.35
                      + ctx * 0.40)
        inhibition = bg * 0.40 + trn * 0.30
        target = excitation - inhibition * 0.5
        if target < 0.0:
            target = 0.0
        return min(1.0, target)

    def _working_memory(self, drive: float, ctx: float,
                         integrator: float) -> float:
        """MD-mPFC delay-period maintenance signal (Bolkan 2017).

        Working memory requires sustained MD↔mPFC reciprocal activity.
        We model this as a function of drive multiplied by cortical
        feedback, with an integrator that tracks recent activity.
        """
        if drive < 0.18 or ctx < 0.15:
            return 0.0
        return min(1.0, drive * ctx * 1.6 + integrator * 0.2)

    def _rule_amplification(self, drive: float, ctx: float) -> float:
        """Schmitt 2017 — MD amplifies cortico-cortical connectivity.

        Amplification is multiplicative on cortical drive — MD does not
        carry categorical info but boosts cortical signal-to-noise.
        """
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * (0.6 + ctx * 0.6))

    def _flexibility(self, drive: float, amyg: float, bg: float) -> float:
        """Cognitive flexibility composite (Halassa 2018)."""
        # Flexibility requires drive + value (BLA) input with low BG gating
        return min(1.0, drive * 0.4 + amyg * 0.3 + (1.0 - bg) * 0.3 - 0.15)

    def _pfc_layer1(self, drive: float, rule: float, wm: float) -> float:
        """MD axons projecting to PFC layer 1 apical tufts."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.45 + rule * 0.30 + wm * 0.25)

    def _classify_state(self, drive: float, wm: float, rule: float) -> str:
        if drive < 0.14:
            return "quiet"
        if wm > self.WM_THRESHOLD:
            return "wm_maintain"
        if rule > self.RULE_THRESHOLD:
            return "rule_amplify"
        return "relay"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ---- main tick ----

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        amyg_data = prior.get("BasalAmygdala", {})
        if not amyg_data:
            amyg_data = prior.get("BasolateralAmygdala", {})
        if not amyg_data:
            amyg_data = prior.get("LateralAmygdala", {})
        amyg = float(amyg_data.get("amyg_drive",
                            amyg_data.get("bla_drive",
                                amyg_data.get("output", 0.0))))

        vp_data = prior.get("VentralPallidum", {})
        if not vp_data:
            vp_data = prior.get("VentralPallidumReward", {})
        vp = float(vp_data.get("vp_output",
                         vp_data.get("vp_drive", 0.0)))

        snr_data = prior.get("SubstantiaNigraReticulata", {})
        snr = float(snr_data.get("snr_output", 0.0))

        ctx_data = prior.get("PrelimbicCortex", {})
        if not ctx_data:
            ctx_data = prior.get("mPFC", {})
        if not ctx_data:
            ctx_data = prior.get("InfralimbicCortex", {})
        ctx = float(ctx_data.get("cortical_drive",
                         ctx_data.get("pfc_drive",
                             ctx_data.get("prelimbic_drive", 0.0))))

        trn_data = prior.get("ThalamicReticularNucleus", {})
        trn = float(trn_data.get("trn_inhibition", 0.0))

        amyg_eff = self._amygdala_drive(amyg)
        bg = self._bg_inhibition(vp, snr)
        target = self._drive_target(amyg_eff, ctx, bg, trn)
        prev_drive = float(self.state.get("md_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        # Slow delay-period integrator (decays + accumulates)
        prev_integ = float(self.state.get("delay_integrator", 0.0))
        new_integ = max(0.0, prev_integ * 0.85 + new_drive * 0.20)
        new_integ = min(1.0, new_integ)

        wm = self._working_memory(new_drive, ctx, new_integ)
        rule = self._rule_amplification(new_drive, ctx)
        flex = self._flexibility(new_drive, amyg_eff, bg)
        pfc_l1 = self._pfc_layer1(new_drive, rule, wm)

        state = self._classify_state(new_drive, wm, rule)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        wm_count = int(self.state.get("wm_count", 0))
        if state == "wm_maintain":
            wm_count += 1

        self.state["md_drive"] = round(new_drive, 4)
        self.state["pfc_layer1_signal"] = round(pfc_l1, 4)
        self.state["working_memory_signal"] = round(wm, 4)
        self.state["rule_amplification_signal"] = round(rule, 4)
        self.state["flexibility_signal"] = round(flex, 4)
        self.state["md_state"] = state
        self.state["recent_states"] = recent
        self.state["wm_count"] = wm_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["delay_integrator"] = round(new_integ, 4)
        self.persist_state()

        return {
            "md_drive": round(new_drive, 4),
            "pfc_layer1_signal": round(pfc_l1, 4),
            "working_memory_signal": round(wm, 4),
            "rule_amplification_signal": round(rule, 4),
            "flexibility_signal": round(flex, 4),
            "md_state": state,
        }

    def _wm_engagement(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("wm_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("md_drive", 0.0),
            "wm": self.state.get("working_memory_signal", 0.0),
            "rule": self.state.get("rule_amplification_signal", 0.0),
            "state": self.state.get("md_state", "quiet"),
        }
