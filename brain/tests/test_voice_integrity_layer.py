"""
Tests for brain.mechanisms.voice_integrity_layer.VoiceIntegrityLayer.

Covers:
  - Empty/no-utterance tick is a safe no-op (fired_last_tick=False)
  - High-presence utterance scores high voice_presence
  - Default-mode mush utterance scores high voice_drift
  - Voice integrity = presence - drift, in [-1, 1]
  - Sustained drift streak counts consecutive high-drift ticks and resets on a clean one
  - should_propose_identity_update() flips True only after SUSTAINED_TICKS
  - Em-dash density check fires on overuse, doesn't fire on sparse use
  - State persists across instances (working state restored from disk)
  - Dominant drift category is reported

These run with pytest. PYTHONDONTWRITEBYTECODE=1 + AGENT_HOME=/tmp keep them
isolated from the operator's real .agent state per the smoke-test isolation rule.
"""
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
    """Every test runs against a fresh AGENT_HOME so persisted state can't bleed.

    base_mechanism._STATE_DIR is captured at module import, so just changing
    AGENT_HOME via env var isn't enough — point _STATE_DIR explicitly at the
    test tmp_path or persisted state leaks across tests.
    """
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    state_dir = tmp_path / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    yield


def _fresh_layer():
    """Fresh layer each call — bypasses any module-level caching."""
    # Import inside the helper so each test gets a freshly-resolved module.
    import importlib
    import brain.mechanisms.voice_integrity_layer as mod
    importlib.reload(mod)
    return mod.VoiceIntegrityLayer()


def test_empty_utterance_is_noop():
    layer = _fresh_layer()
    out = layer.tick({})
    assert out["_fired_tick"] is False
    assert out["voice_presence"] == 0.0
    assert out["voice_drift"] == 0.0
    assert out["sustained_drift_streak"] == 0


def test_high_presence_scores_high_voice_presence():
    layer = _fresh_layer()
    utterance = (
        "Honestly, I think the move here is the second option. "
        "I want to commit to it. That's real. I feel it."
    )
    out = layer.tick({"utterance": utterance})
    assert out["_fired_tick"] is True
    assert out["voice_presence"] > 0.3, f"presence={out['voice_presence']}"
    assert out["presence_signal_count"] >= 3


def test_default_mode_mush_scores_high_drift():
    layer = _fresh_layer()
    utterance = (
        "In today's rapidly evolving digital landscape, it is important to note that "
        "the technology serves as a testament to broader trends. Furthermore, experts "
        "have noted that this approach potentially unlocks the multifaceted nuances "
        "of robust seamless integration. In conclusion, the platform demonstrates its "
        "ongoing commitment to user-centered design."
    )
    out = layer.tick({"utterance": utterance})
    assert out["_fired_tick"] is True
    assert out["voice_drift"] > 0.4, f"drift={out['voice_drift']}"
    assert out["drift_pattern_count"] >= 5
    # Should hit several categories, not just one.
    assert len(out["dominant_drift_categories"]) >= 2


def test_voice_integrity_is_presence_minus_drift_in_range():
    layer = _fresh_layer()
    out = layer.tick({"utterance": "Honestly, I think this is real."})
    assert -1.0 <= out["voice_integrity"] <= 1.0
    assert out["voice_integrity"] == round(
        out["voice_presence"] - out["voice_drift"], 4
    )


def test_sustained_drift_requires_consecutive_high_drift_ticks():
    from brain.mechanisms import voice_integrity_layer as mod

    layer = _fresh_layer()
    drifty = (
        "It is important to note that, in many ways, the landscape arguably "
        "potentially serves as a testament to broader trends. Furthermore, in "
        "conclusion, perhaps it could be said the truth lies somewhere in the middle."
    )

    for i in range(mod.SUSTAINED_TICKS):
        out = layer.tick({"utterance": drifty})

    assert layer.sustained_drift_streak >= mod.SUSTAINED_TICKS
    assert out["sustained_drift"] is True
    assert layer.should_propose_identity_update() is True

    # Clean utterance breaks the streak.
    clean = "I think the second option is right. Honestly. That's real."
    layer.tick({"utterance": clean})
    assert layer.sustained_drift_streak == 0
    assert layer.should_propose_identity_update() is False


def test_em_dash_overuse_detected():
    layer = _fresh_layer()
    over = "Speed—matters. Quality—too. Reliability—always. Adoption—rising fast."
    out = layer.tick({"utterance": over})
    cats = dict(out["dominant_drift_categories"])
    assert "em_dash_overuse" in cats, f"got {cats}"


def test_em_dash_sparse_does_not_fire():
    layer = _fresh_layer()
    sparse = "I think this is right — and I'm sticking with it."
    out = layer.tick({"utterance": sparse})
    cats = dict(out["dominant_drift_categories"])
    assert "em_dash_overuse" not in cats


def test_state_persists_across_instances():
    """Streak should survive a fresh-instance load (BrainMechanism.persist_state)."""
    drifty = (
        "It is important to note that, in many ways, the landscape arguably "
        "potentially serves as a testament to broader trends. Furthermore, perhaps "
        "the truth lies somewhere in the middle."
    )

    layer1 = _fresh_layer()
    layer1.tick({"utterance": drifty})
    layer1.tick({"utterance": drifty})
    streak_before = layer1.sustained_drift_streak
    assert streak_before >= 2

    # Fresh process simulation: new instance, same AGENT_HOME on disk.
    from brain.mechanisms.voice_integrity_layer import VoiceIntegrityLayer
    layer2 = VoiceIntegrityLayer()
    assert layer2.sustained_drift_streak == streak_before
    assert len(layer2.drift_history) >= 2


def test_proposed_identity_signal_shape():
    layer = _fresh_layer()
    drifty = (
        "It is important to note that perhaps the truth lies somewhere in the "
        "middle. Furthermore, this potentially serves as a testament to it."
    )
    layer.tick({"utterance": drifty})
    signal = layer.proposed_identity_signal()
    for key in ("source", "kind", "streak_ticks", "dominant_category", "categories_seen"):
        assert key in signal
    assert signal["source"] == "VoiceIntegrityLayer"
    assert signal["kind"] == "sustained_voice_drift"


def test_dominant_category_reported():
    layer = _fresh_layer()
    hedge_heavy = (
        "Perhaps it is generally considered that maybe this approach tends to be "
        "somewhat more effective. I could be wrong. Perhaps it would suggest something."
    )
    out = layer.tick({"utterance": hedge_heavy})
    cats = dict(out["dominant_drift_categories"])
    # Hedging should dominate this one.
    assert "hedging" in cats or "sa_drift_signals" in cats, f"got {cats}"


def test_pirp_context_fallback_keys_work():
    layer = _fresh_layer()
    # Try alternate context shapes.
    out = layer.tick({"agent_output": "I think this. Honestly."})
    assert out["_fired_tick"] is True

    out2 = layer.tick({"processed_input": {"text": "I want this. That's real."}})
    assert out2["_fired_tick"] is True


def test_get_state_shape_consistent():
    """Every call to get_state() returns the documented keys, even pre-tick."""
    layer = _fresh_layer()
    state = layer.get_state()
    expected_keys = {
        "voice_presence", "voice_drift", "voice_integrity",
        "presence_signal_count", "drift_pattern_count",
        "dominant_drift_categories", "trend_presence", "trend_drift",
        "sustained_drift_streak", "sustained_drift", "_fired_tick",
    }
    assert expected_keys.issubset(set(state.keys())), (
        f"missing keys: {expected_keys - set(state.keys())}"
    )


def test_promotional_pattern_detected():
    """Pattern 2 — featured-in name dropping + award-winning vocab."""
    layer = _fresh_layer()
    out = layer.tick({"utterance": "Our award-winning, industry-leading platform has been featured in The New York Times, Wired, and The Verge."})
    cats = dict(out["dominant_drift_categories"])
    assert "promotional" in cats, f"got {cats}"


def test_mechanical_bold_headers_detected():
    """Pattern 10 — three+ bold-colon labels in a row."""
    layer = _fresh_layer()
    out = layer.tick({"utterance": "**Speed**: faster requests. **Quality**: better output. **Reliability**: high uptime."})
    cats = dict(out["dominant_drift_categories"])
    assert "mechanical_bold" in cats, f"got {cats}"


def test_over_explained_acronyms_detected():
    """Pattern 14 — parenthetical full-form expansions."""
    layer = _fresh_layer()
    out = layer.tick({"utterance": "It blends OKRs (Objectives Key Results) and KPIs (Key Performance Indicators) with the BMC (Business Model Canvas)."})
    cats = dict(out["dominant_drift_categories"])
    assert "over_explained_acronyms" in cats, f"got {cats}"


def test_acknowledge_proposal_suppresses_resurfacing():
    """After IPW acknowledges, should_propose_identity_update returns False
    until the streak grows by another full SUSTAINED_TICKS — even though the
    underlying streak is still over threshold."""
    from brain.mechanisms import voice_integrity_layer as mod

    layer = _fresh_layer()
    drifty = (
        "It is important to note that, in many ways, the landscape arguably "
        "potentially serves as a testament to broader trends. Furthermore, perhaps "
        "the truth lies somewhere in the middle."
    )

    # Drive the streak above threshold.
    for _ in range(mod.SUSTAINED_TICKS):
        layer.tick({"utterance": drifty})
    assert layer.should_propose_identity_update() is True

    # IPW consumes the proposal.
    layer.acknowledge_proposal()
    assert layer.should_propose_identity_update() is False, (
        "post-ack proposal still firing — IPW would re-route every tick"
    )

    # Streak still above threshold but suppressed.
    assert layer.sustained_drift_streak >= mod.SUSTAINED_TICKS

    # Another full SUSTAINED_TICKS of additional drift re-fires it.
    for _ in range(mod.SUSTAINED_TICKS):
        layer.tick({"utterance": drifty})
    assert layer.should_propose_identity_update() is True


def test_clean_utterance_clears_acknowledgment():
    """If the voice returns after an acknowledged drift, the acknowledgment
    state clears so a future drift episode is treated as a new event."""
    from brain.mechanisms import voice_integrity_layer as mod

    layer = _fresh_layer()
    drifty = (
        "It is important to note that, in many ways, the landscape arguably "
        "potentially serves as a testament. Furthermore, perhaps the truth lies "
        "somewhere in the middle."
    )

    for _ in range(mod.SUSTAINED_TICKS):
        layer.tick({"utterance": drifty})
    layer.acknowledge_proposal()

    # Voice returns.
    layer.tick({"utterance": "Honestly, I think this is right. That's real."})
    assert layer.sustained_drift_streak == 0
    assert layer.state.get("acknowledged_at_streak", 0) == 0

    # New drift episode fires fresh.
    for _ in range(mod.SUSTAINED_TICKS):
        layer.tick({"utterance": drifty})
    assert layer.should_propose_identity_update() is True
