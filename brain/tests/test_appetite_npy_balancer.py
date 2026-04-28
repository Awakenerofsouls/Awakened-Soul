"""
Behavioral tests for Build 19: AppetiteNPYBalancer (arcuate NPY/POMC).

Run:
    pytest brain/tests/test_appetite_npy_balancer.py -v
"""

import asyncio
import pytest

from brain.foundational.Foundational010AppetiteNPYBalancer import AppetiteNPYBalancer


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestMetabolicStateBasics:
    """Hunger-satiety axis responds to metabolic state."""

    def test_hungry_state_elevates_hunger_drive(self):
        mech = AppetiteNPYBalancer()
        prior = {"Homeostat": {"metabolic_state": "hungry"}}
        result = _run(mech.tick({"prior_results": prior}))
        assert result["hunger_drive"] > 0.50

    def test_satiated_state_suppresses_hunger_drive(self):
        mech = AppetiteNPYBalancer()
        prior = {"Homeostat": {"metabolic_state": "satiated"}}
        result = _run(mech.tick({"prior_results": prior}))
        assert result["hunger_drive"] < 0.30

    def test_fed_state_moderate_hunger(self):
        mech = AppetiteNPYBalancer()
        prior = {"Homeostat": {"metabolic_state": "fed"}}
        result = _run(mech.tick({"prior_results": prior}))
        assert 0.15 <= result["hunger_drive"] <= 0.75


class TestStressSuppression:
    """Stress suppresses appetite (fight overrides feeding)."""

    def test_crh_suppresses_hunger_drive(self):
        mech = AppetiteNPYBalancer()
        prior = {
            "Homeostat": {"metabolic_state": "hungry"},
            "StressActivationAxis": {"crh_level": 0.0},
        }
        result_no_stress = _run(mech.tick({"prior_results": prior}))
        prior["StressActivationAxis"] = {"crh_level": 0.80}
        result_stress = _run(mech.tick({"prior_results": prior}))
        assert result_stress["hunger_drive"] < result_no_stress["hunger_drive"]


class TestGutDistress:
    """Nausea/gut distress suppresses appetite."""

    def test_gut_distress_suppresses_hunger_drive(self):
        mech = AppetiteNPYBalancer()
        prior = {
            "Homeostat": {"metabolic_state": "hungry"},
            "StressActivationAxis": {"crh_level": 0.0},
            "GutSignalRelay": {"gut_distress": 0.0},
        }
        result_no_nausea = _run(mech.tick({"prior_results": prior}))
        prior["GutSignalRelay"] = {"gut_distress": 0.70}
        result_nausea = _run(mech.tick({"prior_results": prior}))
        assert result_nausea["hunger_drive"] < result_no_nausea["hunger_drive"]


class TestNetBalance:
    """Net appetitive balance reflects hunger - satiety."""

    def test_hungry_state_positive_balance(self):
        mech = AppetiteNPYBalancer()
        prior = {"Homeostat": {"metabolic_state": "hungry"}}
        result = _run(mech.tick({"prior_results": prior}))
        assert result["net_appetitive_balance"] > 0.0

    def test_satiated_state_negative_balance(self):
        mech = AppetiteNPYBalancer()
        prior = {"Homeostat": {"metabolic_state": "satiated"}}
        result = _run(mech.tick({"prior_results": prior}))
        assert result["net_appetitive_balance"] < 0.0

    def test_balance_bounded(self):
        mech = AppetiteNPYBalancer()
        result = _run(
            mech.tick(
                {
                    "prior_results": {
                        "Homeostat": {"metabolic_state": "satiated"},
                        "StressActivationAxis": {"crh_level": 0.0},
                        "ArousalRegulator": {"arousal_level": 0.0},
                        "GutSignalRelay": {"gut_distress": 1.0},
                    }
                }
            )
        )
        assert -1.0 <= result["net_appetitive_balance"] <= 1.0


class TestMelanocortinTone:
    """MC4R activation (melanocortin tone) tracks POMC activity."""

    def test_melanocortin_tone_increases_with_satiety(self):
        mech = AppetiteNPYBalancer()
        prior_fed = {"Homeostat": {"metabolic_state": "fed"}}
        prior_sat = {"Homeostat": {"metabolic_state": "satiated"}}
        result_fed = _run(mech.tick({"prior_results": prior_fed}))
        result_sat = _run(mech.tick({"prior_results": prior_sat}))
        assert result_sat["melanocortin_tone"] > result_fed["melanocortin_tone"]


class TestOutputKeys:
    """Required keys present."""

    def test_required_keys(self):
        mech = AppetiteNPYBalancer()
        result = _run(mech.tick({"prior_results": {}}))
        for key in ["hunger_drive", "satiety_signal", "net_appetitive_balance", "melanocortin_tone"]:
            assert key in result
