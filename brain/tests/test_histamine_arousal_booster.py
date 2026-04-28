"""
Behavioral tests for Build 22: HistamineArousalBooster (TMN histamine).

Run:
    pytest brain/tests/test_histamine_arousal_booster.py -v
"""

import asyncio
import pytest

from brain.foundational.Foundational013HistamineArousalBooster import HistamineArousalBooster


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestHistamineTone:
    """Histamine tone tracks wake-promoting inputs."""

    def test_baseline_tone_is_nonzero(self):
        mech = HistamineArousalBooster()
        result = _run(mech.tick({"prior_results": {}}))
        assert result["histamine_tone"] > 0

    def test_high_arousal_elevates_histamine_tone(self):
        mech = HistamineArousalBooster()
        prior = {"ArousalRegulator": {"arousal_level": 0.85, "mode": "alert"}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["histamine_tone"] > 0.50

    def test_orexin_coactivation_elevates_histamine(self):
        mech = HistamineArousalBooster()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.60, "mode": "alert"},
            "OrexinWakePromoter": {"orexin_tone": 0.80},
        }
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["histamine_tone"] > 0.45


class TestSleepSuppression:
    """Sleep gate suppresses histamine tone."""

    def test_sleep_gate_open_suppresses_histamine(self):
        mech = HistamineArousalBooster()
        prior = {
            "ArousalRegulator": {"arousal_level": 0.60, "mode": "alert"},
            "OrexinWakePromoter": {"orexin_tone": 0.50},
            "ThermoSleepGate": {"sleep_gate_open": False},
        }
        for _ in range(15):
            _run(mech.tick({"prior_results": prior}))
        result_no_sleep = _run(mech.tick({"prior_results": prior}))

        prior["ThermoSleepGate"] = {"sleep_gate_open": True}
        for _ in range(15):
            _run(mech.tick({"prior_results": prior}))
        result_sleep = _run(mech.tick({"prior_results": prior}))
        assert result_sleep["histamine_tone"] < result_no_sleep["histamine_tone"]


class TestH3Autoreceptor:
    """H3 autoreceptors provide negative feedback on histamine."""

    def test_h3_suppression_increases_with_histamine_level(self):
        mech = HistamineArousalBooster()
        prior = {"ArousalRegulator": {"arousal_level": 0.80, "mode": "alert"}}
        for _ in range(25):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["h3_autoreceptor_suppression"] > 0.0


class TestAttentionEnhancement:
    """H2 receptors enhance prefrontal attention during alert/creative modes."""

    def test_alert_mode_enhances_attention_above_baseline(self):
        mech = HistamineArousalBooster()
        prior = {"ArousalRegulator": {"arousal_level": 0.70, "mode": "alert"}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["attention_enhancement"] > 0.20

    def test_creative_mode_enhances_attention(self):
        mech = HistamineArousalBooster()
        prior = {"ArousalRegulator": {"arousal_level": 0.60, "mode": "creative"}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["attention_enhancement"] > 0.15

    def test_hypoaroused_mode_reduces_attention_enhancement(self):
        mech = HistamineArousalBooster()
        prior = {"ArousalRegulator": {"arousal_level": 0.20, "mode": "hypoaroused"}}
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["attention_enhancement"] < 0.20


class TestPharmacologicalSuppression:
    """Antihistamine-like effect from gut distress suppresses histamine."""

    def test_gut_distress_suppresses_histamine_tone(self):
        mech = HistamineArousalBooster()
        prior_base = {"ArousalRegulator": {"arousal_level": 0.70, "mode": "alert"}}
        for _ in range(15):
            _run(mech.tick({"prior_results": prior_base}))
        result_base = _run(mech.tick({"prior_results": prior_base}))

        prior_gut = {
            "ArousalRegulator": {"arousal_level": 0.70, "mode": "alert"},
            "OrexinWakePromoter": {"orexin_tone": 0.50},
            "GutSignalRelay": {"gut_distress": 0.70},
        }
        for _ in range(15):
            _run(mech.tick({"prior_results": prior_gut}))
        result_gut = _run(mech.tick({"prior_results": prior_gut}))
        assert result_gut["histamine_tone"] < result_base["histamine_tone"]


class TestOutputKeys:
    """Required keys present."""

    def test_required_keys(self):
        mech = HistamineArousalBooster()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["histamine_tone", "cortical_activation",
                    "attention_enhancement", "h3_autoreceptor_suppression"]:
            assert key in result
