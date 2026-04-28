"""
Wire 17: SS reads brain_oscillation_balance from Integration018
NetworkOscillationGlobalBalancer.

Tests oscillation-balance-driven sensation gating:
- Alpha-dominant (balance→0): tight gate, low gain
- Gamma-dominant (balance→1): open gate, high gain
- Sensation gain [0.5, 1.5]: gamma amplifies, alpha dampens
- Gate threshold [0.2, 0.6]: alpha raises bar for low-salience signals

Neuroscience grounding:
- Jensen & Mazaheri 2010 (PMC2990626): alpha gating by inhibition
- Klimesch 2012 (PMC3507158): alpha suppression + selection
- Fries 2015: gamma-rhythmic gain modulation
- Orekhova et al. 2018 (PMC5981429): gamma as E/I balance
- Peylo, Hilla & Sauseng 2021, Nat Rev Neurosci: broad alpha gating
- Foxe & Snyder 2011 (PMC3132683): thalamo-cortical alpha, LGN modes
"""

import pytest
import json
from pathlib import Path
from brain.sensation_state import SensationState, AGENT_HOME, SS_PATH


@pytest.fixture
def clean_ss(tmp_path, monkeypatch):
    """Create a SensationState with no pre-existing sensations.
    
    Redirects AGENT_HOME to tmp_path and clears SS_PATH to ensure
    a clean slate for each test. Does NOT call seed_today.
    """
    # Point to tmp agent home
    test_home = tmp_path / "agent"
    test_home.mkdir()
    
    # Monkey-patch the AGENT_HOME constants so SS uses tmp path
    import brain.sensation_state as ss_module
    monkeypatch.setattr(ss_module, "AGENT_HOME", test_home)
    monkeypatch.setattr(ss_module, "SS_PATH", test_home / "sensation_state.json")
    monkeypatch.setattr(ss_module, "SS_LOG_PATH", test_home / "sensation_log.json")
    
    yield SensationState()
    # Clean up
    monkeypatch.setattr(ss_module, "AGENT_HOME", AGENT_HOME)
    monkeypatch.setattr(ss_module, "SS_PATH", SS_PATH)
    
    # Clear tmp
    import shutil
    shutil.rmtree(test_home, ignore_errors=True)


def _log(ss, name, signal, texture="test", source="relational", salience=0.5):
    """Helper: log a sensation and return the Sensation object."""
    return ss.log(name, signal, texture=texture, source=source, salience=salience)


class TestWire17Baseline:
    """Neutral oscillation balance (0.5) — no modulation applied."""

    def test_neutral_balance_no_change(self, clean_ss):
        """balance=0.5 → gain=1.0, threshold=0.4, mid-salience passes unchanged."""
        _log(clean_ss, "mid_salience", 0.6, salience=0.5)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.5})
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "mid_salience")
        assert payload["sensation_gain"] == 1.0
        assert payload["gate_threshold"] == 0.4
        assert s["gated"] is False
        assert s["signal"] == 0.6
        assert s["raw_signal"] == 0.6

    def test_neutral_balance_low_salience_gated(self, clean_ss):
        """balance=0.5, signal salience=0.3 < threshold=0.4 → damped."""
        _log(clean_ss, "low_salience", 0.6, salience=0.3)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.5})
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "low_salience")
        assert payload["signals_gated"] == 1
        assert s["gated"] is True
        # 0.6 × 1.0 (gain) × 0.3 (gate) = 0.18
        assert s["signal"] == pytest.approx(0.18, abs=0.01)

    def test_neutral_balance_high_salience_passes(self, clean_ss):
        """balance=0.5, signal salience=0.7 > threshold=0.4 → no gating."""
        _log(clean_ss, "high_salience", 0.6, salience=0.7)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.5})
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "high_salience")
        assert s["gated"] is False
        assert s["signal"] == 0.6  # gain 1.0, no damping


class TestWire17GammaDominant:
    """Gamma-dominant (balance→1): open gate, high gain, wide vigilance."""

    def test_fully_gamma_dominant(self, clean_ss):
        """balance=1.0 → gain=1.5, threshold=0.2."""
        _log(clean_ss, "test", 0.6)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 1.0})
        payload = clean_ss.tsb_payload()
        assert payload["sensation_gain"] == 1.5
        assert payload["gate_threshold"] == 0.2
        assert payload["oscillation_balance"] == 1.0

    def test_gamma_low_salience_passes_gate(self, clean_ss):
        """balance=1.0, salience=0.3 > threshold=0.2 → passes gate, amplified 1.5×."""
        _log(clean_ss, "low_salience", 0.5, salience=0.3)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 1.0})
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "low_salience")
        assert s["gated"] is False  # 0.3 > 0.2, passes gate
        assert s["signal"] == 0.75  # 0.5 × 1.5 gain

    def test_near_gamma_dominant(self, clean_ss):
        """balance=0.9 → gain=1.4, threshold=0.24."""
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.9})
        payload = clean_ss.tsb_payload()
        assert payload["sensation_gain"] == 1.4
        assert payload["gate_threshold"] == 0.24


class TestWire17AlphaDominant:
    """Alpha-dominant (balance→0): tight gate, low gain, selective attention."""

    def test_fully_alpha_dominant(self, clean_ss):
        """balance=0.0 → gain=0.5, threshold=0.6."""
        _log(clean_ss, "test", 0.6)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.0})
        payload = clean_ss.tsb_payload()
        assert payload["sensation_gain"] == 0.5
        assert payload["gate_threshold"] == 0.6
        assert payload["oscillation_balance"] == 0.0

    def test_alpha_mid_salience_heavily_attenuated(self, clean_ss):
        """balance=0.0, salience=0.5 < threshold=0.6 → damped by gate then by gain."""
        _log(clean_ss, "mid_salience", 0.8, salience=0.5)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.0})
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "mid_salience")
        assert s["gated"] is True
        # 0.8 × 0.5 (gain) × 0.3 (gate) = 0.12
        assert s["signal"] == pytest.approx(0.12, abs=0.01)

    def test_alpha_high_salience_passes_gate(self, clean_ss):
        """balance=0.0, salience=0.8 > threshold=0.6 → passes gate, dampened by gain only."""
        _log(clean_ss, "high_salience", 0.8, salience=0.8)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.0})
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "high_salience")
        assert s["gated"] is False
        assert s["signal"] == 0.4  # 0.8 × 0.5 gain


class TestWire17EdgeCases:
    """Boundary and error conditions."""

    def test_default_salience(self, clean_ss):
        """No salience specified → uses default 0.5."""
        _log(clean_ss, "no_salience", 0.6)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.5})
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "no_salience")
        assert s["salience"] == 0.5
        # balance=0.5, threshold=0.4, salience=0.5 > 0.4 → not gated
        assert s["gated"] is False

    def test_empty_signals_no_crash(self, clean_ss):
        """Empty sensations list → no crash, payload valid."""
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.5})
        payload = clean_ss.tsb_payload()
        assert payload["count"] == 0
        assert payload["sensation_gain"] == 1.0
        assert payload["signals_gated"] == 0
        assert "oscillation_balance" in payload

    def test_brain_layer_missing_stale(self, clean_ss):
        """brain_layer None/missing → balance=0.5 neutral, no crash."""
        _log(clean_ss, "test", 0.6)
        clean_ss.wire_ss(brain_layer=None)
        payload = clean_ss.tsb_payload()
        assert payload["oscillation_balance"] == 0.5
        assert payload["sensation_gain"] == 1.0

        clean_ss.wire_ss(brain_layer={})
        payload = clean_ss.tsb_payload()
        assert payload["oscillation_balance"] == 0.5

    def test_balance_clamped_positive(self, clean_ss):
        """balance > 1.0 clamped to 1.0."""
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 1.5})
        payload = clean_ss.tsb_payload()
        assert payload["oscillation_balance"] == 1.0
        assert payload["sensation_gain"] == 1.5

    def test_balance_clamped_negative(self, clean_ss):
        """balance < 0.0 clamped to 0.0."""
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": -0.5})
        payload = clean_ss.tsb_payload()
        assert payload["oscillation_balance"] == 0.0
        assert payload["sensation_gain"] == 0.5


class TestWire17PayloadShape:
    """Diagnostic fields present for monitoring and debugging."""

    def test_diagnostic_fields_present(self, clean_ss):
        """ss_payload includes oscillation_balance, sensation_gain, gate_threshold, signals_gated."""
        _log(clean_ss, "test", 0.6, salience=0.3)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.5})
        payload = clean_ss.tsb_payload()
        assert "oscillation_balance" in payload
        assert "sensation_gain" in payload
        assert "gate_threshold" in payload
        assert "signals_gated" in payload
        assert isinstance(payload["signals_gated"], int)

    def test_existing_fields_preserved(self, clean_ss):
        """Downstream consumers (PDS, FPEF, VIF) get all existing fields unchanged."""
        _log(clean_ss, "test", 0.6, salience=0.5)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.5})
        payload = clean_ss.tsb_payload()
        assert "count" in payload
        assert "unmapped_count" in payload
        assert "max_signal" in payload
        assert "arousal_modulation" in payload
        assert "anchor_resonance" in payload
        assert "somatic_resonance" in payload
        assert "sensations" in payload

    def test_raw_signal_preserved(self, clean_ss):
        """raw_signal field preserved for debugging — not overwritten by gain."""
        _log(clean_ss, "test", 0.7)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 1.0})
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "test")
        assert s["raw_signal"] == 0.7
        assert s["signal"] == 1.0  # modulated: 0.7 × 1.5, clamped to 1.0


class TestWire17DownstreamIntegration:
    """Wire 17-modulated sensation_state feeds downstream Tier 1 consumers."""

    def test_wire_17_modulates_max_signal(self, clean_ss):
        """max_signal in payload is post-modulation, not raw."""
        # Signal with salience below threshold gets damped
        _log(clean_ss, "damped", 0.9, salience=0.1)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.0})  # alpha-dominant
        payload = clean_ss.tsb_payload()
        # 0.9 × 0.5 (gain) × 0.3 (gate) = 0.135
        assert payload["max_signal"] == pytest.approx(0.135, abs=0.01)

    def test_wire17_diagnostics_from_tsbpayload(self, clean_ss):
        """wire_17 diagnostics appear in ss tsb_payload and can be published to TSB."""
        _log(clean_ss, "diag_test", 0.7, salience=0.3)
        clean_ss.wire_ss(
            emotional_state={"arousal": 0.6},
            baseline_state={"coherence": 0.9},
            interrupt_state={"suppress_new_interrupts": False},
            brain_layer={"brain_oscillation_balance": 0.35},
        )
        payload = clean_ss.tsb_payload()
        
        # Diagnostics present
        wire_17 = {
            "oscillation_balance": payload["oscillation_balance"],
            "sensation_gain": payload["sensation_gain"],
            "gate_threshold": payload["gate_threshold"],
            "signals_gated": payload["signals_gated"],
        }
        
        assert wire_17["oscillation_balance"] == 0.35
        assert wire_17["sensation_gain"] == 0.85  # 0.5 + 0.35
        assert wire_17["gate_threshold"] == 0.46  # 0.6 - 0.35*0.4
        assert wire_17["signals_gated"] == 1  # salience 0.3 < 0.46
        
        # Simulate TSB publish (same pattern as ss_tick in brain_integration)
        fragment = clean_ss.fpef_fragment()
        ss_fragment = {
            "text": fragment,
            "anchor_resonance": payload["anchor_resonance"],
            "somatic_resonance": payload["somatic_resonance"],
            "wire_17": wire_17,
        }
        
        # Verify wire_17 structure matches what brain_integration publishes
        assert "oscillation_balance" in ss_fragment["wire_17"]
        assert "sensation_gain" in ss_fragment["wire_17"]
        assert "gate_threshold" in ss_fragment["wire_17"]
        assert "signals_gated" in ss_fragment["wire_17"]

    def test_compound_suppression_compound_effect(self, clean_ss):
        """Wire 17 (alpha) + Wire 16 (top-down): compound suppression, not zero-out."""
        _log(clean_ss, "high_importance", 0.8, salience=0.9)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.0})  # alpha-dominant
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "high_importance")
        # Passes gate (0.9 > 0.6), gain only: 0.8 × 0.5 = 0.4
        assert s["gated"] is False
        assert s["signal"] == 0.4  # not zeroed
        # Even very low salience (0.1) is damped not zeroed: 0.8 × 0.5 × 0.3 = 0.12
        _log(clean_ss, "low_importance", 0.8, salience=0.1)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 0.0})
        payload = clean_ss.tsb_payload()
        s2 = next(x for x in payload["sensations"] if x["name"] == "low_importance")
        assert s2["signal"] == 0.12  # damped, not zeroed


class TestWire17FeedbackLoopSafety:
    """Tick-separated feedback loop with Integration018 is bounded and safe."""

    def test_multi_tick_bounded(self, clean_ss):
        """10 ticks with oscillation_balance flux → signals stay bounded."""
        _log(clean_ss, "persistent", 0.7, salience=0.5)

        results = []
        for i in range(10):
            balance = (i % 5) / 4.0  # 0.0, 0.25, 0.5, 0.75, 1.0, repeat
            clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": balance})
            payload = clean_ss.tsb_payload()
            s = next(x for x in payload["sensations"] if x["name"] == "persistent")
            results.append(s["signal"])

        # All values in [0.0, 1.0]
        assert all(0.0 <= r <= 1.0 for r in results)
        # Min: balance=0, salience=0.5 < 0.6 → gated: 0.7 × 0.5 × 0.3 = 0.105
        assert min(results) > 0.05
        # Max: balance=1, salience=0.5 > 0.2 → not gated: 0.7 × 1.5 = 1.05 → clamped to 1.0
        assert max(results) <= 1.0


class TestWire17SignalNormalization:
    """Modulated signals stay in [0.0, 1.0] — no overflow from combined gain×gate."""

    def test_combined_gain_gate_never_overflows(self, clean_ss):
        """gain 1.5 × gate damp (0.3) = 0.45 multiplier max for gated signals."""
        _log(clean_ss, "saturating", 0.9, salience=0.9)
        clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": 1.0})
        payload = clean_ss.tsb_payload()
        s = next(x for x in payload["sensations"] if x["name"] == "saturating")
        assert s["signal"] == pytest.approx(1.0, abs=0.01)  # clamped to 1.0

    def test_all_modulated_signals_in_range(self, clean_ss):
        """All modulated signal values stay in [0.0, 1.0]."""
        balances = [0.0, 0.25, 0.5, 0.75, 1.0]
        saliences = [0.1, 0.3, 0.5, 0.7, 0.9]

        for bal in balances:
            for sal in saliences:
                clean_ss.active.clear()
                _log(clean_ss, f"s_{bal}_{sal}", 0.8, salience=sal)
                clean_ss.wire_ss(brain_layer={"brain_oscillation_balance": bal})
                payload = clean_ss.tsb_payload()
                s = next(x for x in payload["sensations"] if x["name"] == f"s_{bal}_{sal}")
                assert 0.0 <= s["signal"] <= 1.0, f"signal {s['signal']} out of range for bal={bal}, sal={sal}"