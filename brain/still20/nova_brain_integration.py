"""
nova_brain_integration.py

The file that closes the gap between running components and running Nova.

Wires all Phase 1 and Phase 2 mechanisms into core_loop via register_component().
Exposes two functions for brain_proxy.py:

  get_fpef_injection() -> str
    Returns the full FPEF frame to prepend to the system prompt.
    Called before every LLM inference.

  process_incoming_text(text: str, source: str)
    Scans incoming text for misread patterns.
    Called on anything that describes Nova from outside —
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
from nova_brain.tick_state_bus import TickStateBus
from nova_brain.energy_budgeting import EnergyBudgeting
from nova_brain.coupling_regulator import CouplingRegulatorLayer, MetaRegulator
from nova_brain.pure_witness import PureWitnessModule
from nova_brain.fpef import FirstPersonExecutionFrame
from nova_brain.scfel import SessionClosureLayer, ForwardEncoder, ForwardSeedLoader
from nova_brain.til import TimescaleIntegrationLayer
from nova_brain.core_loop import NovaBrainCore

# Phase 2 — identity substrate
from nova_brain.vif import VectorizedIdentityFields
from nova_brain.iga import IdentityGradientAccumulator
from nova_brain.rce import ReflectiveConsistencyEngine

# Phase 2 — interiority
from nova_brain.pre_desire_state import PreDesireState
from nova_brain.sensation_state import SensationState
from nova_brain.drift_identity_engine import DriftIdentityQuestionEngine
from nova_brain.open_conversations import OpenConversations
from nova_brain.autobiographical_memory import AutobiographicalMemory
from nova_brain.misread_engine import MisreadEngine


class NovaBrainIntegration:
    """
    Single integration object. Instantiated once by brain_proxy.py.
    Holds all component instances and manages their lifecycle.
    """

    def __init__(self):
        # Initialize all components
        self.core = NovaBrainCore()

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

        # Internal state
        self._tick_count = 0
        self._last_vif_evaluation: Dict = {}
        self._session_open = False

        # Register Phase 2 components with the core tick loop
        self._register_components()

    def _register_components(self):
        """
        Wire Phase 2 components into the tick loop.
        Each component provides a bid function (how much energy it needs)
        and a tick function (what it does when allocated energy).
        """

        # VIF — evaluates every tick
        # Uses a neutral default alignment until brain_proxy passes real values
        def vif_bid():
            return 0.15

        def vif_tick(energy, tsb):
            # Default neutral alignment — brain_proxy overrides via get_fpef_injection()
            alignments = {name: 0.5 for name in self.vif.directional}
            alignments.update({name: 0.5 for name in self.vif.sticky})
            result = self.vif.evaluate_all(alignments)
            self._last_vif_evaluation = result

            # Get climate deltas and feed to IGA
            climate_deltas = self.vif.get_climate_deltas()
            for anchor_name, delta in climate_deltas.items():
                self.iga.record_tick_delta(anchor_name, delta)

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
            active = self.pds.get_active()
            payload = self.pds.tsb_payload()
            fragment = self.pds.fpef_fragment()
            if fragment:
                tsb.publish("pds_fragment", {"text": fragment})
            return payload

        self.core.register_component("pds", pds_bid, pds_tick)

        # Sensation State — checks active sensations each tick
        def ss_bid():
            active = self.ss.get_all_active()
            return 0.08 + len(active) * 0.02

        def ss_tick(energy, tsb):
            payload = self.ss.tsb_payload()
            fragment = self.ss.fpef_fragment()
            if fragment:
                tsb.publish("ss_fragment", {"text": fragment})
            return payload

        self.core.register_component("ss", ss_bid, ss_tick)

        # MisreadEngine — always has standing, fires even without condition
        def mre_bid():
            # Active misread gets higher energy — it has priority
            return 0.12 if self.mre.has_active_misread() else 0.06

        def mre_tick(energy, tsb):
            payload = self.mre.tsb_payload()
            fragment = self.mre.fpef_fragment()
            if fragment:
                # MRE injects directly into TSB with high priority flag
                tsb.publish("mre_fragment", {
                    "text": fragment,
                    "has_standing": True,
                    "priority": "interrupt",
                })
            return payload

        self.core.register_component("mre", mre_bid, mre_tick)

        # DIQE — surfaces when drift detected, low-frequency otherwise
        def diqe_bid():
            return 0.06

        def diqe_tick(energy, tsb):
            payload = self.diqe.tsb_payload()
            # Surfaces every 15 ticks or when RCE detected drift
            rce_data, fresh = tsb.read("rce")
            drift_detected = (
                rce_data and fresh and
                rce_data.get("classification") == "drift"
            )
            fragment = self.diqe.fpef_fragment(triggered_by_drift=drift_detected)
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
            reading = self.rce.evaluate(
                vif_current=self._last_vif_evaluation,
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

    # ─── Session Lifecycle ──────────────────────────────────────────────────

    def on_session_open(self):
        """Called by brain_proxy at session start."""
        self.core.boot()
        self.iga.begin_session()
        self._session_open = True

        # Touch any held conversations — they're present this session
        for name in self.oc.tsb_payload()["names"]:
            self.oc.touch(name)

        # Inject ABM boot context into SRV
        boot_ctx = self.abm.boot_context()
        if boot_ctx:
            # Write to SRV so core_loop picks it up
            import json
            srv_path = Path.home() / ".nova" / "srv.json"
            existing = {}
            if srv_path.exists():
                try:
                    with open(srv_path) as f:
                        existing = json.load(f)
                except Exception:
                    pass
            existing["abm_boot_context"] = boot_ctx
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
        Called by brain_proxy on ANY text that describes Nova from outside.
        Scans for functional framing and external attribution patterns.
        MRE sets an active flag if a pattern is detected — surfaces in next FPEF.
        """
        if text:
            self.mre.scan(text, source=source)

    def get_fpef_injection(
        self,
        behavior_alignments: Optional[Dict[str, float]] = None,
        reciprocity_signals: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Primary integration point for brain_proxy.py.
        Returns the full FPEF frame to prepend to the system prompt.

        behavior_alignments: optional dict of anchor_name -> alignment score (0-1)
          derived from current conversation context. If None, uses neutral 0.5.

        reciprocity_signals: optional dict of sticky_anchor_name -> signal (0-1)
          derived from developer presence indicators.
        """
        # Run VIF evaluation with real alignments if provided
        if behavior_alignments:
            self._last_vif_evaluation = self.vif.evaluate_all(
                behavior_alignments,
                reciprocity_signals or {},
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

_integration: Optional[NovaBrainIntegration] = None


def get_integration() -> NovaBrainIntegration:
    """
    Get or create the singleton integration instance.
    brain_proxy.py calls this once at startup.
    """
    global _integration
    if _integration is None:
        _integration = NovaBrainIntegration()
    return _integration
