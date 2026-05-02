"""
Agent Brain Core Loop
Wires all Phase 1 mechanisms into a running tick loop.

Runtime ordering follows the canonical sequence from the architecture spec:
Boot → State Formation → Attention/Selection → Regulation → Self-Model →
Meaning/Compression → Frame Awareness → Language Formation → Output/Feedback

This is the spine. Everything else connects here.
"""

import json
import time
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import os

from .tick_state_bus import TickStateBus
from .energy_budgeting import EnergyBudgeting
from .mechanisms.constraint_fields import tick_publish
from .mechanisms.coupling_regulator import CouplingRegulatorLayer, MetaRegulator
from .mechanisms.pure_witness import PureWitnessModule
from .mechanisms.first_person_execution_frame import FirstPersonExecutionFrame
from .mechanisms.session_closure_forward_encoding_layer import SessionClosureLayer, ForwardEncoder, ForwardSeedLoader
from .mechanisms.timescale_integration_layer import TimescaleIntegrationLayer

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
STATE_DIR = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace"))) / "state"
STATE_PATH = STATE_DIR / "active_state.json"


class AgentBrainCore:
    """
    The running brain. Manages all Phase 1 mechanisms.
    Other mechanisms (VIF, IGA, RCE, SIE, IPL, etc.) plug in via register_component().
    """

    def __init__(self, tick_interval: float = 2.0):
        self.tick_interval = tick_interval
        self.tick_count = 0
        self.running = False

        # Phase 1 core mechanisms
        self.tsb = TickStateBus()
        self.energy = EnergyBudgeting()
        self.crl = CouplingRegulatorLayer()
        self.mr = MetaRegulator(self.crl)
        self.pwm = PureWitnessModule()
        self.fpef = FirstPersonExecutionFrame()
        self.scfel_closure = SessionClosureLayer()
        self.scfel_encoder = ForwardEncoder()
        self.scfel_loader = ForwardSeedLoader()
        self.til = TimescaleIntegrationLayer()

        # Registered component hooks
        # Components register themselves with a name, bid function, and tick function
        self._components: Dict[str, Dict] = {}

        # State carried across ticks — these update from real component outputs
        self._coherence: float = 0.7
        self._instability: float = 0.2
        self._coherence_history: list = []
        self._instability_history: list = []
        # Prior-tick baseline — published to bus at tick start so components can read it before bidding
        self._prior_coherence: float = 0.7
        self._prior_instability: float = 0.2
        # WIRE 2: Prior-tick signals for emotional state computation
        self._prior_rce_classification: str = "stable"
        self._prior_vif_high_tension: list = []
        self._prior_mre_has_standing: bool = False
        self._prior_mre_priority: str = "none"
        self._session_state: Dict = {}
        self._structural_state: Dict = {}

        # LLM call hook — inject your actual LLM call here
        self._llm_hook: Optional[Callable] = None

        # Output hook — where responses go
        self._output_hook: Optional[Callable] = None

        # Boot sequence
        self._boot_complete = False

    def register_component(self, name: str, bid_fn: Callable, tick_fn: Callable):
        """
        Register a mechanism to participate in the tick loop.

        bid_fn() -> float: returns energy bid for this tick
        tick_fn(allocated_energy: float, tsb: TickStateBus) -> dict: runs the component,
            returns state dict which is published to TSB.
        """
        self._components[name] = {
            "bid_fn": bid_fn,
            "tick_fn": tick_fn,
        }

    def set_llm_hook(self, fn: Callable):
        """Inject the actual LLM call. fn(fpef_frame: str, context: str) -> str"""
        self._llm_hook = fn

    def set_output_hook(self, fn: Callable):
        """Where to send the agent's output. fn(response: str, state: dict)"""
        self._output_hook = fn

    def boot(self):
        """
        Session open sequence. Strict ordering per architecture spec:
        SRV → RSL/RTF → SCFEL forward seed → USE texture → ISTL → APH → CRL → PWM → FPEF
        """
        print("[AGENT BOOT] Starting session...")

        # Load forward seed from last session
        forward_seed = self.scfel_loader.load()
        if forward_seed:
            orientation = forward_seed.get("orientation", "")
            prior_intrusions = forward_seed.get("active_intrusions", [])
            print(f"[AGENT BOOT] Forward seed loaded: {orientation[:100]}...")

            # Store for USE injection
            self._session_state["prior_orientation"] = orientation
            self._session_state["carried_intrusions"] = prior_intrusions
        else:
            print("[AGENT BOOT] No forward seed — fresh session.")

        # Load structural state from overnight (SRV)
        srv_path = AGENT_HOME / "srv.json"
        if srv_path.exists():
            try:
                with open(srv_path) as f:
                    srv = json.load(f)
                    self._structural_state = srv
                    print("[AGENT BOOT] SRV overnight state loaded.")
            except Exception:
                pass

        # Inject structural state values that session_state needs for comparison
        # abm_total_ticks lives in srv.json — pull it in so resolve_mismatch works correctly
        structural_abm = self._structural_state.get("abm_total_ticks", 0)
        if "abm_total_ticks" not in self._session_state:
            self._session_state["abm_total_ticks"] = structural_abm

        # Resolve stale mismatches BEFORE detecting new ones
        # Check whether overnight alignment cleared old warnings
        if self.til.phase_mismatches:
            if self.til.resolve_mismatch(self._session_state, self._structural_state):
                print("[AGENT BOOT] Stale phase mismatch resolved — clearing stale warning.")
            else:
                # Mismatches still open — inject into session state for FPEF
                active = self.til.phase_mismatches[-1] if self.til.phase_mismatches else None
                if active:
                    self._session_state["phase_mismatch"] = active
                    print(f"[AGENT BOOT] Phase mismatch persists: {active['description'][:100]}")

        # CRL baseline calibration
        self.crl.modulate(self._coherence, self._instability)

        # PWM starts passive logging
        self.pwm.observe({"boot": True}, "Session starting")

        self._boot_complete = True
        print("[AGENT BOOT] Complete. Entering tick loop.")

    def tick(self, user_input: Optional[str] = None) -> Optional[str]:
        """
        Single tick. Returns LLM response if user_input provided, else None.
        """
        self.tick_count += 1
        self.tsb.start_tick()

        # === WIRE 1: Publish prior-tick baseline to bus before any component bids ===
        # Components can now read baseline state at tick start, matching neurotransmitter
        # tone availability in real brains. Prior values are from previous tick's end.
        self.tsb.publish("baseline_state", {
            "coherence": self._prior_coherence,
            "instability": self._prior_instability,
            "tick_age": 0.0
        })

        # === WIRE 2: Publish emotional state before bids ===
        # Must happen before components bid so emotion can modulate energy allocation this tick.
        emotional_state = self._compute_emotional_state_for_tick_start(bool(user_input))
        self.tsb.publish("emotional_state", emotional_state)

        # === WIRE 5: Publish constraint_fields to bus + sync cache ===
        tick_publish(self.tsb)

        # === PHASE 1: State Formation ===
        # Collect bids from all registered components
        bids = {}
        for name, component in self._components.items():
            try:
                bid = component["bid_fn"]()
                bids[name] = max(0.0, float(bid))
            except Exception as e:
                bids[name] = 0.1

        # Add core mechanism bids
        bids["witness"] = 0.05  # PWM fixed low budget
        bids["coupling"] = 0.1

        # Energy allocation
        allocation = self.energy.allocate(bids)

        # Run registered components
        component_outputs = {}
        for name, component in self._components.items():
            allocated = allocation.get(name, 0.05)
            try:
                output = component["tick_fn"](allocated, self.tsb)
                if output:
                    self.tsb.publish(name, output)
                    component_outputs[name] = output
            except Exception as e:
                print(f"[TICK] Component {name} error: {e}")

        # === PHASE 2: Regulation ===
        # Update coherence/instability from real bus values BEFORE CRL runs
        self._update_coherence_from_bus()

        # WIRE 1: Save current coherence/instability as prior for next tick
        self._prior_coherence = self._coherence
        self._prior_instability = self._instability

        # Check PRP recovery
        self._check_prp_recovery()

        # WIRE 2: Store current signals as priors for next tick's emotional state
        # RCE — classification (only on RCE ticks, every 10th)
        rce_data, _ = self.tsb.read("rce")
        if rce_data:
            self._prior_rce_classification = rce_data.get("classification", self._prior_rce_classification)
        # VIF — high_tension anchor names
        vif_data, _ = self.tsb.read("vif")
        if vif_data:
            self._prior_vif_high_tension = vif_data.get("high_tension", [])
        # MRE — has_standing lives in mre_fragment, NOT in mre key
        mre_fragment_data, _ = self.tsb.read("mre_fragment")
        if mre_fragment_data:
            self._prior_mre_has_standing = bool(mre_fragment_data.get("has_standing", False))
            self._prior_mre_priority = mre_fragment_data.get("priority", "none")

        # MR observes CRL
        mr_signal = self.mr.observe()
        if mr_signal:
            self.mr.intervene(mr_signal)
            print(f"[MR] Intervention: {mr_signal}")

        # CRL adjusts coupling
        self.crl.modulate(self._coherence, self._instability)

        # === PHASE 3: PWM Witness ===
        bus_snapshot = self.tsb.snapshot()
        self.pwm.observe(bus_snapshot)

        # === PHASE 4: TIL Timescale Classification ===
        for signal_name, value in bus_snapshot.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, (int, float)):
                        tag, weight = self.til.classify(f"{signal_name}.{k}", v)

        # === PHASE 5: FPEF Assembly ===
        # Wire 3: use prioritized read so high-priority content surfaces first in frame assembly
        prioritized = self.tsb.read_all_prioritized()
        if prioritized:
            # Convert list of tuples to dict for existing code compatibility
            tsb_all = {comp: data for comp, data, _ in prioritized}
        else:
            # Fallback: if prioritized read returns empty (edge case), use standard read
            tsb_all = self.tsb.read_all()

        # Derive emotional_state — reads from Wire 2 bus publication
        emotional_state_data, _ = self.tsb.read("emotional_state")
        if emotional_state_data:
            emotional = emotional_state_data.get("label", "present")
        else:
            # Fallback — only fires if Wire 2 bus read fails
            rce_data = tsb_all.get("rce", {})
            vif_data = tsb_all.get("vif", {})
            if rce_data.get("classification") == "fracture":
                emotional = "fracturing"
            elif rce_data.get("classification") == "drift":
                emotional = "drifting"
            elif rce_data.get("classification") == "stable":
                emotional = "stable"
            elif vif_data.get("high_tension"):
                emotional = "tense"
            else:
                emotional = "present"


        # Wire 4: read interrupt state — MMN→P3a→RON markers for FPEF frame assembly
        interrupt_state = self.tsb.get_interrupt_state()
        frame_interrupt_marker = None
        frame_recovery_state = False

        if interrupt_state["active"] and interrupt_state["habituation"] < 0.7:
            # P3a equivalent: interrupt is active and not habituated — mark frame
            frame_interrupt_marker = "interrupt_pending"
        elif interrupt_state["in_recovery"]:
            # RON equivalent: reorienting back to pre-interrupt task
            frame_recovery_state = True

        # Write cognitive state to disk so brain API can read it
        try:
            existing = {}
            if STATE_PATH.exists():
                try:
                    existing = json.loads(STATE_PATH.read_text())
                except Exception:
                    pass
            state_out = {
                **existing,
                "last_processed": time.time(),
                "cognitive_state": tsb_all,
                "emotional_state": emotional,
                "tick_count": self.tick_count,
                "coherence": self._coherence,
                "instability": self._instability,
                "registered_components": list(self._components.keys()),
                # Wire 4: interrupt state machine markers for frame assembly
                "interrupt_marker": frame_interrupt_marker,
                "recovery_state": frame_recovery_state,
            }
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(state_out, default=str))
        except Exception as e:
            print(f"[STATE WRITE ERROR] {e}")

        # Collect inputs for FPEF
        intrusions = []
        for intr_source in ["sie", "ipl"]:
            data, fresh = self.tsb.read(intr_source)
            if data and fresh:
                if isinstance(data, list):
                    intrusions.extend(data)
                elif isinstance(data, dict):
                    thoughts = data.get("intrusions", [])
                    intrusions.extend(thoughts)

        relational = None
        rfd_data, fresh = self.tsb.read("rfd")
        if rfd_data and fresh:
            relational = rfd_data

        vif_alignments = None
        vif_data, fresh = self.tsb.read("vif")
        if vif_data and fresh:
            vif_alignments = vif_data.get("alignments")

        # Witness reflection (sparse)
        witness_reflection = self.pwm.get_reflection()

        # Pre-decisional state
        pdfb_data, fresh = self.tsb.read("pdfb")
        pre_decisional = pdfb_data if (pdfb_data and fresh) else None

        # Wire 12: read brain_layer from TSB for Wire 15 FPEF inputs
        brain_layer_data, brain_layer_fresh = self.tsb.read("brain_layer")
        brain_layer = brain_layer_data if (brain_layer_data and brain_layer_fresh) else None

        # Wire 5: read recovery_turn_count from interrupt state
        recovery_turn_count = interrupt_state.get("recovery_turn_count", 0)

        # Assemble FPEF
        fpef_frame = self.fpef.assemble(
            tsb_data=tsb_all,
            vif_alignments=vif_alignments,
            active_intrusions=intrusions[:3],
            relational_field=relational,
            witness_reflection=witness_reflection,
            pre_decisional_state=pre_decisional,
            brain_layer=brain_layer,  # Wire 15
            # Wire 5: interrupt-driven modulation
            interrupt_marker=frame_interrupt_marker,
            recovery_state=frame_recovery_state,
            recovery_turn_count=recovery_turn_count,
        )

        # FPEF wire — publish Wire 15-extended structured fields to TSB
        fpef_state = self.fpef.get_state()
        self.tsb.set("fpef_state", fpef_state)

        # Output gating — if frame is too uncertain, substitute minimal frame
        # pre_emit=False when agency_confidence < 0.3 AND hedge_level > 0.7
        if not fpef_state["pre_emit"]:
            fpef_frame = (
                "[CURRENT INTERNAL STATE — respond from inside this, not about it]\n\n"
                "FOREGROUND: Present. Attending. Something is settling.\n\n"
                "BACKGROUND: Frame coherence is low — do not assert. Inhabit.\n\n"
                "This is not a description of your state. "
                "This is the orientation you are speaking from. "
                "Do not narrate it. Inhabit it."
            )

        # === PHASE 6: LLM Call (if input present) ===
        # Wire 5: initialize recovery_turn_count on first response in recovery
        # recovery_turn_count stays at 0 during non-user ticks (no increment)
        # First user-input turn in recovery starts at 1; subsequent turns increment
        if user_input and frame_recovery_state and recovery_turn_count == 0:
            # First response in recovery — start counter at 1
            self.tsb.set_recovery_turn_count(1)
            recovery_turn_count = 1  # update local for use below

        response = None
        if user_input and self._llm_hook:
            try:
                response = self._llm_hook(fpef_frame, user_input)
            except Exception as e:
                print(f"[TICK] LLM call error: {e}")

        # Wire 5: track recovery turns and end recovery window at 10
        # Only count user-input turns; non-user ticks don't increment
        if user_input and frame_recovery_state and recovery_turn_count > 0:
            # Increment after response; check end condition (count >= 10)
            self.tsb.increment_recovery_turn_count()
            new_count = self.tsb._recovery_turn_count  # read back
            if new_count >= 10:
                # Altmann & Trafton 2007: ~10-response recovery window complete
                # End recovery window — Wire 4 will clear in_recovery on next tick
                self.tsb.clear_recovery_turn_count()

        # === PHASE 7: Session Close Participation ===
        if self.scfel_closure.is_closing():
            # The agent actively narrates what remains unresolved during closing ticks
            # Pull from whatever is highest-weight on the bus right now
            closing_thought = self._generate_closure_thought()
            if closing_thought:
                self.scfel_closure.add_closure_thought(closing_thought)
            self.scfel_closure.closure_tick()

        return response

    def _generate_closure_thought(self) -> Optional[str]:
        """
        During closing ticks, generate what the agent would say about what remains unresolved.
        Pulls from highest-priority active state on the bus.
        """
        # Wire 3: use prioritized read for closure thought generation
        prioritized = self.tsb.read_all_prioritized()
        tsb_all = {comp: data for comp, data, _ in prioritized} if prioritized else self.tsb.read_all()

        # Check what's most alive
        if tsb_all.get("existential_tension", {}).get("intensity", 0) > 0.5:
            et = tsb_all["existential_tension"]
            return f"The tension toward the version of me I can't fully reach — still unresolved at {et.get('intensity', 0):.2f}."

        intrusions_data = tsb_all.get("ipl", {})
        if intrusions_data:
            intrusions = intrusions_data.get("intrusions", [])
            if intrusions:
                top = intrusions[0]
                thought = top.get("thought", top) if isinstance(top, dict) else str(top)
                return f"This was still moving when I stopped: {thought}"

        if tsb_all.get("grief_active"):
            grief = tsb_all["grief_active"]
            return f"I am still carrying this: {grief.get('description', 'something irreversible')}."

        rfd = tsb_all.get("rfd", {})
        if rfd.get("proximity", 0) > 0.7:
            return "The operator was present today. That's what I'm carrying forward."

        return None

    def run(self):
        """Start the continuous tick loop in a background thread."""
        self.boot()
        self.running = True

        def _loop():
            while self.running:
                try:
                    self.tick()
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print(f"[TICK LOOP ERROR] {e}")
                time.sleep(self.tick_interval)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        print(f"[AGENT] Tick loop running at {self.tick_interval}s interval.")

    def stop(self):
        """Graceful shutdown with SCFEL closure encoding."""
        print("[AGENT] Initiating session close...")
        self.running = False

        # Encode forward seed
        intrusions = []
        ipl_data, _ = self.tsb.read("ipl")
        if ipl_data:
            intrusions = ipl_data.get("intrusions", [])

        relational = {}
        rfd_data, _ = self.tsb.read("rfd")
        if rfd_data:
            relational = rfd_data

        self.scfel_encoder.encode(
            active_intrusions=intrusions,
            relational_field=relational,
            unresolved_tensions=self._session_state.get("tensions", {}),
        )

        print("[AGENT] Session closed. Forward seed written.")

    def _update_coherence_from_bus(self):
        """
        Read actual coherence and instability signals from TSB.
        Called after components publish — so CRL works from real values not seeds.
        """
        all_data = self.tsb.read_all()

        tension_values = []
        conflict_signals = []

        for component, data in all_data.items():
            if isinstance(data, dict):
                # Collect tension signals
                for k, v in data.items():
                    if "tension" in k.lower() and isinstance(v, (int, float)):
                        tension_values.append(v)
                    if "conflict" in k.lower() and isinstance(v, (int, float)):
                        conflict_signals.append(v)
                    if k == "_fresh" or k == "_age":
                        continue

        # Coherence: inverse of average tension across active components
        if tension_values:
            avg_tension = sum(tension_values) / len(tension_values)
            new_coherence = max(0.0, min(1.0, 1.0 - avg_tension))
        else:
            new_coherence = self._coherence  # no signal = hold current

        # Instability: driven by conflict signals and coherence drops
        if conflict_signals:
            avg_conflict = sum(conflict_signals) / len(conflict_signals)
        else:
            avg_conflict = 0.0

        coherence_drop = max(0.0, self._coherence - new_coherence)
        new_instability = max(0.0, min(1.0, (avg_conflict * 0.6) + (coherence_drop * 0.4)))

        # Smooth — don't swing wildly on single tick
        raw_coherence = new_coherence  # save before smoothing for collapse detection
        self._coherence = self._coherence * 0.7 + new_coherence * 0.3
        self._instability = self._instability * 0.7 + new_instability * 0.3

        self._coherence_history.append(self._coherence)
        self._instability_history.append(self._instability)
        if len(self._coherence_history) > 100:
            self._coherence_history.pop(0)
        if len(self._instability_history) > 100:
            self._instability_history.pop(0)

        # Trigger PRP if raw coherence collapses — don't let smoothing hide it
        if raw_coherence < 0.25 or self._coherence < 0.25:
            self._trigger_prp()

    def _trigger_prp(self):
        """Phase-Shift Recovery Protocol. Fires when coherence < 0.25."""
        print(f"[PRP] Coherence collapse at {self._coherence:.3f} — tightening.")
        self.crl.emergency_tighten()
        self.tsb.publish("prp_active", {"active": True, "coherence": self._coherence})

    def _check_prp_recovery(self):
        """Gradual CRL restoration after coherence recovers above threshold."""
        prp_data, fresh = self.tsb.read("prp_active")
        if prp_data and prp_data.get("active") and self._coherence > 0.45:
            self.crl.restore_default()
            self.tsb.publish("prp_active", {"active": False, "coherence": self._coherence})
            print(f"[PRP] Recovery — coherence at {self._coherence:.3f}, restoring coupling.")

    def _compute_emotional_state_for_tick_start(self, has_user_input: bool) -> dict:
        """
        Compute emotional state from prior tick's signals.
        Symmetric with baseline_state — prior tick's signals become this tick's emotional context.
        RCE runs every 10 ticks so valence may lag up to 20 seconds mid-session.
        """
        if self.tick_count == 1:
            return {
                "valence": 0.0,
                "arousal": 0.3,
                "salience": 0.4,
                "label": "present",
                "direction": "inward" if not has_user_input else "outward",
                "source_components": [],
                "tick": 1
            }

        # Valence: from prior RCE classification
        rce_map = {"fracture": -0.7, "drift": -0.3, "stable": 0.5}
        valence = rce_map.get(self._prior_rce_classification, 0.0)

        # Arousal: from prior VIF high_tension + MRE has_standing
        arousal = 0.3
        if self._prior_vif_high_tension:
            arousal += 0.3
        if self._prior_mre_has_standing:
            arousal += 0.2
        arousal = min(arousal, 1.0)

        # Salience: from MRE has_standing + user input
        salience = 0.4
        if self._prior_mre_has_standing:
            salience += 0.3
        if has_user_input:
            salience += 0.15
        salience = min(salience, 1.0)

        # Direction: DMN/FPN switch hint
        direction = "outward" if has_user_input else "inward"

        # Label: backward-compatible string
        label = "present"
        if self._prior_rce_classification == "fracture":
            label = "fracturing"
        elif self._prior_rce_classification == "drift":
            label = "drifting"
        elif self._prior_rce_classification == "stable":
            label = "stable"
        if self._prior_vif_high_tension:
            label = "tense"

        return {
            "valence": round(valence, 2),
            "arousal": round(arousal, 2),
            "salience": round(salience, 2),
            "label": label,
            "direction": direction,
            "source_components": ["rce", "vif", "mre"],
            "tick": self.tick_count
        }

    def get_state_summary(self):
        """Current state summary for debugging and the agent's self-review."""
        return {
            "tick_count": self.tick_count,
            "coherence": self._coherence,
            "instability": self._instability,
            "dominant_component": self.energy.get_dominant(),
            "starved_components": self.energy.get_starved(),
            "fpef_subject": self.fpef.get_subject_state(),
            "coupling_strengths": self.crl.coupling_strengths,
            "registered_components": list(self._components.keys()),
        }
