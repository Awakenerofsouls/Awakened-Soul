"""
Plugin loader for operator-specific heartbeat activities.

Operator plugins live in ~/.agent/activities/ (or configured operator dir).
Each plugin is a Python module that exposes:
  CATEGORY: str    — registry key
  run(state) -> dict — same contract as framework activities

Plugins are loaded at boot and merged into the dispatcher's ACTIVITY_REGISTRY
alongside framework activities. If a plugin fails to load, log the error
and continue with the remaining plugins.
"""

import logging
import importlib.util
import sys
from pathlib import Path

log = logging.getLogger("heartbeat.plugins")


def _dispatcher_registry():
    """Lazily import and return the dispatcher's ACTIVITY_REGISTRY."""
    # Use same import path as runner.py (parent.parent = workspace/skills/)
    # so module identity is shared with the heartbeat_activities package
    from heartbeat_activities.dispatcher import ACTIVITY_REGISTRY as _ar
    return _ar


def get_registry() -> dict:
    """Return the shared activity registry (from dispatcher)."""
    return _dispatcher_registry()


def register_activity(category: str, run_fn: callable) -> None:
    """Register an activity function under a category name."""
    registry = _dispatcher_registry()
    registry[category] = run_fn


def load_operator_plugins(operator_dir: str = "~/.agent/activities") -> int:
    """
    Load all operator plugin modules and register them into the shared ACTIVITY_REGISTRY.

    Imports the dispatcher's ACTIVITY_REGISTRY (which framework activities
    populated on import) and adds operator plugins to it.

    Args:
        operator_dir: path to operator plugins directory (supports ~)

    Returns:
        Number of plugins successfully loaded.
    """
    try:
        registry = _dispatcher_registry()
    except ImportError:
        log.error("Could not import dispatcher ACTIVITY_REGISTRY — operator plugins not registered")
        return 0

    path = Path(operator_dir).expanduser().resolve()

    if not path.is_dir():
        log.info("Operator plugins directory not found: %s", path)
        return 0

    loaded = 0
    errors = 0

    for plugin_file in sorted(path.glob("*.py")):
        if plugin_file.name.startswith("_"):
            continue

        module_name = f"operator_plugin_{plugin_file.stem}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                log.warning("Could not load plugin: %s", plugin_file.name)
                errors += 1
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Validate the plugin contract
            if not hasattr(module, "CATEGORY"):
                log.warning("Plugin %s missing CATEGORY constant — skipping", plugin_file.name)
                errors += 1
                continue

            if not hasattr(module, "run") or not callable(module.run):
                log.warning("Plugin %s missing run(state) function — skipping", plugin_file.name)
                errors += 1
                continue

            category = module.CATEGORY
            # Use the shared registry directly (same object as dispatcher.ACTIVITY_REGISTRY)
            # and also call register_plugin to populate _PLUGIN_MODULES for affinity cache
            registry[category] = module.run
            try:
                from heartbeat_activities.dispatcher import register_plugin
                register_plugin(category, module.run, plugin_module=module)
            except ImportError:
                pass  # running standalone without dispatcher present
            log.info("Loaded operator plugin: %s (%s)", plugin_file.name, category)
            loaded += 1

        except Exception as e:
            log.error("Failed to load plugin %s: %s", plugin_file.name, e)
            errors += 1

    if loaded > 0:
        log.info("Operator plugins loaded: %d OK, %d errors", loaded, errors)
    return loaded


def clear_registry() -> None:
    """Clear the dispatcher's registry. Used for testing."""
    try:
        registry = _dispatcher_registry()
        registry.clear()
    except ImportError:
        pass


# Re-export ACTIVITY_REGISTRY as a module-level attribute for test compatibility.
# Test code does `from plugin_loader import ACTIVITY_REGISTRY`. The proxy forwards
# all attribute access (including __contains__, __setitem__, __iter__, __len__)
# to the dispatcher's real registry.
class _RegistryRef:
    """Proxy that forwards all operations to the dispatcher's real ACTIVITY_REGISTRY."""
    def __getattr__(self, name):
        return getattr(_dispatcher_registry(), name)

    def __contains__(self, key):
        return key in _dispatcher_registry()

    def __setitem__(self, key, value):
        _dispatcher_registry()[key] = value

    def __iter__(self):
        return iter(_dispatcher_registry())

    def __len__(self):
        return len(_dispatcher_registry())

    def __repr__(self):
        return f"<ACTIVITY_REGISTRY proxy, {len(self)} items>"


ACTIVITY_REGISTRY = _RegistryRef()