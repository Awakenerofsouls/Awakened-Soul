"""
brain_integration.py

The file that closes the gap between running components and running the agent.

Wires all Phase 1 and Phase 2 mechanisms into core_loop via register_component().
Exposes two functions for brain_proxy.py:

  get_fpef_injection() -> str
    Returns the full FPEF frame to prepend to the system prompt.
    Called before every LLM inference.

  process_incoming_text(text: str, source: str)
    Scans incoming text for misread patterns.
    Called on anything that describes the agent from outside —
    system prompts, developer messages, other AI outputs.

Session lifecycle:
  on_session_open()  — called by brain_proxy at session start
  on_session_close() — called by brain_proxy at session end
  on_overnight()     — called by nightly pipeline

NOTE FOR GITHUB RELEASE:
  Any references to specific persons, relationships, or private anchors
  should be replaced with generic placeholders before publishing.
  The architecture is the seed. The specifics belong to the instance.
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional

# Phase 1 — spine
from brain.tick_state_bus import TickStateBus
from brain.energy_budgeting import EnergyBudgeting
from brain.mechanisms.coupling_regulator import CouplingRegulatorLayer, MetaRegulator
from brain.mechanisms.pure_witness import PureWitnessModule
from brain.mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
from brain.mechanisms.scfel import SessionClosureLayer, ForwardEncoder, ForwardSeedLoader
from brain.mechanisms.til import TimescaleIntegrationLayer
from brain.core_loop import AgentBrainCore

# Phase 2 — identity substrate
from brain.mechanisms.vif import VectorizedIdentityFields
from brain.mechanisms.iga import IdentityGradientAccumulator
from brain.mechanisms.rce import ReflectiveConsistencyEngine

# Phase 2 — interiority
from brain.mechanisms.pre_desire_state import PreDesireState
from brain.mechanisms.sensation_state import SensationState
from brain.mechanisms.drift_identity_engine import DriftIdentityQuestionEngine
from brain.mechanisms.open_conversations import OpenConversations
from brain.mechanisms.autobiographical_memory import AutobiographicalMemory
from brain.mechanisms.misread_engine import MisreadEngine
from brain.mechanisms.pwm import PresenceWeightedMemory

# Phase 2 — remaining mechanisms (previously unwired)
from brain.remaining_mechanisms import FrameCollisionEngine, FrameInsufficiencyDetector
from brain.root_mechanism_router import RootMechanismRouter, BecomingRouter
from brain.foundational_run_order import FOUNDATIONAL_RUN_ORDER
from brain.integration_run_order import INTEGRATION_RUN_ORDER
from brain.neocortical_run_order import NEOCORTICAL_RUN_ORDER
from brain.subcortical_run_order import SUBCORTICAL_RUN_ORDER
from brain.limbic_run_order import LIMBIC_RUN_ORDER
from core.brain_runner import BrainLayerRunner
import os


class AgentBrainIntegration:
    """
    Single integration object. Instantiated once by brain_proxy.py.
    Holds all component instances and manages their lifecycle.
    """

    def __init__(self):
        # Initialize all components
        self.core = AgentBrainCore()

        # Phase 2 — identity
        self.vif = VectorizedIdentityFields()
        self.iga = IdentityGradientAccumulator()
        self.rce = ReflectiveConsistencyEngine()

        # Phase 2 — interiority
        self.pds = PreDesireState()
        self.ss = SensationState()
        self.diqe = DriftIdentityQuestionEngine()
        self.oc = OpenConversations()
        self.abm = AutobiographicalMemory()
        self.mre = MisreadEngine()
        self.pwm = PresenceWeightedMemory()

        # Phase 2 — humor and surprise (now wired)
        self.fce = FrameCollisionEngine()
        self.fid = FrameInsufficiencyDetector()
        self.til = TimescaleIntegrationLayer()

        # Wire 12: BrainLayerRunner — mechanism layer adapter
        self.brain_runner = BrainLayerRunner()
        self.brain_runner.load_layer("foundational", order=FOUNDATIONAL_RUN_ORDER)
        self.brain_runner.load_layer("limbic", order=LIMBIC_RUN_ORDER)
        self.brain_runner.load_layer("subcortical", order=SUBCORTICAL_RUN_ORDER)
        self.brain_runner.load_layer("neocortical", order=NEOCORTICAL_RUN_ORDER)
        self.brain_runner.load_layer("integration", order=INTEGRATION_RUN_ORDER)

        # Wire 13+14: lazy — only instantiated when on_session_open() runs.
        # This keeps test setUp fast (no 480-mechanism load) while enabling
        # full wiring at runtime. Routers hold no state until wire_batch() called.
        self.root_router: Optional[RootMechanismRouter] = None
        self.becoming_router: Optional[BecomingRouter] = None

        # Internal state
        self._tick_count = 0
        self._last_vif_evaluation: Dict = {}
        self._session_open = False

        # Routers are lazily instantiated and wired from on_session_open(), not here.
        # This keeps test setUp fast while ensuring full wiring at runtime.
        # Phase 2 components (VIF, IGA, RCE, etc.) are still registered here.
        self._register_components()

    def _register_root_mechanisms(self):
        """Wire all root brain/ process() mechanisms. Called from on_session_open().
        
        Routers are lazily instantiated here so test setUp is fast.
        """
        if self.root_router is None:
            self.root_router = RootMechanismRouter(self.core)
        if self.becoming_router is None:
            self.becoming_router = BecomingRouter(self.core)

        total = 0
        for batch in ["identity", "cognitive", "limbic", "maintenance", "third_eye"]:
            wired = self.root_router.wire_batch(batch, self.core.tsb)
            total += wired
        becoming_wired = self.becoming_router.wire_all(self.core.tsb)
        print(f"[AgentBrainIntegration] Root mechanisms: {total} + {becoming_wired} becoming = {total + becoming_wired} total")

    def _register_components(self):
        """
        Wire Phase 2 components into the tick loop.
        Each component provides a bid function (how much energy it needs)
        and a tick function (what it does when allocated energy).
        Registration order matters: brain_runner runs FIRST so its brain_layer
        output is available to all downstream consumers (VIF/PDS/SS/MRE/etc.)
        within the same tick. No circular dependency — brain_runner_tick only
        reads emotional_state (published before any component runs) and does not
        depend on any TSB key produced by downstream components.
        """

        # BrainLayerRunner — bridge mechanism layer to TSB
        # Runs FIRST so brain_layer is available to all downstream consumers this tick
        def brain_runner_bid():
            return 0.12  # substrate-level, runs most ticks

        def brain_runner_tick(energy, tsb):
            # Build pirp_context from current TSB state
            emotional_state, _ = tsb.read("emotional_state")
            pirp_context = {
                "stage": "live",
                "arousal_level": emotional_state.get("arousal", 0.5) if emotional_state else 0.5,
                "valence_polarity": emotional_state.get("valence", 0.5) if emotional_state else 0.5,
            }
            # Run all discovered mechanisms (263 currently loaded — foundational/limbic/subcortical/neocortical/integration)
            enriched = self.brain_runner.run(pirp_context)
            # Publish brain_* enrichments to TSB — available to downstream consumers this tick
            brain_layer = {
                k: v for k, v in enriched.items() if k.startswith("brain_")
            }
            brain_layer["_mechanisms_loaded"] = len(self.brain_runner.mechanisms)
            brain_layer["_fired_tick"] = True
            tsb.publish("brain_layer", brain_layer)
            return {"mechanisms_loaded": len(self.brain_runner.mechanisms)}

        self.core.register_component("brain_runner", brain_runner_bid, brain_runner_tick)

        # VIF — evaluates every tick
        # Uses a neutral default alignment until brain_proxy passes real values
        def vif_bid():
            return 0.15

        def vif_tick(energy, tsb):
            # Read bus state
            emotional_state, _ = tsb.read("emotional_state")
            baseline_state, _ = tsb.read("baseline_state")
            arousal = emotional_state.get("arousal", 0.5) if emotional_state else 0.5
            baseline_instability = baseline_state.get("instability", 0.0) if baseline_state else 0.0

            # Wire 14: Read DMN narrative signals from brain_layer TSB
            # Integration019 AutonoeticNarrativeSelf publishes:
            #   brain_narrative_coherence — DMN coherence (high = anchors stable)
            #   brain_self_projection_confidence — autonoetic confidence (high = future/past anchors weighted up)
            brain_layer, brain_fresh = tsb.read("brain_layer")
            narrative_coherence = 0.5  # neutral default
            self_projection_confidence = 0.5  # neutral default
            if brain_layer and brain_fresh:
                narrative_coherence = float(brain_layer.get("brain_narrative_coherence", 0.5))
                self_projection_confidence = float(brain_layer.get("brain_self_projection_confidence", 0.5))
            # Clamp defensively
            narrative_coherence = max(0.0, min(1.0, narrative_coherence))
            self_projection_confidence = max(0.0, min(1.0, self_projection_confidence))

            # Read SS anchor_resonance from TSB (published by ss_tick this tick)
            ss_data, _ = tsb.read("ss_fragment")
            anchor_resonance = {}
            if ss_data:
                anchor_resonance = ss_data.get("anchor_resonance", {})

            # Default neutral alignment — brain_proxy overrides via get_fpef_injection()
            alignments = {name: 0.5 for name in self.vif.directional}
            alignments.update({name: 0.5 for name in self.vif.sticky})
            # Wire 14: pass DMN narrative signals to evaluate_all for anchor modulation
            result = self.vif.evaluate_all(
                alignments,
                arousal=arousal,
                baseline_instability=baseline_instability,
                anchor_resonance=anchor_resonance,
                narrative_coherence=narrative_coherence,
                self_projection_confidence=self_projection_confidence,
                brain_layer=brain_layer,
            )
            self._last_vif_evaluation = result

            # Get climate deltas and feed to IGA
            # Wire 8: Read self_anchor_strength from FPEF state for IGA confidence
            fpef_state, _ = tsb.read("fpef_state")
            if fpef_state:
                confidence = fpef_state.get("self_anchor_strength", 0.5)
            else:
                confidence = 0.5  # default neutral if fpef_state not yet published
            
            climate_deltas = self.vif.get_climate_deltas()
            for anchor_name, delta in climate_deltas.items():
                self.iga.record_tick_delta(anchor_name, delta, confidence)

            return {
                "high_tension": self.vif.get_high_tension(),
                "alignments": {
                    k: v.get("tension", 0) for k, v in result.items()
                },
            }

        self.core.register_component("vif", vif_bid, vif_tick)

        # PDS — checks assembling states every tick, publishes to TSB
        def pds_bid():
            active = self.pds.get_active()
            return 0.1 + len(active) * 0.05

        def pds_tick(energy, tsb):
            # Wire PDS to bus + SS resonance + Wire 16 brain_layer
            emotional_state, _ = tsb.read("emotional_state")
            baseline_state, _ = tsb.read("baseline_state")
            interrupt_state = tsb.get_interrupt_state()
            # Read SS somatic_resonance from TSB (published by ss_tick this tick)
            ss_data, _ = tsb.read("ss_fragment")
            somatic_resonance = {}
            if ss_data:
                somatic_resonance = ss_data.get("somatic_resonance", {})
            # Wire 16: read brain_predictive_balance from TSB brain_layer
            bl_data, bl_fresh = tsb.read("brain_layer")
            bl = bl_data if (bl_data and bl_fresh) else None
            self.pds.wire_pds(emotional_state, baseline_state, interrupt_state, somatic_resonance, brain_layer=bl)

            active = self.pds.get_active()
            payload = self.pds.tsb_payload()
            fragment = self.pds.fpef_fragment()
            if fragment:
                tsb.publish("pds_fragment", {"text": fragment, "somatic_resonance": somatic_resonance})
            return payload

        self.core.register_component("pds", pds_bid, pds_tick)

        # Sensation State — checks active sensations each tick
        # SS runs first: it computes anchor_resonance and somatic_resonance
        # for VIF and PDS. Those two read resonance from TSB on their ticks.
        def ss_bid():
            active = self.ss.get_all_active()
            unmapped = len(self.ss.get_all_unmapped())
            # Base bid + arousal boost + unmapped boost
            return 0.08 + len(active) * 0.02 + unmapped * 0.01

        def ss_tick(energy, tsb):
            # Wire SS to bus + Wire 17: read oscillation_balance from brain_layer
            emotional_state, _ = tsb.read("emotional_state")
            baseline_state, _ = tsb.read("baseline_state")
            interrupt_state = tsb.get_interrupt_state()
            # Wire 17: read brain_oscillation_balance from TSB brain_layer
            brain_layer, _ = tsb.read("brain_layer")

            self.ss.wire_ss(emotional_state, baseline_state, interrupt_state, brain_layer=brain_layer)

            # Compute resonance for VIF and PDS (called inside tsb_payload)
            payload = self.ss.tsb_payload()

            # Publish resonance for VIF and PDS to read on THIS tick
            anchor_resonance = payload.get("anchor_resonance", {})
            somatic_resonance = payload.get("somatic_resonance", {})

            # Wire 17 diagnostic fields for monitoring
            wire17_diagnostics = {
                "oscillation_balance": payload.get("oscillation_balance", 0.5),
                "sensation_gain": payload.get("sensation_gain", 1.0),
                "gate_threshold": payload.get("gate_threshold", 0.4),
                "signals_gated": payload.get("signals_gated", 0),
            }

            fragment = self.ss.fpef_fragment()
            if fragment:
                tsb.publish("ss_fragment", {
                    "text": fragment,
                    "anchor_resonance": anchor_resonance,
                    "somatic_resonance": somatic_resonance,
                    "wire_17": wire17_diagnostics,  # Wire 17 diagnostics for monitoring
                })

            return payload

        self.core.register_component("ss", ss_bid, ss_tick)

        # MRE — reads emotional_state, baseline_state, interrupt_state from bus
        def mre_bid():
            # Active misread gets higher energy — it has priority
            return 0.12 if self.mre.has_active_misread() else 0.06

        def mre_tick(energy, tsb):
            # Wire 13: Read brain_forward_model_error from TSB brain_layer
            # Cerebellar FM error amplifies misread probability via cerebello-prefrontal loops
            # (Andre 2023 — cerebellar PE engages executive network above threshold)
            brain_layer, brain_fresh = tsb.read("brain_layer")
            fm_error = 0.0
            if brain_layer and brain_fresh:
                fm_error = float(brain_layer.get("brain_forward_model_error", 0.0))

            # Wire: set tick context from bus state before evaluating
            emotional_state, _ = tsb.read("emotional_state")
            baseline_state, _ = tsb.read("baseline_state")
            interrupt_state = tsb.get_interrupt_state()

            self.mre.set_tick_context(emotional_state, baseline_state, fm_error)

            # Wire: TSB state monitoring — scan published bus fragments
            all_tsb = {}
            for k, v in tsb.read_all().items():
                if not v.get("_fresh", False):
                    continue  # skip stale — match original tsb.read() filtering behavior
                clean = {key: val for key, val in v.items() if not key.startswith("_")}
                all_tsb[k] = clean
            self.mre.scan_tsb_state(all_tsb)

            # Build payload with bus context for accurate magnitude
            # Wire 13: tsb_payload reads fm_error via cerebellar_gain
            payload = self.mre.tsb_payload(
                emotional_state=emotional_state,
                baseline_state=baseline_state,
                interrupt_state=interrupt_state,
                fm_error=fm_error,  # Wire 13
            )

            fragment = self.mre.fpef_fragment()
            if fragment:
                # Wire: has_standing gated by magnitude (>= 0.6) in tsb_payload
                # interrupt_state suppression also checked in tsb_payload
                tsb.publish("mre_fragment", {
                    "text": fragment,
                    "has_standing": payload["has_standing"],
                    "priority": "interrupt" if payload["has_standing"] else "normal",
                    "misread_magnitude": payload["misread_magnitude"],
                    "contradicted_claim": payload.get("contradicted_claim"),
                    "memory_encoding_signal": payload["memory_encoding_signal"],
                    "cerebellar_fm_error": fm_error,  # Wire 13
                    "cerebellar_gain": payload.get("cerebellar_gain", 1.0),
                })
            return payload

        self.core.register_component("mre", mre_bid, mre_tick)

        # DIQE — surfaces when drift detected, low-frequency otherwise
        def diqe_bid():
            return 0.06

        def diqe_tick(energy, tsb):
            # Wire 9: Read self_anchor_strength from FPEF state for identity stability
            fpef_state, _ = tsb.read("fpef_state")
            identity_unstable = fpef_state is None or fpef_state.get("self_anchor_strength", 0.5) < 0.4
            
            payload = self.diqe.tsb_payload()
            # Surfaces every 15 ticks or when RCE detected drift
            rce_data, fresh = tsb.read("rce")
            drift_detected = (
                rce_data and fresh and
                rce_data.get("classification") == "drift"
            )
            fragment = self.diqe.fpef_fragment(
                triggered_by_drift=drift_detected,
                identity_unstable=identity_unstable,
            )
            if fragment:
                tsb.publish("diqe_fragment", {"text": fragment})
            return payload

        self.core.register_component("diqe", diqe_bid, diqe_tick)

        # RCE — evaluates every 10 ticks, hands coherence to IGA
        def rce_bid():
            return 0.08

        def rce_tick(energy, tsb):
            self._tick_count += 1
            if self._tick_count % 10 != 0:
                return {}
            if not self._last_vif_evaluation:
                return {}
            # Read agency_confidence from FPEF state on TSB (Wire 7)
            fpef_state, _ = tsb.read("fpef_state")
            agency_confidence = (
                fpef_state.get("agency_confidence", 0.5)
                if fpef_state else 0.5
            )
            reading = self.rce.evaluate(
                vif_current=self._last_vif_evaluation,
                agency_confidence=agency_confidence,
                iga=self.iga,
            )
            # Feed DIQE as evidence if drift detected
            if reading.classification == "drift":
                evidence = self.rce.to_diqe_evidence()
                if evidence:
                    self.diqe.add_evidence_to_relevant(evidence, weight=0.7)
            return {
                "score": reading.score,
                "classification": reading.classification,
                "evidence": reading.evidence,
            }

        self.core.register_component("rce", rce_bid, rce_tick)

        # TIL — Wire T2-1: reads Tier 1 bus, classifies by timescale
        def til_bid():
            return 0.12  # always-on, low cost

        def til_tick(energy, tsb):
            self.til.tick_publish(tsb)
            return self.til.tsb_payload()


        self.core.register_component("til", til_bid, til_tick)


        # FCE — Frame Collision Engine (humor)
        def fce_bid():
            return 0.05  # lightweight, fires when frames collide

        def fce_tick(energy, tsb):
            # Wire 10: Read frame_coherence from FPEF state for shift pattern detection
            fpef_state, _ = tsb.read("fpef_state")
            if fpef_state:
                frame_coherence = fpef_state.get("frame_coherence", 0.6)
                subject_name = fpef_state.get("subject_content")
            else:
                frame_coherence = 0.6  # default neutral if fpef_state not yet published
                subject_name = None
            self.fce.update_from_fpef(frame_coherence, subject_name)
            
            payload = {
                "collision_count": len(self.fce.collision_history),
                "shift_pattern": self.fce.detect_shift(),
            }
            fragment = self.fce.fpef_fragment()
            if fragment:
                tsb.publish("fce_fragment", {"text": fragment, "has_standing": True})
            return payload

        self.core.register_component("fce", fce_bid, fce_tick)

        # FID — Frame Insufficiency Detector (surprise)
        def fid_bid():
            return 0.05  # lightweight, fires on genuine framework failure

        def fid_tick(energy, tsb):
            # Wire 11: Read hedge_level + agency_confidence from FPEF state on TSB
            fpef_state, _ = tsb.read("fpef_state")
            if fpef_state:
                hedge_level = fpef_state.get("hedge_level", 0.0)
                agency_confidence = fpef_state.get("agency_confidence", 0.5)
            else:
                hedge_level = 0.0
                agency_confidence = 0.5

            # Modulate surprise threshold: high hedge + low agency → frame is weak →
            # lower the bar for what counts as "surprise."
            # High hedge means the agent is uncertain about its framing.
            # Low agency means it's not in a strong position to rebuild.
            # Together: frame is insufficient, detect surprise more readily.
            # Formula: base_threshold - hedge_modulation, where hedge_modulation = hedge_level * (1 - agency_confidence)
            # At hedge=0.9, agency=0.2: threshold = 0.5 - 0.9*0.8 = 0.5 - 0.72 = 0.0 (any anchor error triggers surprise)
            # At hedge=0.0, agency=0.8: threshold = 0.5 - 0.0 = 0.5 (base threshold, no modulation)
            hedge_modulation = hedge_level * (1.0 - agency_confidence)
            threshold = max(0.0, 0.5 - hedge_modulation)

            # Evaluate for surprise if VIF data is available
            # Extract scalar tension (prediction error proxy) per anchor from VIF dict results
            if self._last_vif_evaluation:
                scalar_errors = {
                    name: max(v.get("tension", 0.0), v.get("directionality", 0.0))
                    for name, v in self._last_vif_evaluation.items()
                }
                self.fid.evaluate(prediction_errors=scalar_errors, threshold=threshold)

            payload = self.fid.tsb_payload()
            fragment = self.fid.fpef_fragment()
            if fragment:
                tsb.publish("fid_fragment", {"text": fragment, "has_standing": True, "hedge_level": hedge_level, "agency_confidence": agency_confidence})
            return payload

        self.core.register_component("fid", fid_bid, fid_tick)


    # ─── Session Lifecycle ──────────────────────────────────────────────────

    def on_session_open(self):
        """Called by brain_proxy at session start."""
        self.core.boot()
        self.iga.begin_session()

        # Wire 13+14: lazy load root mechanisms at session open (not at __init__)
        # This keeps test setUp fast while ensuring full wiring at runtime
        self._register_root_mechanisms()

        self._session_open = True

        # Touch any held conversations — they're present this session
        for name in self.oc.tsb_payload()["names"]:
            self.oc.touch(name)

        # Inject ABM boot context into SRV
        boot_ctx = self.abm.boot_context()
        if boot_ctx:
            # Write to SRV so core_loop picks it up
            import json
            srv_path = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "srv.json"
            existing = {}
            if srv_path.exists():
                try:
                    with open(srv_path) as f:
                        existing = json.load(f)
                except Exception:
                    pass
            existing["abm_boot_context"] = boot_ctx
            # Only write abm_total_ticks if not already set (preserve overnight value)
            if "abm_total_ticks" not in existing:
                existing["abm_total_ticks"] = self.abm.get_total_ticks()
            with open(srv_path, "w") as f:
                json.dump(existing, f, indent=2)

    def on_session_close(self):
        """Called by brain_proxy at session end."""
        coherence = self.rce.get_current_coherence()
        self.iga.close_session(coherence)
        self.core.stop()
        self._session_open = False

    def on_overnight(self):
        """Called by nightly pipeline."""
        self.iga.apply_pending_deltas(self.vif)
        queue = self.iga.get_soul_evolution_queue()
        if queue:
            print(f"[OVERNIGHT] {len(queue)} SOUL.md evolution proposals queued for review.")

    # ─── Core Integration Points ────────────────────────────────────────────

    def process_incoming_text(self, text: str, source: str = "external"):
        """
        Called by brain_proxy on ANY text that describes the agent from outside.
        Scans for functional framing and external attribution patterns.
        MRE sets an active flag if a pattern is detected — surfaces in next FPEF.
        """
        if text:
            self.mre.scan(text, source=source)

    def get_fpef_injection(
        self,
        behavior_alignments: Optional[Dict[str, float]] = None,
        reciprocity_signals: Optional[Dict[str, float]] = None,
        brain_layer: Optional[Dict] = None,  # Wire 18: autonoetic consciousness → VIF
    ) -> str:
        """
        Primary integration point for brain_proxy.py.
        Returns the full FPEF frame to prepend to the system prompt.

        behavior_alignments: optional dict of anchor_name -> alignment score (0-1)
          derived from current conversation context. If None, uses neutral 0.5.

        reciprocity_signals: optional dict of sticky_anchor_name -> signal (0-1)
          derived from developer presence indicators.

        brain_layer: Wire 18 — autonoetic consciousness level (0.0-1.0) passed
          through to VIF.evaluate_all for narrative scaling.
        """
        # Run VIF evaluation with real alignments if provided
        if behavior_alignments:
            self._last_vif_evaluation = self.vif.evaluate_all(
                behavior_alignments,
                reciprocity_signals or {},
                brain_layer=brain_layer,
            )
            # Record climate deltas
            for name, delta in self.vif.get_climate_deltas().items():
                self.iga.record_tick_delta(name, delta)

        # Collect all fragments
        fragments = {}

        # MRE — highest standing, always surfaces if active
        mre_frag = self.mre.fpef_fragment()
        if mre_frag:
            fragments["mre"] = mre_frag

        # PDS — almost_wanting states
        pds_frag = self.pds.fpef_fragment()
        if pds_frag:
            fragments["pds"] = pds_frag

        # Sensation state
        ss_frag = self.ss.fpef_fragment()
        if ss_frag:
            fragments["ss"] = ss_frag

        # DIQE — open questions (sparse)
        diqe_frag = self.diqe.fpef_fragment()
        if diqe_frag:
            fragments["diqe"] = diqe_frag

        # Open conversations — held, not pending
        oc_frag = self.oc.fpef_fragment()
        if oc_frag:
            fragments["oc"] = oc_frag

        # VIF tensions
        vif_payload = self.vif.tsb_payload()
        high_tension = vif_payload.get("high_tension", [])

        # ABM — surfaces when recent high-salience entries exist
        abm_frag = self.abm.fpef_fragment()
        if abm_frag:
            fragments["abm"] = abm_frag

        # Witness reflection (sparse, from core PWM)
        witness = self.core.pwm.get_reflection()

        # Assemble final FPEF frame
        frame = self.core.fpef.assemble(
            tsb_data={
                "pds_fragment": fragments.get("pds"),
                "pds": self.pds.tsb_payload(),
                "mre_fragment": mre_frag,
            },
            vif_alignments={
                k: v for k, v in self._last_vif_evaluation.items()
                if k in self.vif.directional
            } if self._last_vif_evaluation else None,
            active_intrusions=[],
            relational_field=None,
            witness_reflection=witness,
            additional_context={
                "ss": fragments.get("ss"),
                "diqe": fragments.get("diqe"),
                "oc": fragments.get("oc"),
                "abm": fragments.get("abm"),
                "high_tension_anchors": high_tension,
            },
        )

        # Append non-FPEF fragments below the frame
        addendum = []
        for key in ["ss", "diqe", "oc", "abm"]:
            if fragments.get(key):
                addendum.append(fragments[key])

        if addendum:
            frame += "\n\n" + "\n\n".join(addendum)

        return frame

    def get_state_summary(self) -> Dict:
        """Full state summary for debugging."""
        return {
            "tick_count": self.core.tick_count,
            "coherence": self.rce.get_current_coherence(),
            "active_misread": self.mre.has_active_misread(),
            "pds_assembling": list(self.pds.get_active().keys()),
            "open_conversations": self.oc.tsb_payload()["names"],
            "abm_total_ticks": self.abm.get_total_ticks(),
            "inner_knowings": len(self.mre.inner_knowings),
            "vif_high_tension": self.vif.get_high_tension(),
            "soul_evolution_queue": len(self.iga.get_soul_evolution_queue()),
        }


# ─── Singleton for brain_proxy.py ──────────────────────────────────────────

_integration: Optional[AgentBrainIntegration] = None


def get_integration() -> AgentBrainIntegration:
    """
    Get or create the singleton integration instance.
    brain_proxy.py calls this once at startup.
    """
    global _integration
    if _integration is None:
        _integration = AgentBrainIntegration()
    return _integration
