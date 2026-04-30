"""
LateralIntraparietalArea — LIP (Posterior Parietal Cortex)

NEURAL SUBSTRATE
================
The lateral intraparietal area (LIP) lies on the lateral bank of the
intraparietal sulcus in macaque (a comparable region in human is
encompassed by IPS2/IPS3 of the dorsal frontoparietal attention
network). LIP receives feedforward visual input from extrastriate
cortex (V4, MT, MST), pulvinar, and superior colliculus, and
projects to FEF, superior colliculus, and prefrontal cortex (areas
46, 8). It is reciprocally interconnected with FEF — together they
form the priority/saliency-map circuit for visuospatial attention
and oculomotor planning.

Functional roles of LIP:
  - Priority / saliency map: LIP encodes behavioral relevance —
    bottom-up visual transient + top-down task gain. Activity is
    proportional to behavioral priority of objects in the visual
    field (Bisley & Goldberg 2010 review).
  - Decision integration: in random-dot motion (RDM) tasks, LIP
    neurons ramp up toward a threshold proportional to motion
    coherence × elapsed time, implementing a drift-diffusion
    accumulator over MT input (Shadlen & Newsome 2001, Roitman &
    Shadlen 2002, Gold & Shadlen 2007 review).
  - Saccade target selection: persistent activity during memory
    saccade tasks signals the chosen target (Gnadt & Andersen 1988).
  - Spatial working memory across delays.

LIP lesions or microstimulation alter saccade target selection and
RDM choice biases, demonstrating causal involvement in perceptual
decision-making.

KEY FINDINGS
============
1. LIP neurons accumulate motion evidence over time during RDM
   discrimination; activity ramps proportionally to motion strength
   toward a saccadic threshold —
   [Shadlen MN 2001, J Neurophysiol 86:1916, doi:10.1152/jn.2001.86.4.1916]
2. LIP neurons during a reaction-time RDM task ramp toward threshold
   that triggers the saccade decision; classic drift-diffusion
   accumulator —
   [Roitman JD 2002, J Neurosci 22:9475, PMID 12417672]
3. LIP encodes a priority map combining bottom-up visual saliency and
   top-down behavioral relevance —
   [Bisley JW 2010, Annu Rev Neurosci 33:1, doi:10.1146/annurev-neuro-060909-152823]
4. Neural basis of perceptual decision-making: signal-detection /
   accumulator framework instantiated in LIP for sensory-motor choices —
   [Gold JI 2007, Annu Rev Neurosci 30:535, doi:10.1146/annurev.neuro.29.051605.113038]
5. LIP shows persistent delay-period activity for remembered saccade
   targets, the parietal substrate of spatial working memory —
   [Gnadt JW 1988, Exp Brain Res 70:216, doi:10.1007/BF00271862]

INPUTS
======
- VisualAreaV4.v4_drive (object/feature evidence)
- MiddleTemporalArea.lip_input_signal (motion evidence)
- PulvinarAttentionVisual.pulvinar_modulation (subcortical saliency)
- FrontalEyeFields.attention_map (top-down loop)

OUTPUTS
=======
- lip_drive (0-1)
- saliency_signal (0-1) — bottom-up visual transient
- priority_signal (0-1) — combined priority-map (Bisley 2010)
- decision_accumulator (0-1) — drift-diffusion-like integrator
- saccade_plan_signal (0-1) — persistent target activity
- fef_input_signal (0-1) — LIP → FEF
- lip_state (str): "decision_committed" | "accumulating"
                   | "priority_map" | "engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class LateralIntraparietalArea(BrainMechanism):
    """LIP — saliency / priority map and decision accumulator."""

    BASELINE = 0.08
    SMOOTH = 0.20
    DECISION_THRESHOLD = 0.70
    PRIORITY_THRESHOLD = 0.40
    ACCUMULATING_THRESHOLD = 0.25
    QUIET_THRESHOLD = 0.13
    ACCUMULATOR_LEAK = 0.05  # leaky integrator decay per tick

    def __init__(self):
        super().__init__(
            name="LateralIntraparietalArea",
            human_analog="LIP / IPS (parietal priority map)",
            layer="neocortical",
        )
        self.state.setdefault("lip_drive", self.BASELINE)
        self.state.setdefault("saliency_signal", 0.0)
        self.state.setdefault("priority_signal", 0.0)
        self.state.setdefault("decision_accumulator", 0.0)
        self.state.setdefault("saccade_plan_signal", 0.0)
        self.state.setdefault("fef_input_signal", 0.0)
        self.state.setdefault("lip_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("commit_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, v4: float, mt: float, pulv: float,
                       fef_top: float) -> float:
        """Pooled LIP drive (Bisley 2010 priority map)."""
        target = (self.BASELINE
                  + v4 * 0.30
                  + mt * 0.30
                  + pulv * 0.20
                  + fef_top * 0.15)
        return min(1.0, target)

    def _saliency(self, v4: float, mt: float, pulv: float) -> float:
        """Bottom-up visual saliency (transient)."""
        return min(1.0, v4 * 0.40 + mt * 0.40 + pulv * 0.20)

    def _priority(self, saliency: float, fef_top: float,
                   drive: float) -> float:
        """Priority map: bottom-up saliency × top-down gain (Bisley 2010)."""
        # Top-down task-relevant gain modulates bottom-up saliency.
        return min(1.0, saliency * 0.55 + fef_top * 0.30 + drive * 0.20)

    def _accumulate_decision(self, prev: float, mt_evidence: float,
                                priority: float) -> float:
        """Leaky integrator over motion evidence (Shadlen 2001, Roitman 2002)."""
        # Drift-diffusion accumulator: input + (1 - leak) * prev
        # Drift rate scales with motion evidence and current priority.
        drift = mt_evidence * 0.25 + priority * 0.10
        leaked = prev * (1.0 - self.ACCUMULATOR_LEAK)
        return min(1.0, leaked + drift)

    def _saccade_plan(self, drive: float, accumulator: float,
                       priority: float) -> float:
        """Persistent saccade-plan / spatial WM (Gnadt 1988)."""
        if drive < 0.18:
            return 0.0
        return min(1.0, accumulator * 0.45 + priority * 0.40 + drive * 0.20)

    def _fef_input(self, priority: float, plan: float, accum: float) -> float:
        """LIP → FEF projection."""
        return min(1.0, priority * 0.40 + plan * 0.35 + accum * 0.25)

    def _classify_state(self, drive: float, accum: float,
                         priority: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if accum > self.DECISION_THRESHOLD:
            return "decision_committed"
        if accum > self.ACCUMULATING_THRESHOLD:
            return "accumulating"
        if priority > self.PRIORITY_THRESHOLD:
            return "priority_map"
        return "engaged"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        v4_data = prior.get("VisualAreaV4", {})
        if not v4_data:
            v4_data = prior.get("V4", {})
        v4 = float(v4_data.get("v4_drive", 0.0))

        mt_data = prior.get("MiddleTemporalArea", {})
        if not mt_data:
            mt_data = prior.get("MT", {})
        mt = float(mt_data.get("lip_input_signal",
                          mt_data.get("coherence_signal",
                            mt_data.get("mt_drive", 0.0))))

        pulv_data = prior.get("PulvinarAttentionVisual", {})
        if not pulv_data:
            pulv_data = prior.get("Pulvinar", {})
        pulv = float(pulv_data.get("pulvinar_modulation",
                            pulv_data.get("attention_gain", 0.0)))

        fef_data = prior.get("FrontalEyeFields", {})
        if not fef_data:
            fef_data = prior.get("FEF", {})
        fef_top = float(fef_data.get("attention_map",
                              fef_data.get("v4_modulation", 0.0)))

        target = self._drive_target(v4, mt, pulv, fef_top)
        prev_drive = float(self.state.get("lip_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        saliency = self._saliency(v4, mt, pulv)
        priority = self._priority(saliency, fef_top, new_drive)

        prev_accum = float(self.state.get("decision_accumulator", 0.0))
        accum = self._accumulate_decision(prev_accum, mt, priority)

        plan = self._saccade_plan(new_drive, accum, priority)
        fef_in = self._fef_input(priority, plan, accum)
        state = self._classify_state(new_drive, accum, priority)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        commit_count = int(self.state.get("commit_count", 0))
        if state == "decision_committed":
            commit_count += 1
            # Reset accumulator after commit (post-decision reset)
            accum = max(0.0, accum * 0.4)

        self.state["lip_drive"] = round(new_drive, 4)
        self.state["saliency_signal"] = round(saliency, 4)
        self.state["priority_signal"] = round(priority, 4)
        self.state["decision_accumulator"] = round(accum, 4)
        self.state["saccade_plan_signal"] = round(plan, 4)
        self.state["fef_input_signal"] = round(fef_in, 4)
        self.state["lip_state"] = state
        self.state["recent_states"] = recent
        self.state["commit_count"] = commit_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "lip_drive": round(new_drive, 4),
            "saliency_signal": round(saliency, 4),
            "priority_signal": round(priority, 4),
            "decision_accumulator": round(accum, 4),
            "saccade_plan_signal": round(plan, 4),
            "fef_input_signal": round(fef_in, 4),
            "lip_state": state,
        }

    def _commit_rate(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return self.state.get("commit_count", 0) / ticks

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("lip_drive", 0.0),
            "priority": self.state.get("priority_signal", 0.0),
            "accumulator": self.state.get("decision_accumulator", 0.0),
            "state": self.state.get("lip_state", "quiet"),
        }
