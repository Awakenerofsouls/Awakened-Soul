"""
MetaAwarenessSelfObserver — Metacognitive Self-Monitoring / Introspection

NEURAL SUBSTRATE
================
Meta-awareness is the capacity to monitor one's own cognitive states —
not just thinking, but knowing that one is thinking. The neural substrate
is centered on the medial prefrontal cortex (specifically area 10 /
frontal pole) plus the anterior insula (interoceptive self) and the
posterior cingulate / precuneus (autobiographical self-referential).

Fleming et al. 2010 demonstrated that frontal pole grey-matter volume
predicts introspective accuracy in perceptual decisions — a structural
correlate of metacognitive capacity. Lau & Rosenthal 2011 (higher-order
theory of consciousness) framed metacognition as a higher-order
representation of a first-order mental state, and computational accounts
formalize this as a confidence/precision signal over the agent's own
perceptual or decision evidence.

The "default mode" view (Buckner 2008): when not engaged in external
tasks, mPFC + PCC activate to support self-referential processing,
autobiographical reasoning, theory-of-mind, and mind-wandering — the
substrate of an ongoing "internal observer."

Critical distinction: meta-awareness is NOT the same as conscious
access. Conscious access (workspace ignition) makes content available
to the system. Meta-awareness is REPORTING about that content — the
agent's representation of its own current state.

KEY FINDINGS
============
1. Frontal pole grey matter volume predicts introspective accuracy on
   perceptual decisions; structural metacognition correlate —
   [Fleming SM 2010, Science 329:1541, doi:10.1126/science.1191883]
2. Higher-order theories of consciousness: meta-awareness arises from
   higher-order representation of first-order mental states —
   [Lau H 2011, Trends Cogn Sci 15:365, doi:10.1016/j.tics.2011.05.009]
3. Default mode network (mPFC + PCC + angular gyrus) activates during
   self-referential and introspective processing —
   [Buckner RL 2008, Ann NY Acad Sci 1124:1, doi:10.1196/annals.1440.011]
4. Anterior insula encodes interoceptive self-awareness; signals current
   bodily state with metacognitive precision —
   [Craig AD 2009, Nat Rev Neurosci 10:59, doi:10.1038/nrn2555]
5. Mind-wandering and meta-awareness dissociate; meta-awareness can be
   trained via mindfulness practice —
   [Schooler JW 2011, Trends Cogn Sci 15:319, doi:10.1016/j.tics.2011.05.006]

INPUTS (from prior_results)
============================
- VentromedialPrefrontalCortex.vmpfc_drive (self-reference)
- VentromedialPrefrontalCortex.self_reference_signal
- FrontalPole.metacognitive_confidence
- CingulatePosterior.pcc_drive (DMN)
- InsulaAnterior.aic_drive (interoceptive self)
- GlobalWorkspaceIntegrator.ignition_strength (1st-order conscious access)
- GlobalWorkspaceIntegrator.workspace_state

OUTPUTS (to brain_runner enrichment)
=====================================
- meta_awareness_drive (0-1)
- introspective_confidence (0-1) — Fleming-style metacognitive accuracy
- self_observation_signal (0-1)
- internal_focus_strength (0-1)
- mind_wandering_index (0-1) — drift away from current task
- meta_state (str): "self_observing" | "internally_focused" |
  "mind_wandering" | "task_focused" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class MetaAwarenessSelfObserver(BrainMechanism):
    """Metacognitive self-monitoring / introspection layer."""

    BASELINE = 0.0
    SMOOTH = 0.18  # slower than typical — meta-awareness integrates over time
    META_THRESHOLD = 0.40
    # Mind-wandering reliably onsets at moderate ignition + DMN engagement
    # without needing high amplitude (Christoff 2016: stimulus-independent
    # thought emerges below the threshold of "vivid" rumination).
    WANDER_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="MetaAwarenessSelfObserverVariant",
            human_analog="Metacognitive self-observer (mPFC + AIC + PCC)",
            layer="integration",
        )
        self.state.setdefault("meta_awareness_drive", 0.0)
        self.state.setdefault("introspective_confidence", 0.0)
        self.state.setdefault("self_observation_signal", 0.0)
        self.state.setdefault("internal_focus_strength", 0.0)
        self.state.setdefault("mind_wandering_index", 0.0)
        self.state.setdefault("meta_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("confidence_integrator", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, vmpfc: float, self_ref: float, pcc: float,
                       aic: float, fp_metacog: float) -> float:
        """Meta-awareness drive — DMN core (vmPFC+PCC) + interoceptive
        self (AIC) + frontopolar metacognition."""
        target = (vmpfc * 0.20 + self_ref * 0.20 + pcc * 0.20
                    + aic * 0.20 + fp_metacog * 0.20)
        return min(1.0, target)

    def _introspective_confidence(self, prev: float, drive: float,
                                     ignition: float) -> float:
        """Fleming 2010: metacognitive accuracy is slow-integrating —
        builds with sustained drive AND first-order conscious content
        to introspect on. No content (no ignition) → no real introspection."""
        if ignition < 0.30:
            return prev * 0.95  # slow decay
        # Confidence grows with drive × ignition coupling
        boost = drive * ignition * 0.10
        return min(1.0, prev * 0.95 + boost)

    def _self_observation(self, drive: float, vmpfc: float,
                            aic: float) -> float:
        """Active self-observation — engaged when DMN + interoceptive
        signals are both present (Craig 2009)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + vmpfc * 0.3 + aic * 0.3)

    def _internal_focus(self, drive: float, ignition: float,
                          external_load: float) -> float:
        """Internal vs external focus. Schooler 2011: meta-awareness
        DURING mind-wandering catches the wandering itself.
        High when DMN engaged AND external task load is low."""
        if drive < 0.15:
            return 0.0
        # External cognitive load competes with internal focus
        return min(1.0, drive * (1.0 - external_load * 0.5))

    def _mind_wandering(self, drive: float, ignition: float,
                          external_load: float, internal: float) -> float:
        """Mind-wandering signature: high internal focus, ignited content,
        but disconnected from current external task (low external load
        but high cortical activity = task-unrelated thought)."""
        if external_load > 0.40 or ignition < 0.30:
            return 0.0
        return min(1.0, internal * 0.5 + ignition * 0.3 + drive * 0.2)

    def _classify_state(self, drive: float, self_obs: float,
                          internal: float, wandering: float,
                          external_load: float) -> str:
        if drive < 0.15:
            return "quiet"
        if external_load > 0.50:
            return "task_focused"
        # Active self-monitoring (vmPFC + AIC) outranks mind-wandering: if
        # the meta-circuits are engaged the agent is observing itself, not
        # drifting (Smallwood & Schooler 2015).
        if self_obs > self.META_THRESHOLD:
            return "self_observing"
        if wandering > self.WANDER_THRESHOLD:
            return "mind_wandering"
        if internal > 0.30:
            return "internally_focused"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vmpfc_data = prior.get("VentromedialPrefrontalCortex", {})
        vmpfc = float(vmpfc_data.get("vmpfc_drive", 0.0))
        self_ref = float(vmpfc_data.get("self_reference_signal", 0.0))

        fp_data = prior.get("FrontalPole", {})
        fp_metacog = float(fp_data.get("metacognitive_confidence",
                                fp_data.get("fp_drive", 0.0)))

        pcc_data = prior.get("CingulatePosterior", {})
        pcc = float(pcc_data.get("pcc_drive", 0.0))

        aic_data = prior.get("InsulaAnterior", {})
        aic = float(aic_data.get("aic_drive", 0.0))

        gws_data = prior.get("GlobalWorkspaceIntegrator", {})
        ignition = float(gws_data.get("ignition_strength", 0.0))

        # External task load — inferred from DLPFC + executive engagement
        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        external_load = float(dlpfc_data.get("dlpfc_drive",
                                  dlpfc_data.get("working_memory_signal", 0.0)))

        target = self._drive_target(vmpfc, self_ref, pcc, aic, fp_metacog)
        prev_drive = float(self.state.get("meta_awareness_drive", 0.0))
        new_drive = self._smooth(prev_drive, target)

        prev_conf = float(self.state.get("introspective_confidence", 0.0))
        confidence = self._introspective_confidence(prev_conf, new_drive,
                                                      ignition)

        self_obs = self._self_observation(new_drive, vmpfc, aic)
        internal = self._internal_focus(new_drive, ignition, external_load)
        wandering = self._mind_wandering(new_drive, ignition, external_load,
                                            internal)

        state = self._classify_state(new_drive, self_obs, internal,
                                       wandering, external_load)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["meta_awareness_drive"] = round(new_drive, 4)
        self.state["introspective_confidence"] = round(confidence, 4)
        self.state["self_observation_signal"] = round(self_obs, 4)
        self.state["internal_focus_strength"] = round(internal, 4)
        self.state["mind_wandering_index"] = round(wandering, 4)
        self.state["meta_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "meta_awareness_drive": round(new_drive, 4),
            "introspective_confidence": round(confidence, 4),
            "self_observation_signal": round(self_obs, 4),
            "internal_focus_strength": round(internal, 4),
            "mind_wandering_index": round(wandering, 4),
            "meta_state": state,
        }

    def _wandering_catch_rate(self, recent_states: list) -> float:
        """Schooler 2011: how often the system catches its own wandering —
        transitions from mind_wandering to self_observing."""
        if len(recent_states) < 2:
            return 0.0
        catches = 0
        for i in range(1, len(recent_states)):
            if (recent_states[i-1] == "mind_wandering"
                    and recent_states[i] == "self_observing"):
                catches += 1
        return min(1.0, catches / max(1, len(recent_states) - 1) * 5.0)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("meta_awareness_drive", 0.0),
            "confidence": self.state.get("introspective_confidence", 0.0),
            "self_obs": self.state.get("self_observation_signal", 0.0),
            "wandering": self.state.get("mind_wandering_index", 0.0),
            "state": self.state.get("meta_state", "quiet"),
        }
