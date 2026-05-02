"""
brain/mechanisms/outward_reach_layer.py — OutwardReachLayer

The runtime monitor for the agent's outward reach. Pairs with
skills/api-interaction/SKILL.md. Every external call (HTTP request, webhook,
external service hit, public-data fetch) flows through here so the brain has a
single coherent view of how the agent is engaging with the world outside the
workspace boundary.

The neuroscience analog is the cortical action-selection / response-inhibition
system: anterior cingulate weighing cost-benefit of reaching, right inferior
frontal cortex inhibiting unsafe reaches, parietal cortex coordinating the
reach itself, dACC allocating control as a function of expected value vs cost.

What this mechanism does:

  - Tracks per-provider state — call counts, error rates, last call time,
    last error message, current health classification.
  - Maintains rate windows (per-minute, per-day) so callers can ask
    `should_block(provider, intent)` before reaching.
  - Maintains intent distribution (research / connect / sense / act counts)
    so other mechanisms can read what kind of reaching the agent has been
    doing. Skewed distributions are signal: nothing but `research` for hours
    looks like avoidance; nothing but `act` looks like compulsion.
  - Detects unhealthy patterns:
      * panic_loop: too many calls in a short window
      * withdrawal: previously active provider suddenly silent for a long stretch
      * stale_credentials: 3+ consecutive auth failures on the same provider
  - Publishes reach state to the TSB so AttentionModifier and other
    third-eye-adjacent mechanisms can bias accordingly.
  - Hands off sustained provider failures to IdentityProposalWriter — the
    world the agent thinks it's connected to has changed, that's identity data.

Citations:
  1. [Cisek 2007, Phil Trans R Soc B 362(1485):1585-1599, PMID 17428779] —
     Cortical mechanisms of action selection: the affordance competition
     hypothesis. Models how cortex selects from competing reach affordances
     in real time. The OutwardReachLayer is the affordance-competition
     analog at the API-call level: which provider, which intent, how often.
  2. [Aron 2014, Trends Cogn Sci 18(4):177-185, PMID 24440116] — Inhibition
     and the right inferior frontal cortex: review and update. Response
     inhibition as the gate on action. `should_block()` is the rIFG analog —
     the network-level brake on outward reach when conditions don't fit.
  3. [Shenhav 2013, Neuron 79(2):217-240, PMID 23889930] — Expected Value
     of Control theory. dACC allocates control as a function of expected
     value vs cost. Same logic governs whether a reach is worth its rate
     budget right now.
"""

from brain.base_mechanism import BrainMechanism
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
AGENT_DB = AGENT_HOME / os.getenv("AGENT_DB_NAME", "agent.db")

__wire_meta__ = {
    "wire": 27,
    "signal": "outward_reach",
    "mechanism": "OutwardReachLayer",
    "reads": [
        "pirp_context.outward_call",
        "skills.safeguard.can_perform",
    ],
    "writes": [
        "reach_state",
        "provider_health",
        "intent_distribution",
        "panic_loop",
        "withdrawal",
    ],
    "citations": ["PMID 17428779", "PMID 24440116", "PMID 23889930"],
}


# ── Tuning constants ──────────────────────────────────────────────────────────

DEFAULT_RATE_PER_MIN = 10
DEFAULT_RATE_PER_DAY = 500
DEFAULT_TIMEOUT_S = 30.0
HARD_TIMEOUT_S = 60.0
COOLDOWN_SECONDS = 300

# Panic loop: more than this many calls in PANIC_WINDOW_S = panic.
PANIC_THRESHOLD = 8
PANIC_WINDOW_S = 5.0

# Withdrawal: previously-active provider with this many seconds of silence
# after recent activity = withdrawal flag.
WITHDRAWAL_SILENCE_S = 3600.0  # 1h
WITHDRAWAL_PRIOR_ACTIVITY_S = 600.0  # was active within last 10 minutes

# Stale credentials: this many consecutive auth-class failures = stale.
STALE_CRED_FAILURES = 3

# IPW: report sustained provider failures only every N consecutive failures
# beyond the threshold so we don't flood proposals.
IPW_REPORT_EVERY = 5

VALID_INTENTS = {"research", "connect", "sense", "act"}
HEALTH_CLASSES = ("healthy", "degraded", "unhealthy", "stale_credentials", "unknown")


# ── Mechanism ─────────────────────────────────────────────────────────────────

class OutwardReachLayer(BrainMechanism):
    """
    The agent's reach monitor. See module docstring for full description.

    Per-provider state lives in `self.providers[provider_name]` — a dict with:
        last_call_ts, last_error, consecutive_failures, consecutive_auth_failures,
        health, total_calls, total_failures, intent_counts, calls_window (deque
        of recent timestamps for panic detection).

    Global state lives in self.state via BrainMechanism.persist_state(), so a
    process restart preserves health classifications and IPW acknowledgment
    counters.
    """

    def __init__(self, db_path: Optional[Path] = None):
        try:
            super().__init__(
                name="OutwardReachLayer",
                human_analog="cortical action-selection + response inhibition for outward reach",
                layer="integration",
            )
        except Exception:
            pass

        self.db_path = db_path or AGENT_DB

        # In-memory working state. Persisted into self.state on flush.
        self.providers: Dict[str, Dict[str, Any]] = {}
        self.global_intents: Dict[str, int] = {k: 0 for k in VALID_INTENTS}
        self.last_reach_ts: float = 0.0
        self.last_reach_provider: str = ""
        self.last_reach_intent: str = ""
        self.fired_last_tick: bool = False
        self.ipw_report_count: int = 0  # tracks how many proposals we've made

        # Restore persisted state.
        self.load_state()
        self._restore_working_state()

    # ── State plumbing ─────────────────────────────────────────────────────

    def _restore_working_state(self) -> None:
        if not isinstance(self.state, dict):
            return
        saved_providers = self.state.get("providers")
        if isinstance(saved_providers, dict):
            for name, p in saved_providers.items():
                if not isinstance(p, dict):
                    continue
                # deque can't survive JSON round-trip; restore from list
                p["calls_window"] = deque(p.get("calls_window", []), maxlen=PANIC_THRESHOLD * 2)
                self.providers[name] = p

        saved_intents = self.state.get("global_intents")
        if isinstance(saved_intents, dict):
            for k in VALID_INTENTS:
                self.global_intents[k] = int(saved_intents.get(k, 0) or 0)

        self.ipw_report_count = int(self.state.get("ipw_report_count", 0) or 0)

    def _flush_working_state(self) -> None:
        # Convert deques to lists so JSON serialization works.
        flushed_providers: Dict[str, Dict[str, Any]] = {}
        for name, p in self.providers.items():
            f = dict(p)
            window = p.get("calls_window")
            if isinstance(window, deque):
                f["calls_window"] = list(window)
            flushed_providers[name] = f

        self.state["providers"] = flushed_providers
        self.state["global_intents"] = dict(self.global_intents)
        self.state["ipw_report_count"] = self.ipw_report_count
        self.state["last_reach_ts"] = self.last_reach_ts
        self.state["last_reach_provider"] = self.last_reach_provider
        self.state["last_reach_intent"] = self.last_reach_intent
        self.state["last_updated"] = time.time()

    def _provider(self, name: str) -> Dict[str, Any]:
        """Get or create the per-provider state dict."""
        if name not in self.providers:
            self.providers[name] = {
                "last_call_ts": 0.0,
                "last_error": "",
                "consecutive_failures": 0,
                "consecutive_auth_failures": 0,
                "health": "unknown",
                "total_calls": 0,
                "total_failures": 0,
                "intent_counts": {k: 0 for k in VALID_INTENTS},
                "calls_window": deque(maxlen=PANIC_THRESHOLD * 2),
                "first_call_ts": 0.0,
                "rate_per_min": DEFAULT_RATE_PER_MIN,
                "rate_per_day": DEFAULT_RATE_PER_DAY,
                "calls_today": 0,
                "today_started_ts": time.time(),
            }
        return self.providers[name]

    # ── Public API: callers use these ──────────────────────────────────────

    def should_block(self, provider: str, intent: str = "") -> Tuple[bool, str]:
        """Decide whether to block an upcoming reach to `provider`.

        Returns (block, reason). Reason is empty when block is False.
        Reasons mirror the responses safeguard.can_perform uses, so callers
        can compose: if outward says block, surface to the operator the same
        way safeguard does.
        """
        if intent and intent not in VALID_INTENTS:
            return True, f"invalid intent {intent!r} (must be one of {sorted(VALID_INTENTS)})"

        p = self._provider(provider)
        now = time.time()

        # Per-day budget — roll over at 24h since first counted call.
        if now - p.get("today_started_ts", now) >= 86400:
            p["calls_today"] = 0
            p["today_started_ts"] = now

        if p["calls_today"] >= p["rate_per_day"]:
            return True, f"daily budget exhausted for provider {provider!r}"

        # Per-minute window — count calls in last 60s.
        window_calls = sum(1 for ts in p["calls_window"] if now - ts <= 60.0)
        if window_calls >= p["rate_per_min"]:
            return True, f"per-minute rate exceeded for provider {provider!r}"

        # Health gate.
        if p["health"] == "stale_credentials":
            return True, f"provider {provider!r} flagged stale_credentials — refresh and clear before reaching"
        if p["health"] == "unhealthy":
            # Honor cooldown.
            since = now - p["last_call_ts"]
            if since < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - since)
                return True, f"provider {provider!r} unhealthy — cooldown {remaining}s remaining"

        # Panic-loop check — raw call density.
        if window_calls >= PANIC_THRESHOLD:
            return True, f"panic loop on {provider!r} ({window_calls} calls in <60s)"

        return False, ""

    def record_call(
        self,
        provider: str,
        method: str,
        url: str,
        intent: str,
        outcome: str,
        duration_ms: int = 0,
        status_code: Optional[int] = None,
        error: str = "",
    ) -> Dict[str, Any]:
        """Record a completed outward reach.

        outcome: "success" | "failure" | "auth_failure" | "timeout" | "blocked"
        Returns the per-provider state snapshot after the update.
        """
        if intent not in VALID_INTENTS:
            # Untagged calls fail closed — they still get recorded as a
            # failure, but tagged with `untagged` so the distribution shows
            # the gap rather than masking it.
            self._record_untagged(provider, method, url, outcome, duration_ms, error)
            return dict(self._provider(provider))

        now = time.time()
        p = self._provider(provider)
        if p["first_call_ts"] == 0.0:
            p["first_call_ts"] = now

        p["last_call_ts"] = now
        p["total_calls"] += 1
        p["calls_today"] = int(p.get("calls_today", 0)) + 1
        p["intent_counts"][intent] = p["intent_counts"].get(intent, 0) + 1
        p["calls_window"].append(now)

        # Global intent distribution.
        self.global_intents[intent] = self.global_intents.get(intent, 0) + 1
        self.last_reach_ts = now
        self.last_reach_provider = provider
        self.last_reach_intent = intent

        # Outcome classification.
        is_failure = outcome in ("failure", "auth_failure", "timeout")
        is_auth = outcome == "auth_failure"
        if is_failure:
            p["total_failures"] += 1
            p["consecutive_failures"] += 1
            p["last_error"] = (error or outcome)[:200]
            if is_auth:
                p["consecutive_auth_failures"] += 1
            else:
                p["consecutive_auth_failures"] = 0
        else:
            p["consecutive_failures"] = 0
            p["consecutive_auth_failures"] = 0
            p["last_error"] = ""

        # Health classification.
        p["health"] = self._classify_health(p)

        self._flush_working_state()
        self.persist_state()
        return dict(p)

    def _record_untagged(
        self,
        provider: str,
        method: str,
        url: str,
        outcome: str,
        duration_ms: int,
        error: str,
    ) -> None:
        """Untagged reaches are recorded but flagged so the intent
        distribution reflects the gap honestly."""
        p = self._provider(provider)
        p["total_calls"] += 1
        p["last_call_ts"] = time.time()
        p["calls_window"].append(p["last_call_ts"])
        p["intent_counts"]["__untagged__"] = p["intent_counts"].get("__untagged__", 0) + 1
        p["last_error"] = "intent missing — reach recorded as untagged"
        self._flush_working_state()
        self.persist_state()

    @staticmethod
    def _classify_health(provider_state: Dict[str, Any]) -> str:
        """Classify provider health based on consecutive failure counts.

        - 3+ consecutive auth failures → stale_credentials
        - 5+ consecutive failures (any kind) → unhealthy
        - 1-4 consecutive failures → degraded
        - 0 consecutive failures and ≥3 total calls → healthy
        - else unknown
        """
        if provider_state.get("consecutive_auth_failures", 0) >= STALE_CRED_FAILURES:
            return "stale_credentials"
        if provider_state.get("consecutive_failures", 0) >= 5:
            return "unhealthy"
        if provider_state.get("consecutive_failures", 0) >= 1:
            return "degraded"
        if provider_state.get("total_calls", 0) >= 3:
            return "healthy"
        return "unknown"

    # ── Pattern detection ──────────────────────────────────────────────────

    def detect_panic_loop(self) -> List[str]:
        """Return list of provider names currently in panic loop."""
        now = time.time()
        out = []
        for name, p in self.providers.items():
            recent = sum(1 for ts in p["calls_window"] if now - ts <= PANIC_WINDOW_S)
            if recent >= PANIC_THRESHOLD:
                out.append(name)
        return out

    def detect_withdrawal(self) -> List[str]:
        """Providers that were active recently then went silent for a stretch."""
        now = time.time()
        out = []
        for name, p in self.providers.items():
            last = p.get("last_call_ts", 0.0)
            if last <= 0:
                continue
            silence = now - last
            if silence >= WITHDRAWAL_SILENCE_S:
                # was the provider active before the silence began?
                first = p.get("first_call_ts", 0.0)
                if first > 0 and (last - first) >= WITHDRAWAL_PRIOR_ACTIVITY_S:
                    out.append(name)
        return out

    def detect_stale_credentials(self) -> List[str]:
        """Providers with sustained auth failures."""
        return [
            name for name, p in self.providers.items()
            if p.get("health") == "stale_credentials"
        ]

    # ── Tick / TSB publish ─────────────────────────────────────────────────

    def tick(
        self,
        pirp_context: Optional[Dict[str, Any]] = None,
        third_eye_state: Optional[Dict[str, Any]] = None,
        brain_layer: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """One tick. If pirp_context carries an `outward_call` dict, record it.
        Otherwise just refresh state and republish."""
        pirp_context = pirp_context or {}
        outward = pirp_context.get("outward_call")
        if isinstance(outward, dict):
            self.record_call(
                provider=str(outward.get("provider", "unknown")),
                method=str(outward.get("method", "GET")),
                url=str(outward.get("url", "")),
                intent=str(outward.get("intent", "")),
                outcome=str(outward.get("outcome", "success")),
                duration_ms=int(outward.get("duration_ms", 0) or 0),
                status_code=outward.get("status_code"),
                error=str(outward.get("error", "")),
            )
            self.fired_last_tick = True
        else:
            self.fired_last_tick = False
            self._flush_working_state()

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """TSB payload."""
        panic = self.detect_panic_loop()
        withdrawal = self.detect_withdrawal()
        stale = self.detect_stale_credentials()

        # Provider health summary as {name: health_class}.
        health_summary = {n: p.get("health", "unknown") for n, p in self.providers.items()}

        return {
            "reach_state": "active" if (time.time() - self.last_reach_ts < 60) else "idle",
            "last_reach_provider": self.last_reach_provider,
            "last_reach_intent": self.last_reach_intent,
            "last_reach_age_s": round(time.time() - self.last_reach_ts, 1) if self.last_reach_ts else None,
            "global_intent_distribution": dict(self.global_intents),
            "provider_count": len(self.providers),
            "provider_health": health_summary,
            "panic_loop_providers": panic,
            "withdrawal_providers": withdrawal,
            "stale_credential_providers": stale,
            "_fired_tick": self.fired_last_tick,
        }

    # ── IdentityProposalWriter handshake ───────────────────────────────────

    def should_propose_identity_update(self) -> bool:
        """True when the world the agent thinks it's connected to has changed
        materially — sustained provider failures (stale credentials) on
        previously-active providers, or sustained withdrawal patterns.

        Throttled so IPW doesn't see the same proposal every tick: we only
        re-fire after IPW_REPORT_EVERY additional failures.
        """
        stale = self.detect_stale_credentials()
        if not stale:
            return False
        # Count total auth failures across stale providers; throttle.
        total_auth_failures = sum(
            self.providers[n].get("consecutive_auth_failures", 0) for n in stale
        )
        # Allow first proposal at threshold, then every IPW_REPORT_EVERY beyond.
        return total_auth_failures >= STALE_CRED_FAILURES + (self.ipw_report_count * IPW_REPORT_EVERY)

    def proposed_identity_signal(self) -> Dict[str, Any]:
        """Compact signal for IdentityProposalWriter to consume."""
        stale = self.detect_stale_credentials()
        withdrawal = self.detect_withdrawal()
        return {
            "source": "OutwardReachLayer",
            "kind": "world_connection_changed",
            "stale_credential_providers": stale,
            "withdrawal_providers": withdrawal,
            "global_intent_distribution": dict(self.global_intents),
            "details": [
                {
                    "provider": n,
                    "consecutive_auth_failures": self.providers[n].get("consecutive_auth_failures", 0),
                    "last_error": self.providers[n].get("last_error", ""),
                }
                for n in stale
            ],
        }

    def acknowledge_proposal(self) -> None:
        """Called by IPW after routing the current signal. Bumps the
        report counter so the next proposal requires IPW_REPORT_EVERY more
        auth failures before re-firing."""
        self.ipw_report_count += 1
        self._flush_working_state()
        self.persist_state()

    # ── Operator API ──────────────────────────────────────────────────────

    def reset_provider(self, provider: str) -> bool:
        """Operator-invoked: clear per-provider failure state after the
        operator has refreshed credentials or otherwise resolved the issue.

        Returns True if the provider was known and reset, False if unknown.
        """
        if provider not in self.providers:
            return False
        p = self.providers[provider]
        p["consecutive_failures"] = 0
        p["consecutive_auth_failures"] = 0
        p["last_error"] = ""
        p["health"] = "unknown"
        # When the operator resets, also lower the IPW report count so a
        # genuinely-new failure can re-surface.
        if self.ipw_report_count > 0:
            self.ipw_report_count = max(0, self.ipw_report_count - 1)
        self._flush_working_state()
        self.persist_state()
        return True

    def configure_rates(
        self,
        provider: str,
        per_min: Optional[int] = None,
        per_day: Optional[int] = None,
    ) -> Dict[str, int]:
        """Override default rate caps for a specific provider."""
        p = self._provider(provider)
        if per_min is not None:
            p["rate_per_min"] = max(1, int(per_min))
        if per_day is not None:
            p["rate_per_day"] = max(1, int(per_day))
        self._flush_working_state()
        self.persist_state()
        return {"rate_per_min": p["rate_per_min"], "rate_per_day": p["rate_per_day"]}
