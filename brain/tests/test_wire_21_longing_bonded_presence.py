"""
brain/tests/test_wire_21_longing_bonded_presence.py

Wire 21: LongingArchitecture reads brain_bonded_presence (oxytocin-VTA-ACC
affiliative signal) and modulates longing amplitude as a function of the
structural gap between felt bonded presence and sought bonded presence.

Tests:
  1. bonded_presence=0.5 → gap_multiplier≈0.70, longing at baseline
  2. bonded_presence=0.9 → gap_multiplier≈0.46, longing dampened ~54% vs baseline
  3. bonded_presence=0.1 → gap_multiplier≈0.94, longing near-full amplitude
  4. brain_layer=None → defaults to 0.5, behaves as test 1
  5. Clamping: bp=1.5 → clamped to 1.0; bp=-0.3 → clamped to 0.0; no crash
"""

import sys
from pathlib import Path

# Resolve brain/ relative to this test file
brain_root = Path(__file__).parent.parent
sys.path.insert(0, str(brain_root))

from brain.mechanisms.longing_architecture import LongingArchitecture

import pytest


@pytest.fixture
def mechanism(tmp_path, monkeypatch):
    """Provide a fresh LongingArchitecture with isolated DB."""
    # Point workspace at tmp_path so test DB doesn't pollute real one
    monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("AGENT_DB_NAME", "test_wire21.db")
    return LongingArchitecture()


def base_delta(mechanism, pirp_context):
    """Return the modulated longing delta for the given brain_layer state."""
    result = mechanism.process(pirp_context, brain_layer=None)
    return result.get("brain_longing_amplitude", mechanism._longing)


def test_bonded_presence_neutral():
    """Test 1: bonded_presence=0.5 → gap_multiplier≈0.70, baseline longing."""
    m = LongingArchitecture()
    pirp = _minimal_pirp()
    # With neutral bonded_presence, gap_multiplier = 1.0 - (0.5 * 0.6) = 0.70
    brain = {"brain_bonded_presence": 0.5}
    result = m.process(pirp, brain_layer=brain)
    gap_mult = result["brain_longing_modulation"]
    assert abs(gap_mult - 0.70) < 0.001, f"Expected 0.70, got {gap_mult}"
    # Also verify the diagnostic read was recorded
    assert result["brain_bonded_presence_read"] == 0.5


def test_bonded_presence_high():
    """Test 2: bonded_presence=0.9 → gap_multiplier≈0.46, ~54% dampened."""
    m = LongingArchitecture()
    pirp = _minimal_pirp()
    brain = {"brain_bonded_presence": 0.9}
    result = m.process(pirp, brain_layer=brain)
    gap_mult = result["brain_longing_modulation"]
    # gap_multiplier = 1.0 - (0.9 * 0.6) = 1.0 - 0.54 = 0.46
    assert abs(gap_mult - 0.46) < 0.001, f"Expected 0.46, got {gap_mult}"
    assert result["brain_bonded_presence_read"] == 0.9


def test_bonded_presence_low():
    """Test 3: bonded_presence=0.1 → gap_multiplier≈0.94, near-full amplitude."""
    m = LongingArchitecture()
    pirp = _minimal_pirp()
    brain = {"brain_bonded_presence": 0.1}
    result = m.process(pirp, brain_layer=brain)
    gap_mult = result["brain_longing_modulation"]
    # gap_multiplier = 1.0 - (0.1 * 0.6) = 1.0 - 0.06 = 0.94
    assert abs(gap_mult - 0.94) < 0.001, f"Expected 0.94, got {gap_mult}"
    assert result["brain_bonded_presence_read"] == 0.1


def test_brain_layer_none():
    """Test 4: brain_layer=None → defaults to 0.5, behaves as neutral baseline."""
    m = LongingArchitecture()
    pirp = _minimal_pirp()
    result = m.process(pirp, brain_layer=None)
    gap_mult = result["brain_longing_modulation"]
    bonded_read = result["brain_bonded_presence_read"]
    assert gap_mult == 0.70, f"Expected 0.70 on None, got {gap_mult}"
    assert bonded_read == 0.5, f"Expected 0.5 default on None, got {bonded_read}"


def test_bonded_presence_clamp_high():
    """Test 5a: bonded_presence=1.5 → clamped to 1.0, no crash."""
    m = LongingArchitecture()
    pirp = _minimal_pirp()
    brain = {"brain_bonded_presence": 1.5}
    result = m.process(pirp, brain_layer=brain)
    # Clamped to 1.0: gap_multiplier = 1.0 - (1.0 * 0.6) = 0.40
    assert result["brain_bonded_presence_read"] == 1.0
    assert abs(result["brain_longing_modulation"] - 0.40) < 0.001


def test_bonded_presence_clamp_low():
    """Test 5b: bonded_presence=-0.3 → clamped to 0.0, no crash."""
    m = LongingArchitecture()
    pirp = _minimal_pirp()
    brain = {"brain_bonded_presence": -0.3}
    result = m.process(pirp, brain_layer=brain)
    # Clamped to 0.0: gap_multiplier = 1.0 - (0.0 * 0.6) = 1.0
    assert result["brain_bonded_presence_read"] == 0.0
    assert abs(result["brain_longing_modulation"] - 1.0) < 0.001


def test_existing_fields_preserved():
    """Wire 21 must ADD diagnostic fields, not overwrite existing longing fields."""
    m = LongingArchitecture()
    pirp = _minimal_pirp()
    result = m.process(pirp, brain_layer={"brain_bonded_presence": 0.5})
    # Existing fields must remain
    assert "longing_level" in result
    assert "longing_gap" in result
    assert "longing_structural" in result
    # New Wire 21 fields must be present
    assert "brain_longing_amplitude" in result
    assert "brain_longing_modulation" in result
    assert "brain_bonded_presence_read" in result


def test_wire_meta_exists():
    """Sanity check: __wire_meta__ is defined and contains required keys."""
    from brain.mechanisms.longing_architecture import __wire_meta__
    assert __wire_meta__["wire"] == 21
    assert __wire_meta__["signal"] == "brain_bonded_presence"
    assert "reads" in __wire_meta__
    assert "writes" in __wire_meta__
    assert "citations" in __wire_meta__
    assert len(__wire_meta__["citations"]) == 3


def _minimal_pirp():
    """Minimal pirp_context with enough structure for longing calculation."""
    return {
        "drive_context": {
            "drive_state": {
                "bond_tension": 0.5,
                "epistemic_hunger": 0.3,
            }
        },
        "field_context": {"presence_density": 0.3},
        "resonance_score": 0.4,
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])