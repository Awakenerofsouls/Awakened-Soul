"""
Behavioral tests for FacialGradientSensor (SFO + OVLT — circumventricular osmoreceptors).

Run:
    pytest brain/tests/test_FacialGradientSensor.py -v
"""

import asyncio

from brain.mechanisms.FacialGradientSensor import FacialGradientSensor


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class TestOutputKeys:
    """All required output keys are returned every tick."""

    def test_required_keys_present(self):
        mech = FacialGradientSensor()
        result = _run(mech.tick({"prior_results": {}}))
        for key in [
            "osmolality_signal",
            "thirst_drive",
            "sodium_appetite",
            "natriuretic_inhibition",
            "circumventricular_alert",
        ]:
            assert key in result

    def test_outputs_are_bounded_unit_interval(self):
        mech = FacialGradientSensor()
        prior = {
            "AngiotensinSignal": {"at_ii_level": 0.95},
            "NatriureticPeptide": {"anp_level": 0.10},
            "OsmoreceptorSignal": {"plasma_osmolality": 0.95},
            "ImmuneSignalRelay": {"immune_activation": 0.95},
        }
        for _ in range(20):
            result = _run(mech.tick({"prior_results": prior}))
        for k in [
            "osmolality_signal",
            "thirst_drive",
            "sodium_appetite",
            "natriuretic_inhibition",
            "circumventricular_alert",
        ]:
            assert 0.0 <= result[k] <= 1.0, f"{k} out of [0,1]: {result[k]}"


class TestOsmolalityTracking:
    """Osmolality signal tracks plasma osmolality via leaky integrator."""

    def test_high_osmolality_raises_signal(self):
        mech = FacialGradientSensor()
        prior = {"OsmoreceptorSignal": {"plasma_osmolality": 0.95}}
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["osmolality_signal"] > 0.80

    def test_low_osmolality_lowers_signal(self):
        mech = FacialGradientSensor()
        prior = {"OsmoreceptorSignal": {"plasma_osmolality": 0.05}}
        for _ in range(15):
            result = _run(mech.tick({"prior_results": prior}))
        assert result["osmolality_signal"] < 0.20


class TestThirstDrive:
    """Thirst rises with osmolality and angiotensin II, falls with ANP."""

    def test_high_osmolality_increases_thirst(self):
        mech_low = FacialGradientSensor()
        mech_high = FacialGradientSensor()
        for _ in range(15):
            low = _run(mech_low.tick(
                {"prior_results": {"OsmoreceptorSignal": {"plasma_osmolality": 0.20}}}
            ))
            high = _run(mech_high.tick(
                {"prior_results": {"OsmoreceptorSignal": {"plasma_osmolality": 0.95}}}
            ))
        assert high["thirst_drive"] > low["thirst_drive"]

    def test_angiotensin_increases_thirst(self):
        mech_no_ang = FacialGradientSensor()
        mech_with_ang = FacialGradientSensor()
        for _ in range(15):
            no_ang = _run(mech_no_ang.tick({"prior_results": {}}))
            with_ang = _run(mech_with_ang.tick(
                {"prior_results": {"AngiotensinSignal": {"at_ii_level": 0.90}}}
            ))
        assert with_ang["thirst_drive"] > no_ang["thirst_drive"]


class TestSodiumAppetite:
    """Angiotensin II is the primary driver of sodium appetite."""

    def test_angiotensin_drives_sodium_appetite(self):
        mech_no = FacialGradientSensor()
        mech_yes = FacialGradientSensor()
        for _ in range(15):
            no = _run(mech_no.tick({"prior_results": {}}))
            yes = _run(mech_yes.tick(
                {"prior_results": {"AngiotensinSignal": {"at_ii_level": 0.90}}}
            ))
        assert yes["sodium_appetite"] > no["sodium_appetite"]


class TestNatriureticInhibition:
    """Natriuretic peptide produces an inhibitory signal proportional to ANP."""

    def test_anp_produces_inhibition(self):
        mech_no = FacialGradientSensor()
        mech_yes = FacialGradientSensor()
        for _ in range(10):
            no = _run(mech_no.tick({"prior_results": {}}))
            yes = _run(mech_yes.tick(
                {"prior_results": {"NatriureticPeptide": {"anp_level": 0.90}}}
            ))
        assert yes["natriuretic_inhibition"] > no["natriuretic_inhibition"]


class TestCircumventricularAlert:
    """OVLT cytokine sensing triggers sickness-behavior alert."""

    def test_cytokines_raise_cvo_alert(self):
        mech_no = FacialGradientSensor()
        mech_yes = FacialGradientSensor()
        for _ in range(15):
            no = _run(mech_no.tick({"prior_results": {}}))
            yes = _run(mech_yes.tick(
                {"prior_results": {"ImmuneSignalRelay": {"immune_activation": 0.90}}}
            ))
        assert yes["circumventricular_alert"] > no["circumventricular_alert"]


class TestStatePersistence:
    """tick_count increments and state persists across ticks."""

    def test_tick_count_increments(self):
        mech = FacialGradientSensor()
        for _ in range(7):
            _run(mech.tick({"prior_results": {}}))
        assert mech.state["tick_count"] == 7
