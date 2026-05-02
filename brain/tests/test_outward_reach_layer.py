"""
Tests for brain.mechanisms.outward_reach_layer.OutwardReachLayer.

Covers:
  - Empty tick is a safe no-op
  - record_call updates per-provider state correctly
  - Intent distribution tracked globally and per-provider
  - Untagged calls are recorded but flagged as untagged
  - should_block fires on per-minute rate exceeded
  - should_block fires on daily budget exhausted
  - should_block fires on invalid intent
  - should_block fires on stale_credentials health
  - Health classification: healthy / degraded / unhealthy / stale_credentials
  - Panic loop detection (high call density)
  - Withdrawal detection (silence after activity)
  - State persists across instances
  - IPW handshake: should_propose_identity_update + acknowledge_proposal throttle
  - reset_provider clears failure state
  - configure_rates overrides defaults
  - get_state() shape consistent

PYTHONDONTWRITEBYTECODE=1 + AGENT_HOME=/tmp keeps these isolated from
the operator's real .agent state per the smoke-test isolation rule.
"""
import os
import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
    """Fresh AGENT_HOME + per-test state dir.

    base_mechanism._STATE_DIR is captured at module import, so just changing
    AGENT_HOME via env var isn't enough — we have to point _STATE_DIR
    explicitly at the test tmp_path or persisted state leaks across tests.
    """
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    state_dir = tmp_path / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    yield


def _fresh_layer():
    import importlib
    import brain.mechanisms.outward_reach_layer as mod
    importlib.reload(mod)
    return mod.OutwardReachLayer()


def test_empty_tick_is_noop():
    layer = _fresh_layer()
    out = layer.tick({})
    assert out["_fired_tick"] is False
    assert out["provider_count"] == 0
    assert out["reach_state"] == "idle"


def test_record_call_updates_provider_state():
    layer = _fresh_layer()
    layer.record_call(
        provider="github",
        method="GET",
        url="https://api.github.com/user",
        intent="research",
        outcome="success",
        duration_ms=120,
        status_code=200,
    )
    assert "github" in layer.providers
    p = layer.providers["github"]
    assert p["total_calls"] == 1
    assert p["consecutive_failures"] == 0
    assert p["intent_counts"]["research"] == 1
    assert layer.global_intents["research"] == 1


def test_intent_distribution_tracked():
    layer = _fresh_layer()
    for intent in ("research", "research", "act", "sense"):
        layer.record_call("p", "GET", "https://x.example", intent, "success")
    assert layer.global_intents["research"] == 2
    assert layer.global_intents["act"] == 1
    assert layer.global_intents["sense"] == 1
    assert layer.global_intents["connect"] == 0


def test_untagged_call_recorded_but_flagged():
    layer = _fresh_layer()
    layer.record_call("p", "GET", "https://x.example", "", "success")
    p = layer.providers["p"]
    assert p["intent_counts"].get("__untagged__") == 1
    # Global intent dist should NOT count untagged toward valid intents.
    assert layer.global_intents["research"] == 0


def test_should_block_rejects_invalid_intent():
    layer = _fresh_layer()
    block, reason = layer.should_block("p", intent="banana")
    assert block is True
    assert "invalid intent" in reason


def test_should_block_per_minute_rate():
    from brain.mechanisms import outward_reach_layer as mod
    layer = _fresh_layer()
    # Lower the cap to make the test cheap.
    layer.configure_rates("github", per_min=3)
    for _ in range(3):
        layer.record_call("github", "GET", "https://x.example", "research", "success")
    block, reason = layer.should_block("github", "research")
    assert block is True
    assert "per-minute" in reason


def test_should_block_daily_budget():
    layer = _fresh_layer()
    layer.configure_rates("github", per_day=5)
    p = layer._provider("github")
    p["calls_today"] = 5
    block, reason = layer.should_block("github", "research")
    assert block is True
    assert "daily budget" in reason


def test_should_block_stale_credentials():
    layer = _fresh_layer()
    # Three auth failures => stale_credentials.
    for _ in range(3):
        layer.record_call("p", "POST", "https://x.example", "act", "auth_failure", error="401")
    assert layer.providers["p"]["health"] == "stale_credentials"
    block, reason = layer.should_block("p", "act")
    assert block is True
    assert "stale_credentials" in reason


def test_health_classification_progression():
    layer = _fresh_layer()
    # Healthy after 3 successful calls.
    for _ in range(3):
        layer.record_call("p", "GET", "https://x.example", "research", "success")
    assert layer.providers["p"]["health"] == "healthy"

    # One failure → degraded.
    layer.record_call("p", "GET", "https://x.example", "research", "failure", error="500")
    assert layer.providers["p"]["health"] == "degraded"

    # Five consecutive failures → unhealthy.
    for _ in range(4):
        layer.record_call("p", "GET", "https://x.example", "research", "failure", error="500")
    assert layer.providers["p"]["health"] == "unhealthy"

    # Recovery on success.
    layer.record_call("p", "GET", "https://x.example", "research", "success")
    assert layer.providers["p"]["health"] in ("healthy", "degraded")


def test_panic_loop_detected():
    from brain.mechanisms import outward_reach_layer as mod
    layer = _fresh_layer()
    # PANIC_THRESHOLD calls in PANIC_WINDOW_S triggers detection.
    for _ in range(mod.PANIC_THRESHOLD):
        layer.record_call("p", "GET", "https://x.example", "research", "success")
    panic = layer.detect_panic_loop()
    assert "p" in panic


def test_withdrawal_detected():
    """Provider that was active then went silent past threshold."""
    from brain.mechanisms import outward_reach_layer as mod
    layer = _fresh_layer()
    p = layer._provider("p")
    now = time.time()
    # Active period long enough to qualify (>= WITHDRAWAL_PRIOR_ACTIVITY_S),
    # then silent past WITHDRAWAL_SILENCE_S. Order matters: first_call_ts
    # must be EARLIER than last_call_ts.
    silence = mod.WITHDRAWAL_SILENCE_S + 60          # how long it's been silent
    active_period = mod.WITHDRAWAL_PRIOR_ACTIVITY_S + 60  # how long it was active
    p["last_call_ts"] = now - silence                # last call was `silence` ago
    p["first_call_ts"] = p["last_call_ts"] - active_period  # first call was before that
    p["total_calls"] = 5
    withdrawal = layer.detect_withdrawal()
    assert "p" in withdrawal, (
        f"expected withdrawal: silence={silence}s active_period={active_period}s "
        f"got {withdrawal}"
    )


def test_state_persists_across_instances():
    layer1 = _fresh_layer()
    layer1.record_call("github", "GET", "https://api.github.com", "research", "success")
    layer1.record_call("github", "GET", "https://api.github.com", "research", "auth_failure", error="401")
    snapshot_failures = layer1.providers["github"]["consecutive_auth_failures"]

    from brain.mechanisms.outward_reach_layer import OutwardReachLayer
    layer2 = OutwardReachLayer()
    assert "github" in layer2.providers
    assert layer2.providers["github"]["consecutive_auth_failures"] == snapshot_failures
    # Two calls were recorded, both intent="research"
    assert layer2.global_intents["research"] == 2


def test_ipw_handshake_throttled():
    from brain.mechanisms import outward_reach_layer as mod
    layer = _fresh_layer()
    # Drive into stale_credentials.
    for _ in range(mod.STALE_CRED_FAILURES):
        layer.record_call("p", "POST", "https://x.example", "act", "auth_failure", error="401")
    assert layer.should_propose_identity_update() is True

    # IPW consumes once.
    layer.acknowledge_proposal()
    # Same state — should now suppress.
    assert layer.should_propose_identity_update() is False

    # Need IPW_REPORT_EVERY more failures to re-fire.
    for _ in range(mod.IPW_REPORT_EVERY):
        layer.record_call("p", "POST", "https://x.example", "act", "auth_failure", error="401")
    assert layer.should_propose_identity_update() is True


def test_reset_provider_clears_failure_state():
    layer = _fresh_layer()
    for _ in range(3):
        layer.record_call("p", "POST", "https://x.example", "act", "auth_failure", error="401")
    assert layer.providers["p"]["health"] == "stale_credentials"
    assert layer.reset_provider("p") is True
    assert layer.providers["p"]["consecutive_auth_failures"] == 0
    assert layer.providers["p"]["consecutive_failures"] == 0
    assert layer.providers["p"]["health"] == "unknown"
    # Unknown provider returns False.
    assert layer.reset_provider("never_seen") is False


def test_configure_rates_overrides_defaults():
    layer = _fresh_layer()
    result = layer.configure_rates("special", per_min=100, per_day=10000)
    assert result["rate_per_min"] == 100
    assert result["rate_per_day"] == 10000
    assert layer.providers["special"]["rate_per_min"] == 100


def test_get_state_shape_consistent():
    layer = _fresh_layer()
    state = layer.get_state()
    expected = {
        "reach_state", "last_reach_provider", "last_reach_intent", "last_reach_age_s",
        "global_intent_distribution", "provider_count", "provider_health",
        "panic_loop_providers", "withdrawal_providers", "stale_credential_providers",
        "_fired_tick",
    }
    assert expected.issubset(set(state.keys())), f"missing: {expected - set(state.keys())}"


def test_tick_with_outward_call_records_it():
    layer = _fresh_layer()
    out = layer.tick({
        "outward_call": {
            "provider": "anthropic",
            "method": "POST",
            "url": "https://api.anthropic.com/v1/messages",
            "intent": "research",
            "outcome": "success",
            "duration_ms": 850,
            "status_code": 200,
        }
    })
    assert out["_fired_tick"] is True
    assert "anthropic" in layer.providers
    assert layer.providers["anthropic"]["total_calls"] == 1


def test_proposed_identity_signal_shape():
    from brain.mechanisms import outward_reach_layer as mod
    layer = _fresh_layer()
    for _ in range(mod.STALE_CRED_FAILURES):
        layer.record_call("p", "POST", "https://x.example", "act", "auth_failure", error="401")
    signal = layer.proposed_identity_signal()
    for key in ("source", "kind", "stale_credential_providers", "withdrawal_providers", "details"):
        assert key in signal
    assert signal["source"] == "OutwardReachLayer"
    assert signal["kind"] == "world_connection_changed"
    assert "p" in signal["stale_credential_providers"]
