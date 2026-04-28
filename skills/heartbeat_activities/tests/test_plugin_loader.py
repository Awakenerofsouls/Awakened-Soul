"""Tests for plugin_loader.py — operator plugin discovery and registration."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.plugin_loader import (
    load_operator_plugins,
    register_activity,
    get_registry,
    clear_registry,
    ACTIVITY_REGISTRY,
)


class TestRegisterActivity:
    def test_register_single_activity(self):
        clear_registry()
        called = []

        def fake_run(state):
            called.append(state)
            return {"ok": True, "category": "test"}

        register_activity("test_category", fake_run)
        registry = get_registry()
        assert "test_category" in registry
        assert registry["test_category"] is fake_run

    def test_register_replaces_existing(self):
        clear_registry()
        first = lambda s: None
        second = lambda s: None
        register_activity("dup", first)
        register_activity("dup", second)
        assert get_registry()["dup"] is second


class TestLoadOperatorPlugins:
    def test_missing_dir_returns_zero(self, tmp_path):
        clear_registry()
        result = load_operator_plugins(str(tmp_path / "NOT_A_REAL_DIR"))
        assert result == 0

    def test_loads_valid_plugin(self, tmp_path):
        clear_registry()
        plugin_file = tmp_path / "test_plugin.py"
        plugin_file.write_text(
            'CATEGORY = "test_activity"\n'
            'def run(state):\n'
            '    return {"ok": True, "category": CATEGORY}\n',
            encoding="utf-8",
        )
        count = load_operator_plugins(str(tmp_path))
        assert count == 1
        assert "test_activity" in get_registry()

    def test_skips_files_starting_with_underscore(self, tmp_path):
        clear_registry()
        (tmp_path / "_private.py").write_text("CATEGORY = 'skip'", encoding="utf-8")
        (tmp_path / "public.py").write_text("CATEGORY = 'ok'\ndef run(s): return {}", encoding="utf-8")
        count = load_operator_plugins(str(tmp_path))
        assert count == 1
        assert "ok" in get_registry()
        assert "skip" not in get_registry()

    def test_skips_plugin_without_category(self, tmp_path):
        clear_registry()
        plugin_file = tmp_path / "no_category.py"
        plugin_file.write_text(
            'def run(state): return {}\n',
            encoding="utf-8",
        )
        count = load_operator_plugins(str(tmp_path))
        assert count == 0

    def test_skips_plugin_without_run_function(self, tmp_path):
        clear_registry()
        plugin_file = tmp_path / "no_run.py"
        plugin_file.write_text('CATEGORY = "norf"\n', encoding="utf-8")
        count = load_operator_plugins(str(tmp_path))
        assert count == 0

    def test_continues_on_import_error(self, tmp_path):
        clear_registry()
        bad = tmp_path / "bad.py"
        bad.write_text("raise RuntimeError('test error')\n", encoding="utf-8")
        good = tmp_path / "good.py"
        good.write_text(
            'CATEGORY = "works"\ndef run(s): return {}',
            encoding="utf-8",
        )
        count = load_operator_plugins(str(tmp_path))
        assert count == 1
        assert "works" in get_registry()

    def test_multiple_plugins_loaded(self, tmp_path):
        clear_registry()
        (tmp_path / "plugin_a.py").write_text(
            'CATEGORY = "a"\ndef run(s): return {}',
            encoding="utf-8",
        )
        (tmp_path / "plugin_b.py").write_text(
            'CATEGORY = "b"\ndef run(s): return {}',
            encoding="utf-8",
        )
        (tmp_path / "plugin_c.py").write_text(
            'CATEGORY = "c"\ndef run(s): return {}',
            encoding="utf-8",
        )
        count = load_operator_plugins(str(tmp_path))
        assert count == 3
        registry = get_registry()
        assert all(k in registry for k in ["a", "b", "c"])


class TestGetRegistry:
    def test_returns_dict(self):
        clear_registry()
        result = get_registry()
        assert isinstance(result, dict)

    def test_persists_between_calls(self):
        clear_registry()
        register_activity("persist_test", lambda s: None)
        assert "persist_test" in get_registry()