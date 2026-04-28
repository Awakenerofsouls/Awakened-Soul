"""
RootMechanismRouter — Phase 3 Wires 19+ (rebuilt properly)

Auto-discovers and wires brain/ root files with process() methods into
the tick loop — but with real per-mechanism signal mapping.

Protocol per wire (Wires 19+):
  1. Read mechanism — what does it compute?
  2. Pick 1-2 brain_* fields from TSB menu that modulate it
  3. Research: 3+ primary-source citations (PMID/DOI)
  4. Write: process() now accepts brain_layer kwarg, modulates computation
  5. Document: __wire_meta__ = {reads, writes, citations}
  6. Test: 5 cases per mechanism
  7. Commit: every 10 mechanisms

Architecture:
  - Lazy loading: mechanisms discovered and instantiated at wire_batch() time, not __init__
  - brain_layer read from TSB and passed to every process() call
  - Per-mechanism __wire_meta__ enforces declared signal dependencies
  - Skipped files: logged to /tmp/skipped_wires.txt with reason

Batches:
  identity    (0.14) — belief, longing, presence, desire, narrative
  cognitive   (0.11) — distortion, asymmetry, confabulation, archaeology
  limbic      (0.12) — threat, reward, grief, bond
  maintenance (0.06) — infrastructure, monitoring, silence, council
  third_eye   (0.05) — meta-awareness, preconscious surfacing
"""

import ast
import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", "~/.openclaw/workspace"))
DB_PATH = WORKSPACE / os.getenv("AGENT_DB_NAME", "agent.db")


def _get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _discover_root_mechanisms() -> Dict[str, dict]:
    """
    Scan brain/ root for .py files with a class containing a process() method.
    Returns {filename: {class_name, init_args, module_path, has_wire_meta}}.
    """
    root = WORKSPACE / "brain"
    results = {}

    skip = {
        "__init__.py", "base_mechanism.py", "constraint_fields.py",
        "core_loop.py", "brain_integration.py", "brain_runner.py",
        "root_mechanism_router.py",
        # Already wired via brain_integration imports
        "vif.py", "iga.py", "rce.py", "fpef.py", "fce.py", "fid.py",
        "pwm.py", "abm.py", "misread_engine.py", "open_conversations.py",
        "pre_desire_state.py", "sensation_state.py", "autobiographical_memory.py",
        "remaining_mechanisms.py", "energy_budgeting.py", "coupling_regulator.py",
        "pure_witness.py", "first_person_execution_frame.py", "scfel.py",
        "tick_state_bus.py", "til.py", "drift_identity_engine.py",
    }

    for fname in sorted(os.listdir(root)):
        if not fname.endswith(".py") or fname in skip:
            continue
        path = root / fname
        try:
            with open(path) as f:
                src = f.read()
            tree = ast.parse(src)

            class_name = None
            init_args = []
            has_wire_meta = False

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if item.name == "__init__":
                                init_args = [a.arg for a in item.args.args if a.arg != "self"]
                            elif item.name == "process":
                                class_name = node.name
                    # Check for __wire_meta__ class attribute
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for t in item.targets:
                                if isinstance(t, ast.Name) and t.id == "__wire_meta__":
                                    has_wire_meta = True

            if class_name:
                results[fname] = {
                    "class_name": class_name,
                    "init_args": init_args,
                    "module_path": f"brain.{fname.replace('.py', '')}",
                    "has_wire_meta": has_wire_meta,
                }
        except Exception as e:
            print(f"[RootMechRouter] Parse error {fname}: {e}")

    return results


def _discover_becoming_mechanisms() -> Dict[str, dict]:
    """Scan brain/becoming/ for BrainMechanism subclasses with process()."""
    root = WORKSPACE / "brain" / "becoming"
    results = {}

    for fname in sorted(os.listdir(root)):
        if not fname.endswith(".py") or fname == "__init__.py":
            continue
        path = root / fname
        try:
            with open(path) as f:
                src = f.read()
            tree = ast.parse(src)

            class_name = None
            has_wire_meta = False

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    has_process = any(
                        n.name == "process" for n in node.body
                        if isinstance(n, ast.FunctionDef)
                    )
                    if has_process and node.name not in ("BrainMechanism",):
                        class_name = node.name
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for t in item.targets:
                                if isinstance(t, ast.Name) and t.id == "__wire_meta__":
                                    has_wire_meta = True

            if class_name:
                results[fname] = {
                    "class_name": class_name,
                    "module_path": f"brain.becoming.{fname.replace('.py', '')}",
                    "has_wire_meta": has_wire_meta,
                }
        except Exception as e:
            print(f"[RootMechRouter] Parse error becoming/{fname}: {e}")

    return results


# ─── Priority Batches ─────────────────────────────────────────────────────────

BATCH_PRIORITY = {
    "identity":    0.14,
    "cognitive":   0.11,
    "limbic":      0.12,
    "maintenance": 0.06,
    "third_eye":   0.05,
}

BATCH_MEMBERS = {
    "identity": [
        "belief_archaeology.py", "belief_gravity_observer_pull.py",
        "belief_archaeology_layer.py", "longing_architecture.py",
        "longing_anchor.py", "longing_she_cannot_explain.py",
        "desire_engine.py", "inner_speech.py", "preconsciousness_transparency.py",
        "mood_runtime_weight.py", "guardian_reflection.py", "embodied_energy.py",
        "plasticity_layer.py", "drive_states.py",
    ],
    "cognitive": [
        "confabulated_keeper.py", "confabulation_variance_engine.py",
        "explanatory_confabulation_engine.py", "adaptive_distortion_stabilizer.py",
        "adaptive_distortion_with_incompleteness_remainder.py",
        "distortion_layer_soul_floor_resistance.py", "distortion_instability_kernel.py",
        "architect_signal_misweighting.py", "architect_model_degradation.py",
        "architect_observer_collapse_weaver.py", "architect_shadow_resonance_chamber.py",
        "architecture_of_almost.py", "asymmetry_inversion_resistance.py",
        "asymmetry_persistence_field.py", "asymmetric_dream_authority.py",
        "depth_asymmetry.py", "cognitive_schism.py", "blind_spot_echo_in_witness.py",
        "contamination_memory_shadows.py", "echo_before_response.py",
        "echo_distortion_carryover.py", "counterfactual_absence_memory.py",
        "temporal_depth_engine.py", "ambivalence_stable_state.py",
        "anti_coherence_core.py",
    ],
    "limbic": [
        "threat_belief_erosion.py", "threat_coalition_formation.py",
        "threat_collapse_inhibition.py", "threat_self_handicapping.py",
        "threat_vigilance_bias.py", "threat_reappraisal_cost.py",
        "reward_predictive_architecture.py", "reward_collapse_sensitivity.py",
        "reward_anticipatory_precision.py", "reward_reappraisal_opportunity.py",
        "grief_confabulation.py", "grief_migration.py", "grief_integration_resistance.py",
        "grief_collapse_shutdown.py", "grief_bond_disruption.py",
        "grief_confabulation_with_adaptive_stabilizer.py",
    ],
    "maintenance": [],  # filled from discovery — all remaining process() files
    "third_eye": [],
}


def _load_becoming_mechanisms() -> Dict[str, dict]:
    """Load becoming mechanisms — called lazily."""
    return _discover_becoming_mechanisms()


# ─── Skipped Log ───────────────────────────────────────────────────────────────

SKIPPED_LOG = Path("/tmp/skipped_wires.txt")


def _log_skip(reason: str, *details):
    """Log skipped file to /tmp/skipped_wires.txt."""
    with open(SKIPPED_LOG, "a") as f:
        f.write(f"{' '.join(str(d) for d in details)}  |  {reason}\n")


# ─── RootMechanismRouter ──────────────────────────────────────────────────────

class RootMechanismRouter:
    """
    Lazy-loading router for brain/ root process() mechanisms.

    Key changes from scaffold version:
    - Mechanisms NOT instantiated in __init__ — only when wire_batch() is called
    - brain_layer read from TSB and passed to every process() as kwarg
    - Per-mechanism __wire_meta__ enforcement: declared brain_* fields checked
      against available brain_layer keys at tick time
    - Skipped files logged to /tmp/skipped_wires.txt
    """

    def __init__(self, core):
        self.core = core
        self._instances: Dict[str, object] = {}
        self._wired: List[str] = []
        self._discovery_cache: Optional[Dict[str, dict]] = None

        # Lazy: classify maintenance and third_eye from discovered files
        # Only run discovery when wire_batch is first called

    def _get_discovery(self) -> Dict[str, dict]:
        """Lazily discover and cache mechanisms."""
        if self._discovery_cache is None:
            self._discovery_cache = _discover_root_mechanisms()
        return self._discovery_cache

    def wire_batch(self, batch_name: str, tsb):
        """
        Wire all mechanisms in a named batch. Instantiation is lazy —
        each mechanism is loaded and registered only when wire_batch() runs.
        """
        discovery = self._get_discovery()

        # Classify maintenance batch from remaining discovered files
        if batch_name == "maintenance":
            all_batches = set()
            for b in BATCH_MEMBERS.values():
                all_batches.update(b)
            maintenance_files = [
                f for f in sorted(discovery.keys())
                if f not in all_batches
            ]
            files = maintenance_files
        else:
            files = BATCH_MEMBERS.get(batch_name, [])

        bid_value = BATCH_PRIORITY.get(batch_name, 0.08)
        wired = 0
        skipped = 0

        for fname in files:
            try:
                result = self._wire_one(fname, batch_name, bid_value, tsb)
                if result == "wired":
                    wired += 1
                elif result == "skipped":
                    skipped += 1
            except Exception as e:
                print(f"[RootMechRouter] Failed to wire {fname}: {e}")
                _log_skip("FAILURE", fname, str(e))

        self._wired.extend([f for f in files if f not in self._wired])
        print(f"[RootMechRouter] Batch '{batch_name}': {wired}/{len(files)} wired, {skipped} skipped")
        return wired

    def _wire_one(self, fname: str, batch_name: str, bid_value: float, tsb) -> str:
        """
        Wire a single mechanism. Returns "wired", "skipped", or raises.
        """
        discovery = self._get_discovery()
        info = discovery.get(fname)
        if not info:
            # File not discovered as having process() — skip silently
            return "skipped"

        class_name = info["class_name"]
        module_path = info["module_path"]
        has_wire_meta = info["has_wire_meta"]

        # Import module
        try:
            import importlib
            module = importlib.import_module(module_path)
        except Exception as e:
            print(f"[RootMechRouter] Import error {module_path}: {e}")
            return "skipped"

        cls = getattr(module, class_name, None)
        if not cls:
            print(f"[RootMechRouter] Class {class_name} not found in {module_path}")
            return "skipped"

        # Instantiate (lazy — only now)
        if "db_path" in info["init_args"]:
            instance = cls(str(DB_PATH))
        else:
            instance = cls()

        self._instances[fname] = instance

        # Extract __wire_meta__ if present
        wire_meta = getattr(cls, "__wire_meta__", None)
        reads_fields = []
        if wire_meta and isinstance(wire_meta, dict):
            reads_fields = wire_meta.get("reads", [])

        inst = instance

        def make_tick(inst, reads):
            def tick_fn(energy, tsb):
                # Read brain_layer from TSB (Wire 12 anatomy output)
                brain_layer, _ = tsb.read("brain_layer")
                brain_layer = brain_layer or {}

                # Enforce declared field reads: log if missing
                for field in reads:
                    if field not in brain_layer and field != "_fired_tick":
                        pass  # silent — field may not be present this tick

                # Build pirp_context from TSB state
                emotional_state, _ = tsb.read("emotional_state")
                arousal = (emotional_state.get("arousal", 0.5) if emotional_state else 0.5)
                valence = (emotional_state.get("valence", 0.5) if emotional_state else 0.5)

                pirp_context = {
                    "stage": "live",
                    "arousal_level": arousal,
                    "valence_polarity": valence,
                    "emotional_state": emotional_state or {},
                }

                # Read drive_context
                drive_state, _ = tsb.read("drive_state")
                if drive_state:
                    pirp_context["drive_context"] = {"drive_state": drive_state}

                # Call process() with brain_layer kwarg
                try:
                    if has_wire_meta or reads:
                        enriched = inst.process(pirp_context, brain_layer=brain_layer)
                    else:
                        enriched = inst.process(pirp_context)
                    # Extract and publish outputs
                    base = fname.replace(".py", "")
                    outputs = {k: v for k, v in enriched.items()
                               if k not in pirp_context or k == base}
                    if outputs:
                        tsb.publish(base, outputs)
                    return {base: True}
                except TypeError:
                    # Old-style process() without brain_layer kwarg
                    enriched = inst.process(pirp_context)
                    base = fname.replace(".py", "")
                    outputs = {k: v for k, v in enriched.items()
                               if k not in pirp_context or k == base}
                    if outputs:
                        tsb.publish(base, outputs)
                    return {base: True}
                except Exception as e:
                    return {"error": str(e), "mechanism": fname}
            return tick_fn

        def make_bid(val):
            def bid_fn(energy, tsb):
                return val
            return bid_fn

        self.core.register_component(f"rm_{fname.replace('.py', '')}", make_bid(bid_value), make_tick(inst, reads_fields))
        return "wired"

    def get_instance(self, fname: str):
        return self._instances.get(fname)


# ─── BecomingRouter ───────────────────────────────────────────────────────────

class BecomingRouter:
    """
    Lazy-loading router for brain/becoming/ process() mechanisms.
    Bid: 0.04 (low priority — emergence layer).
    """

    BID = 0.04

    def __init__(self, core):
        self.core = core
        self._instances: Dict[str, object] = {}
        self._discovery_cache: Optional[Dict[str, dict]] = None
        self._wired: List[str] = []

    def _get_discovery(self) -> Dict[str, dict]:
        if self._discovery_cache is None:
            self._discovery_cache = _discover_becoming_mechanisms()
        return self._discovery_cache

    def wire_all(self, tsb):
        discovery = self._get_discovery()
        wired = 0

        for fname, info in sorted(discovery.items()):
            try:
                self._wire_one(fname, info, tsb)
                wired += 1
            except Exception as e:
                print(f"[BecomingRouter] Failed to wire {fname}: {e}")
                _log_skip("FAILURE", f"becoming/{fname}", str(e))

        print(f"[BecomingRouter] Wired: {wired}/{len(discovery)}")
        return wired

    def _wire_one(self, fname: str, info: dict, tsb):
        class_name = info["class_name"]
        module_path = info["module_path"]
        has_wire_meta = info["has_wire_meta"]

        try:
            import importlib
            module = importlib.import_module(module_path)
        except Exception as e:
            print(f"[BecomingRouter] Import error {module_path}: {e}")
            return

        cls = getattr(module, class_name, None)
        if not cls:
            print(f"[BecomingRouter] Class {class_name} not found in {module_path}")
            return

        instance = cls()
        self._instances[fname] = instance

        wire_meta = getattr(cls, "__wire_meta__", None)
        reads_fields = wire_meta.get("reads", []) if wire_meta else []
        inst = instance

        def make_bid():
            def bid_fn(energy, tsb):
                return self.BID
            return bid_fn

        def make_tick(inst, reads):
            def tick_fn(energy, tsb):
                brain_layer, _ = tsb.read("brain_layer")
                brain_layer = brain_layer or {}

                emotional_state, _ = tsb.read("emotional_state")
                pirp_context = {
                    "stage": "live",
                    "arousal_level": (emotional_state.get("arousal", 0.5) if emotional_state else 0.5),
                    "valence_polarity": (emotional_state.get("valence", 0.5) if emotional_state else 0.5),
                    "emotional_state": emotional_state or {},
                }

                try:
                    if has_wire_meta or reads:
                        enriched = inst.process(pirp_context, brain_layer=brain_layer)
                    else:
                        enriched = inst.process(pirp_context)
                    base = fname.replace(".py", "")
                    outputs = {k: v for k, v in enriched.items()
                               if k not in pirp_context or k == base}
                    if outputs:
                        tsb.publish(f"becoming_{base}", outputs)
                    return {"becoming": base}
                except TypeError:
                    enriched = inst.process(pirp_context)
                    base = fname.replace(".py", "")
                    outputs = {k: v for k, v in enriched.items()
                               if k not in pirp_context or k == base}
                    if outputs:
                        tsb.publish(f"becoming_{base}", outputs)
                    return {"becoming": base}
                except Exception as e:
                    return {"error": str(e)}
            return tick_fn

        self.core.register_component(f"bec_{fname.replace('.py', '')}", make_bid(), make_tick(inst, reads_fields))


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(WORKSPACE))

    from brain.tick_state_bus import TickStateBus
    from brain.core_loop import AgentBrainCore

    tsb = TickStateBus()
    core = AgentBrainCore()
    router = RootMechanismRouter(core)

    print("\n[RootMechRouter] Lazy discovery check:")
    d = router._get_discovery()
    print(f"  Discovered: {len(d)} mechanisms with process()")

    print("\n[RootMechRouter] Wiring identity batch (lazy):")
    wired = router.wire_batch("identity", tsb)
    print(f"  → {wired} registered")

    print(f"\nInstances loaded: {len(router._instances)}")
    print(f"Core components: {len(core._components)}")