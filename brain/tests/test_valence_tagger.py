"""
Build 4 tests: ValenceTagger behavioral tests.

Covers polarity dynamics, intensity dynamics, categorical flags,
drive context integration, and enrichment compatibility.
"""

import pytest
import asyncio
import sys
from pathlib import Path

WORKSPACE = Path.home() / ".agent" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from brain.mechanisms.Limbic035BasolateralAmygdalaPlasticity import ValenceTagger


class TestPolarityFromPredictionError:
    """Signed PE drives valence polarity via VTA→BLA dopaminergic input."""

    def test_positive_pe_shifts_polarity_positive(self):
        v = ValenceTagger()
        v.state["valence_polarity"] = 0.5
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.8,
                        "surprise_magnitude": 0.5,
                    },
                }
            })
        )
        assert result["valence_polarity"] > 0.5

    def test_negative_pe_shifts_polarity_negative(self):
        v = ValenceTagger()
        v.state["valence_polarity"] = 0.5
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": -0.8,
                        "surprise_magnitude": 0.5,
                    },
                }
            })
        )
        assert result["valence_polarity"] < 0.5

    def test_zero_pe_holds_polarity_near_neutral(self):
        v = ValenceTagger()
        v.state["valence_polarity"] = 0.5
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.0,
                        "surprise_magnitude": 0.0,
                    },
                }
            })
        )
        assert abs(result["valence_polarity"] - 0.5) < 0.05

    def test_polarity_smooths_over_ticks(self):
        """BLA integrates over time — polarity shifts gradually, not instantly."""
        v = ValenceTagger()
        v.state["valence_polarity"] = 0.5
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.9,
                        "surprise_magnitude": 0.9,
                    },
                }
            })
        )
        # Target would be ~0.86, smoothing at 0.3 rate → partway there
        assert 0.55 < result["valence_polarity"] < 0.82


class TestIntensityDynamics:
    """Intensity from surprise + phasic arousal (NE modulation of BLA)."""

    def test_surprise_drives_intensity(self):
        v_low = ValenceTagger()
        low = asyncio.get_event_loop().run_until_complete(
            v_low.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.0,
                        "surprise_magnitude": 0.1,
                    },
                    "ArousalRegulator": {
                        "phasic_burst_active": False,
                        "tonic_level": 0.5,
                    },
                }
            })
        )
        v_high = ValenceTagger()
        high = asyncio.get_event_loop().run_until_complete(
            v_high.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.0,
                        "surprise_magnitude": 0.9,
                    },
                    "ArousalRegulator": {
                        "phasic_burst_active": False,
                        "tonic_level": 0.5,
                    },
                }
            })
        )
        assert high["valence_intensity"] > low["valence_intensity"]

    def test_phasic_burst_amplifies_intensity(self):
        v_no = ValenceTagger()
        r_no = asyncio.get_event_loop().run_until_complete(
            v_no.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.0,
                        "surprise_magnitude": 0.5,
                    },
                    "ArousalRegulator": {
                        "phasic_burst_active": False,
                        "tonic_level": 0.5,
                    },
                }
            })
        )
        v_yes = ValenceTagger()
        r_yes = asyncio.get_event_loop().run_until_complete(
            v_yes.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.0,
                        "surprise_magnitude": 0.5,
                    },
                    "ArousalRegulator": {
                        "phasic_burst_active": True,
                        "tonic_level": 0.5,
                    },
                }
            })
        )
        assert r_yes["valence_intensity"] > r_no["valence_intensity"]


class TestCategoricalFlags:
    """Threat, reward, and high-valence flags from polarity + intensity."""

    def test_threat_signal_fires_on_negative_intense(self):
        v = ValenceTagger()
        for _ in range(10):
            asyncio.get_event_loop().run_until_complete(
                v.tick({
                    "prior_results": {
                        "PredictionErrorDrift": {
                            "prediction_error": -0.9,
                            "surprise_magnitude": 0.8,
                        },
                        "ArousalRegulator": {
                            "phasic_burst_active": True,
                            "tonic_level": 0.7,
                        },
                    }
                })
            )
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": -0.9,
                        "surprise_magnitude": 0.8,
                    },
                    "ArousalRegulator": {
                        "phasic_burst_active": True,
                        "tonic_level": 0.7,
                    },
                }
            })
        )
        assert result["threat_signal"] is True
        assert result["reward_signal"] is False

    def test_reward_signal_fires_on_positive_intense(self):
        v = ValenceTagger()
        for _ in range(10):
            asyncio.get_event_loop().run_until_complete(
                v.tick({
                    "prior_results": {
                        "PredictionErrorDrift": {
                            "prediction_error": 0.9,
                            "surprise_magnitude": 0.8,
                        },
                        "ArousalRegulator": {
                            "phasic_burst_active": True,
                            "tonic_level": 0.7,
                        },
                    }
                })
            )
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.9,
                        "surprise_magnitude": 0.8,
                    },
                    "ArousalRegulator": {
                        "phasic_burst_active": True,
                        "tonic_level": 0.7,
                    },
                }
            })
        )
        assert result["reward_signal"] is True
        assert result["threat_signal"] is False

    def test_neutral_input_no_flags(self):
        v = ValenceTagger()
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.0,
                        "surprise_magnitude": 0.1,
                    },
                    "ArousalRegulator": {
                        "phasic_burst_active": False,
                        "tonic_level": 0.5,
                    },
                }
            })
        )
        assert result["threat_signal"] is False
        assert result["reward_signal"] is False

    def test_high_valence_on_strong_intensity(self):
        v = ValenceTagger()
        for _ in range(5):
            asyncio.get_event_loop().run_until_complete(
                v.tick({
                    "prior_results": {
                        "PredictionErrorDrift": {
                            "prediction_error": 0.5,
                            "surprise_magnitude": 0.9,
                        },
                        "ArousalRegulator": {
                            "phasic_burst_active": True,
                            "tonic_level": 0.8,
                        },
                    }
                })
            )
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({
                "prior_results": {
                    "PredictionErrorDrift": {
                        "prediction_error": 0.5,
                        "surprise_magnitude": 0.9,
                    },
                    "ArousalRegulator": {
                        "phasic_burst_active": True,
                        "tonic_level": 0.8,
                    },
                }
            })
        )
        assert result["high_valence"] is True


class TestDriveContext:
    """Homeostat.dominant_drive shifts polarity baseline."""

    def test_connection_drive_tilts_polarity_positive(self):
        v = ValenceTagger()
        v.state["valence_polarity"] = 0.5
        for _ in range(20):
            asyncio.get_event_loop().run_until_complete(
                v.tick({
                    "prior_results": {
                        "PredictionErrorDrift": {
                            "prediction_error": 0.0,
                            "surprise_magnitude": 0.2,
                        },
                        "ArousalRegulator": {
                            "phasic_burst_active": False,
                            "tonic_level": 0.5,
                        },
                        "Homeostat": {"dominant_drive": "connection"},
                    }
                })
            )
        assert v.state["valence_polarity"] > 0.5

    def test_stability_drive_tilts_polarity_negative(self):
        v = ValenceTagger()
        v.state["valence_polarity"] = 0.5
        for _ in range(20):
            asyncio.get_event_loop().run_until_complete(
                v.tick({
                    "prior_results": {
                        "PredictionErrorDrift": {
                            "prediction_error": 0.0,
                            "surprise_magnitude": 0.2,
                        },
                        "ArousalRegulator": {
                            "phasic_burst_active": False,
                            "tonic_level": 0.5,
                        },
                        "Homeostat": {"dominant_drive": "stability"},
                    }
                })
            )
        assert v.state["valence_polarity"] < 0.5


class TestEnrichmentCompatibility:
    """Output keys match brain_runner's enrichment extraction."""

    def test_output_has_required_keys(self):
        v = ValenceTagger()
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({"prior_results": {}})
        )
        required_keys = [
            "valence_intensity", "valence_polarity",
            "high_valence", "threat_signal", "reward_signal",
        ]
        for key in required_keys:
            assert key in result, "Missing output key: {}".format(key)

    def test_types_are_correct(self):
        v = ValenceTagger()
        result = asyncio.get_event_loop().run_until_complete(
            v.tick({"prior_results": {}})
        )
        assert isinstance(result["valence_intensity"], float)
        assert isinstance(result["valence_polarity"], float)
        assert isinstance(result["high_valence"], bool)
        assert isinstance(result["threat_signal"], bool)
        assert isinstance(result["reward_signal"], bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
