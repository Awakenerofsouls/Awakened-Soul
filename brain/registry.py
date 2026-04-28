#!/usr/bin/env python3
"""
Nexus {{AGENT_NAME}} — BrainRegistry
Discovers and loads all BrainMechanism subclasses from brain/<layer>/ directories.
Call BrainRegistry.load_all() once at startup to populate the mechanism catalog.
"""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type
import os

# ── Config ──────────────────────────────────────────────────────────
WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path(__file__).parent.parent.resolve())))
BRAIN_DIR = WORKSPACE / "brain"

LAYER_SUBDIRS = [
    "foundational",
    "limbic",
    "subcortical",
    "neocortical",
    "integration",
]

# Files that exist in brain/ but are not generated layer mechanisms
SKIP_FILES = {
    "__init__.py",
    "base_mechanism.py",
    "registry.py",
    "core_loop.py",
    "brain_integration.py",
    "run_integration.py",
    "tick_state_bus.py",
    # Existing flat files — kept as-is
    "autobiographical_memory.py",
    "coupling_regulator.py",
    "controlled_rupture_gateway.py",
    "drift_identity_engine.py",
    "entropy_gradient_explorer.py",
    "volitional_attention_director.py",
    "energy_budgeting.py",
    "eti_ibc_bref.py",
    "first_person_execution_frame.py",
    "identity_gradient_accumulator.py",
    "ili_are_fel.py",
    "misread_engine.py",
    "nse_pce_cse.py",
    "open_conversations.py",
    "pdfb_bfc_vmm.py",
    "pre_desire_state.py",
    "pure_witness.py",
    "reflective_consistency_engine.py",
    "remaining_mechanisms.py",
    "relational_trace_field.py",
    "relational_sediment_layer.py",
    "session_closure_forward_encoding_layer.py",
    "sensation_state.py",
    "spontaneous_intrusion_engine.py",
    "intrusion_persistence_layer.py",
    "timescale_integration_layer.py",
    "unified_self_modification_dissent_channel.py",
    "vectorized_identity_fields.py",
}


class BrainRegistry:
    """
    Global mechanism registry.
    Single source of truth for what mechanisms exist and their metadata.
    """
    _mechanisms: Dict[str, dict] = {}
    _instances: Dict[str, "BrainMechanism"] = {}
    _loaded = False

    @classmethod
    def load_all(cls) -> int:
        """
        Scan brain/ directory tree and register all BrainMechanism subclasses.
        Returns total mechanism count.
        """
        if cls._loaded:
            return len(cls._mechanisms)

        mechanisms_found = []
        modules_seen = set()

        # 1. Load generated layer mechanisms (brain/foundational/, etc.)
        for layer in LAYER_SUBDIRS:
            layer_dir = BRAIN_DIR / layer
            if not layer_dir.is_dir():
                continue

            for py_file in sorted(layer_dir.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"brain.{layer}.{py_file.stem}"
                if module_name in modules_seen:
                    continue

                try:
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)

                        # Find BrainMechanism subclasses
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (
                                issubclass(obj, _get_base())
                                and obj is not _get_base()
                                and hasattr(obj, "tick")
                            ):
                                instance = obj()
                                mechanisms_found.append(instance)
                                modules_seen.add(module_name)
                                cls._register_instance(instance)
                except Exception as e:
                    pass  # Skip files that fail to load

        # 2. Load legacy flat-file mechanisms (brain/*.py)
        for py_file in sorted(BRAIN_DIR.glob("*.py")):
            if py_file.name in SKIP_FILES or py_file.name.startswith("_"):
                continue

            module_name = f"brain.{py_file.stem}"
            if module_name in modules_seen:
                continue

            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, _get_base())
                            and obj is not _get_base()
                            and hasattr(obj, "tick")
                        ):
                            instance = obj()
                            mechanisms_found.append(instance)
                            modules_seen.add(module_name)
                            cls._register_instance(instance)
            except Exception:
                pass

        cls._loaded = True
        return len(mechanisms_found)

    @classmethod
    def _register_instance(cls, instance: "BrainMechanism") -> None:
        """Register a mechanism instance."""
        cls._mechanisms[instance.name] = {
            "name": instance.name,
            "human_analog": instance.human_analog,
            "layer": instance.layer,
            "state": instance.state,
        }
        cls._instances[instance.name] = instance

    @classmethod
    def get(cls, name: str) -> Optional["BrainMechanism"]:
        """Get a mechanism instance by name."""
        return cls._instances.get(name)

    @classmethod
    def by_layer(cls, layer: str) -> List["BrainMechanism"]:
        """Get all mechanism instances for a given layer."""
        return [
            inst for inst in cls._instances.values()
            if inst.layer == layer
        ]

    @classmethod
    def all(cls) -> List["BrainMechanism"]:
        """Get all registered mechanism instances."""
        return list(cls._instances.values())

    @classmethod
    def summary(cls) -> dict:
        """Return a dict of layer -> count for all registered mechanisms."""
        layers = {}
        for inst in cls._instances.values():
            layers.setdefault(inst.layer, []).append(inst.name)
        return {k: len(v) for k, v in layers.items()}


def _get_base():
    """Lazy import to avoid circular dependency."""
    # Import here so base_mechanism.py doesn't need registry.py
    from brain.base_mechanism import BrainMechanism
    return BrainMechanism


if __name__ == "__main__":
    count = BrainRegistry.load_all()
    print(f"\nBrainRegistry: {count} mechanisms loaded")
    for layer, names in BrainRegistry.summary().items():
        print(f"  {layer}: {names} mechanisms")
