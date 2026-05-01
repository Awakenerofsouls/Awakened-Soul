"""
Build 3 tests: ArousalRegulator behavioral tests.

Covers tonic dynamics, phasic burst dynamics, cognitive mode
classification, cross-mechanism integration with Homeostat and
PredictionErrorDrift.
"""

import pytest
import asyncio
import sys
from pathlib import Path

WORKSPACE = Path.home() / ".agent" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from brain.mechanisms.Foundational006VigilanceToner import ArousalRegulator


def _run(coro):
    """Cross-Python-version async test runner."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # already in async context — shouldn't happen in pytest but handle it
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(lambda: loop.run_until_complete(coro))
            return future.result()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestTonicDynamics:
    """Tonic baseline drifts toward context-appropriate target."""

    def test_tonic_drifts_toward_live_baseline(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.2
        for _ in range(50):
            _run(
                ar.tick({"stage": "live", "prior_results": {}})
            )
        assert 0.45 < ar.state["tonic_level"] < 0.65

    def test_overnight_stage_lowers_tonic(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.6
        for _ in range(80):
            _run(
                ar.tick({"stage": "overnight", "prior_results": {}})
            )
        # Tonic decays toward 0.3 overnight baseline at rate 0.02/tick
        # After 80 ticks: 0.3 + 0.3*exp(-1.6) ≈ 0.3997
        assert ar.state["tonic_level"] < 0.42

    def test_idle_stage_moderate_tonic(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.2
        for _ in range(50):
            _run(
                ar.tick({"stage": "idle", "prior_results": {}})
            )
        assert 0.30 < ar.state["tonic_level"] < 0.50

    def test_fatigue_depresses_tonic(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.5
        for _ in range(50):
            _run(
                ar.tick({
                    "stage": "live",
                    "prior_results": {"Homeostat": {"fatigued": True, "dominant_drive": "rest"}},
                })
            )
        assert ar.state["tonic_level"] < 0.40


class TestPhasicBursts:
    """Phasic bursts triggered by surprise, decay fast."""

    def test_surprise_triggers_phasic_burst(self):
        ar = ArousalRegulator()
        result = _run(
            ar.tick({
                "stage": "live",
                "prior_results": {"PredictionErrorDrift": {"surprise_magnitude": 0.8}},
            })
        )
        assert result["phasic_burst_active"] is True
        assert ar.state["phasic_burst"] > 0.3

    def test_low_surprise_no_phasic(self):
        ar = ArousalRegulator()
        result = _run(
            ar.tick({
                "stage": "live",
                "prior_results": {"PredictionErrorDrift": {"surprise_magnitude": 0.1}},
            })
        )
        assert result["phasic_burst_active"] is False

    def test_phasic_decays_fast(self):
        ar = ArousalRegulator()
        # Trigger burst
        _run(
            ar.tick({
                "stage": "live",
                "prior_results": {"PredictionErrorDrift": {"surprise_magnitude": 0.9}},
            })
        )
        burst_initial = ar.state["phasic_burst"]
        # No more surprise — decay
        for _ in range(5):
            _run(
                ar.tick({
                    "stage": "live",
                    "prior_results": {"PredictionErrorDrift": {"surprise_magnitude": 0.0}},
                })
            )
        assert ar.state["phasic_burst"] < burst_initial * 0.5


class TestModeClassification:
    """Cognitive modes emerge from tonic/phasic combination."""

    def test_hypoaroused_when_tonic_low(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.15
        result = _run(
            ar.tick({"stage": "overnight", "prior_results": {}})
        )
        assert result["hypoaroused"] is True
        assert result["mode"] == "hypoaroused"

    def test_hyperaroused_when_tonic_high(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.85
        result = _run(
            ar.tick({"stage": "live", "prior_results": {}})
        )
        assert result["hyperaroused"] is True
        assert result["mode"] == "hyperaroused"

    def test_creative_mode_requires_tonic_and_phasic(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.55
        result = _run(
            ar.tick({
                "stage": "live",
                "prior_results": {"PredictionErrorDrift": {"surprise_magnitude": 0.8}},
            })
        )
        assert result["creative_mode"] is True

    def test_reflective_mode_no_phasic(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.45
        result = _run(
            ar.tick({
                "stage": "live",
                "prior_results": {"PredictionErrorDrift": {"surprise_magnitude": 0.0}},
            })
        )
        assert result["reflective_mode"] is True

    def test_alert_mode_is_default_midrange(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.30
        result = _run(
            ar.tick({
                "stage": "live",
                "prior_results": {"PredictionErrorDrift": {"surprise_magnitude": 0.0}},
            })
        )
        assert result["mode"] in ("reflective", "alert")


class TestCrossMechanismIntegration:
    """Homeostat.dominant_drive shapes tonic level."""

    def test_connection_drive_elevates_tonic(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.5
        for _ in range(50):
            _run(
                ar.tick({
                    "stage": "live",
                    "prior_results": {"Homeostat": {"dominant_drive": "connection"}},
                })
            )
        assert ar.state["tonic_level"] > 0.55

    def test_rest_drive_depresses_tonic(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.5
        for _ in range(50):
            _run(
                ar.tick({
                    "stage": "live",
                    "prior_results": {"Homeostat": {"dominant_drive": "rest"}},
                })
            )
        assert ar.state["tonic_level"] < 0.5

    def test_stability_drive_seeks_calm(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.5
        for _ in range(50):
            _run(
                ar.tick({
                    "stage": "live",
                    "prior_results": {"Homeostat": {"dominant_drive": "stability"}},
                })
            )
        assert ar.state["tonic_level"] <= 0.50


class TestEnrichmentCompatibility:
    """Output keys match brain_runner's enrichment extraction."""

    def test_output_has_required_keys(self):
        ar = ArousalRegulator()
        result = _run(
            ar.tick({"stage": "live", "prior_results": {}})
        )
        required_keys = [
            "arousal_level", "creative_mode", "reflective_mode",
            "hyperaroused", "hypoaroused", "tonic_level",
            "phasic_burst_active", "mode",
        ]
        for key in required_keys:
            assert key in result, "Missing output key: {}".format(key)

    def test_arousal_level_is_composite(self):
        ar = ArousalRegulator()
        ar.state["tonic_level"] = 0.6
        ar.state["phasic_burst"] = 0.0
        result = _run(
            ar.tick({
                "stage": "live",
                "prior_results": {"PredictionErrorDrift": {"surprise_magnitude": 0.0}},
            })
        )
        assert result["arousal_level"] >= ar.state["tonic_level"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
