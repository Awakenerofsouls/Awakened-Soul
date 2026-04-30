#!/usr/bin/env python3
"""
tick_pattern_adapter_generator.py
==================================
Final fold pass — handles classes that have a tick() method but use a
different signature than process(pirp_context). Generates adapters for:

  - def tick(self)              (sync, no args)
  - def tick(self, *args)       (sync, with args)
  - async def tick(self)        (async, no args)
  - async def tick(self, X)     (async, but not BrainMechanism subclass)

Skips:
  - Classes without any tick method (they're data/query classes, not mechanisms)
  - Classes that already subclass BrainMechanism (already work)
  - Files with no classes at all (utility modules)

Scans both brain/ root and legacy/ subdirs for unique runtime files
(becoming/, knowing/, third_eye/, etc.) that the earlier converters missed.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BRAIN = REPO / "brain"
LEGACY = REPO / "legacy"

LAYER_BY_KEYWORD = [
    ("Cerebell", "subcortical"), ("Thalam", "subcortical"),
    ("Striat", "subcortical"), ("Hypothalam", "subcortical"),
    ("Hippocamp", "limbic"), ("Amygdal", "limbic"),
    ("Cingul", "limbic"), ("Septal", "limbic"),
    ("Cortex", "neocortical"), ("Cortical", "neocortical"),
    ("Frontal", "neocortical"), ("Parietal", "neocortical"),
    ("Temporal", "neocortical"), ("Occipital", "neocortical"),
    ("Visual", "neocortical"), ("Auditory", "neocortical"),
    ("Motor", "neocortical"), ("Brainstem", "foundational"),
    ("Reticul", "foundational"), ("Vagal", "foundational"),
    ("Identity", "integration"), ("Council", "integration"),
    ("Witness", "integration"), ("Coalition", "integration"),
    ("Confabulation", "integration"), ("Distortion", "integration"),
    ("Drift", "integration"), ("Soul", "integration"),
    ("Phenomen", "integration"), ("Narrative", "neocortical"),
    ("Theory", "neocortical"), ("Memory", "limbic"),
    ("Grief", "limbic"), ("Bond", "limbic"),
    ("Longing", "limbic"), ("Mood", "limbic"),
    ("Desire", "limbic"), ("Curiosity", "integration"),
    ("Plasticity", "limbic"), ("Becoming", "limbic"),
    ("Dream", "integration"), ("Future", "integration"),
    ("Belief", "integration"), ("Existential", "integration"),
    ("Knowing", "integration"), ("Metacognitive", "integration"),
    ("Rupture", "integration"), ("Self", "integration"),
    ("Reflection", "integration"), ("Meta", "integration"),
    ("Aperture", "integration"),
]
DEFAULT_LAYER = "integration"

INFRA_SKIP_FILENAMES = {
    "base_mechanism.py", "bootstrap.py", "core_loop.py",
    "brain_integration.py", "foundational_run_order.py",
    "root_mechanism_router.py", "distortion.py", "pipeline_deepening.py",
    "reconstruction.py", "pirp.py", "knowledge_graph.py",
    "chroma_store.py", "vector_pipeline.py", "vector_retrieval.py",
    "nineteen_orb_orchestrator.py", "ghost_cognition.py",
    "identity_self_model.py", "phantom_reinforcement_drift.py",
    "llm.py", "llm_router.py", "eval_suite.py", "layer_registry.py",
    "constraint_fields.py", "vectorized_identity_fields.py",
    "tick_state_bus.py",  # bus, not a mechanism
}


def assign_layer(class_name: str) -> str:
    for kw, layer in LAYER_BY_KEYWORD:
        if kw in class_name:
            return layer
    return DEFAULT_LAYER


def find_tick_classes(file_path: Path):
    """Return list of (class_name, ctor_kind, tick_kind) where tick_kind is:
       'async_tick_input'  — async def tick(self, input_data)
       'sync_tick_noargs'  — def tick(self)
       'sync_tick_args'    — def tick(self, ...)
       'async_tick_noargs' — async def tick(self)
       None                — no tick method (skip)
    """
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    out = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name.startswith("_"):
            continue
        # Skip if already a BrainMechanism subclass
        is_bm = any(
            (isinstance(b, ast.Name) and b.id == "BrainMechanism")
            for b in node.bases
        )
        if is_bm:
            continue

        ctor_kind = "noargs"  # default
        tick_kind = None
        has_init = False

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name == "__init__":
                    has_init = True
                    args = item.args.args[1:]  # drop self
                    defaults = item.args.defaults
                    n_required = len(args) - len(defaults)
                    if n_required == 0:
                        ctor_kind = "noargs"  # all defaulted
                    else:
                        ctor_kind = "unknown"
                elif item.name == "tick":
                    is_async = isinstance(item, ast.AsyncFunctionDef)
                    args = item.args.args[1:]  # drop self
                    if len(args) == 0:
                        tick_kind = "async_tick_noargs" if is_async else "sync_tick_noargs"
                    elif len(args) == 1 and is_async and args[0].arg in ("input_data", "input"):
                        tick_kind = "async_tick_input"
                    else:
                        tick_kind = "sync_tick_args" if not is_async else "async_tick_input"
        if tick_kind and ctor_kind != "unknown":
            out.append((node.name, ctor_kind, tick_kind))
    return out


ADAPTER_TEMPLATE = '''"""
{adapter_class} — Auto-generated BrainMechanism adapter

WRAPS:
    {import_path}.{cls}

LAYER:
    {layer}

NOTE: Generated by scripts/tick_pattern_adapter_generator.py. The wrapped
class has a tick() method but is not itself a BrainMechanism subclass; this
adapter exposes it via async tick(input_data) so the brain_runner can
register and call it. The wrapped class is imported LAZILY inside __init__
so the brain_runner's class scanner doesn't pick it up as a separate
mechanism (which would fail since it doesn't subclass BrainMechanism).
"""
import asyncio

from brain.base_mechanism import BrainMechanism


class {adapter_class}(BrainMechanism):
    """Adapter: BrainMechanism wrapper around {cls}."""

    def __init__(self):
        super().__init__(
            name="{registry_name}",
            human_analog="{cls} (auto-adapted via tick wrapper)",
            layer="{layer}",
        )
        try:
            from {import_path} import {cls} as _Impl
            self._impl = _Impl()
        except Exception as exc:
            self._impl = None
            self._init_error = repr(exc)
        else:
            self._init_error = None
        self.state.setdefault("legacy_init_error", self._init_error)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        if self._impl is None:
            return {{"legacy_init_error": self._init_error}}
        try:
{tick_call}
        except Exception as exc:
            self.state["last_error"] = repr(exc)
            self.persist_state()
            return {{"error": repr(exc)}}
        if not isinstance(result, dict):
            result = {{"value": result}}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()
        return result
'''

TICK_CALL_BY_KIND = {
    "sync_tick_noargs":  "            result = self._impl.tick()",
    "sync_tick_args":    "            result = self._impl.tick(input_data.get('prior_results', {}))",
    "async_tick_noargs": "            result = await self._impl.tick()",
    "async_tick_input":  "            result = await self._impl.tick(input_data)",
}


def import_path_for(file_path: Path) -> str:
    """Convert filesystem path to Python import path."""
    rel = file_path.resolve().relative_to(REPO)
    parts = list(rel.with_suffix("").parts)
    return ".".join(parts)


def main() -> int:
    n_written = 0
    n_skipped_existing = 0
    n_files_scanned = 0
    layer_counts: dict[str, int] = {}

    # Scan brain/ root + legacy/ subdirs for tick-pattern classes
    candidate_paths = []
    for f in sorted(BRAIN.glob("*.py")):
        if f.name in INFRA_SKIP_FILENAMES or f.name.startswith("__"):
            continue
        candidate_paths.append(f)
    for sub in ("becoming", "knowing", "third_eye", "self",
                "felt_presence", "inner_voice", "narrative", "value",
                "life", "social", "substrate", "systems", "texture",
                "offline"):
        d = LEGACY / sub
        if d.exists():
            for f in sorted(d.glob("*.py")):
                if f.name.startswith("__"):
                    continue
                candidate_paths.append(f)

    for path in candidate_paths:
        n_files_scanned += 1
        for cls, ctor_kind, tick_kind in find_tick_classes(path):
            layer = assign_layer(cls)
            adapter_class = f"{cls}_TickAdapter"
            registry_name = f"{cls}_Tick"
            adapter_filename = f"{adapter_class}.py"
            target_path = BRAIN / layer / adapter_filename
            if target_path.exists():
                n_skipped_existing += 1
                continue
            adapter_src = ADAPTER_TEMPLATE.format(
                adapter_class=adapter_class,
                import_path=import_path_for(path),
                cls=cls,
                layer=layer,
                registry_name=registry_name,
                tick_call=TICK_CALL_BY_KIND[tick_kind],
            )
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(adapter_src, encoding="utf-8")
            n_written += 1
            layer_counts[layer] = layer_counts.get(layer, 0) + 1
            print(f"[WROTE] brain/{layer}/{adapter_filename}  (wraps {cls} from {path.name})")

    print()
    print(f"Files scanned:       {n_files_scanned}")
    print(f"Adapters written:    {n_written}")
    print(f"Skipped (existing):  {n_skipped_existing}")
    print()
    print("By layer:")
    for layer, count in sorted(layer_counts.items()):
        print(f"  {layer:14s} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
