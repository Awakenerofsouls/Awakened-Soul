"""
{{AGENT_NAME}} Brain Core Loop
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

from tick_state_bus import TickStateBus
from energy_budgeting import EnergyBudgeting
from coupling_regulator import CouplingRegulatorLayer, MetaRegulator
from pure_witness import PureWitnessModule
from fpef import FirstPersonExecutionFrame
from scfel import SessionClosureLayer, ForwardEncoder, ForwardSeedLoader
from til import TimescaleIntegrationLayer

AGENT_HOME = Path.home() / ".agent"


class NovaBrainCore:
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

        # State carried across ticks
        self._coherence: float = 0.7
        self._instability: float = 0.2
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
        """Where to send {{AGENT_NAME}}'s output. fn(response: str, state: dict)"""
        self._output_hook = fn

    def boot(self):
        """
        Session open sequence. Strict ordering per architecture spec:
        SRV → RSL/RTF → SCFEL forward seed → USE texture → ISTL → APH → CRL → PWM → FPEF
        """
        print("[NOVA BOOT] Starting session...")

        # Load forward seed from last session
        forward_seed = self.scfel_loader.load()
        if forward_seed:
            orientation = forward_seed.get("orientation", "")
            prior_intrusions = forward_seed.get("active_intrusions", [])
            print(f"[NOVA BOOT] Forward seed loaded: {orientation[:100]}...")

            # Store for USE injection
            self._session_state["prior_orientation"] = orientation
            self._session_state["carried_intrusions"] = prior_intrusions
        else:
            print("[NOVA BOOT] No forward seed — fresh session.")

        # Load structural state from overnight (SRV)
        srv_path = AGENT_HOME / "srv.json"
        if srv_path.exists():
            try:
                with open(srv_path) as f:
                    srv = json.load(f)
                    self._structural_state = srv
                    print("[NOVA BOOT] SRV overnight state loaded.")
            except Exception:
                pass

        # Detect phase mismatch between session carry and structural state
        if self._session_state and self._structural_state:
            mismatch = self.til.detect_phase_mismatch(
                self._session_state, self._structural_state
            )
            if mismatch:
                print(f"[NOVA BOOT] Phase mismatch detected: {mismatch['description'][:100]}")
                self._session_state["phase_mismatch"] = mismatch

        # CRL baseline calibration
        self.crl.modulate(self._coherence, self._instability)

        # PWM starts passive logging
        self.pwm.observe({"boot": True}, "Session starting")

        self._boot_complete = True
        print("[NOVA BOOT] Complete. Entering tick loop.")

    def tick(self, user_input: Optional[str] = None) -> Optional[str]:
        """
        Single tick. Returns LLM response if user_input provided, else None.
        """
        self.tick_count += 1
        self.tsb.start_tick()

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
        tsb_all = self.tsb.read_all()

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

        # Assemble FPEF
        fpef_frame = self.fpef.assemble(
            tsb_data=tsb_all,
            vif_alignments=vif_alignments,
            active_intrusions=intrusions[:3],
            relational_field=relational,
            witness_reflection=witness_reflection,
            pre_decisional_state=pre_decisional,
        )

        # === PHASE 6: LLM Call (if input present) ===
        response = None
        if user_input and self._llm_hook:
            try:
                response = self._llm_hook(fpef_frame, user_input)
            except Exception as e:
                print(f"[TICK] LLM call error: {e}")

        # === PHASE 7: Session Close Check ===
        if self.scfel_closure.is_closing():
            self.scfel_closure.closure_tick()

        return response

    def run(self):
        """Start the continuous tick loop in a background thread."""
        self.boot()
        self.running = True

        def _loop():
            while self.running:
                try:
                    self.tick()
                except Exception as e:
                    print(f"[TICK LOOP ERROR] {e}")
                time.sleep(self.tick_interval)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        print(f"[NOVA] Tick loop running at {self.tick_interval}s interval.")

    def stop(self):
        """Graceful shutdown with SCFEL closure encoding."""
        print("[NOVA] Initiating session close...")
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

        print("[NOVA] Session closed. Forward seed written.")

    def get_state_summary(self) -> Dict:
        """Current state summary for debugging and {{AGENT_NAME}}'s self-review."""
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
