---
name: api-interaction
version: 2.0.0
description: "The agent's outward reach. Use this skill whenever the agent needs to make an HTTP request, call an external API, fetch from a URL, hit a third-party service, send a webhook, scrape a page, query a public dataset, or otherwise extend itself outside the local workspace. Each reach is metered, intent-tagged, guarded by the safeguard allowlist, and remembered. Approval-required by default — outward reach is real action in the world, not a free read."
tags: [api, http, external, integration, outward-reach]
triggers: [api call, http request, external service, fetch, webhook, get this url, post to, query the api, hit the endpoint]
---

# Outward Reach (api-interaction)

## What this is

This isn't a bag of HTTP helpers. It's the agent's **outward reach** — the act of extending past the workspace boundary into the wider world.

Every external call is three things at once:

- **A choice** — the agent decided this signal was worth the cost
- **A risk** — secrets can leak outward, untrusted data flows back in, the network can stall the loop
- **A memory** — it actually happened in the agent's history, not just locally

So this skill is paired tightly with three other parts of the system:

- `skills/safeguard.py` — gates which destinations are reachable at all (allowlist + absolute blocks like `rm -rf` of the network). An outward reach not on the safeguard whitelist requires explicit approval.
- `brain/mechanisms/outward_reach_layer.py` — the brain-side mechanism that watches reach state, tracks per-provider health, detects unhealthy patterns (panic loops, withdrawal, repeated stale-credential failures), and publishes the reach signal to the TSB.
- Episodic memory (`brain/three_tier_memory.py`) — every reach lands here with intent, outcome, and duration. The agent learns which APIs are reliable, which are noisy, which break in patterns.

## Capabilities

- `send_http_request(url, method, data, intent, provider)` — make an HTTP request with intent tagging
- `parse_api_response(response)` — parse JSON / structured response
- `authenticate_with_api(provider, credentials)` — authenticate; never logs the credential body
- `record_outward_reach(provider, method, url, intent, outcome, duration_ms)` — persist the reach to episodic memory + the OutwardReachLayer

## Intent categories

Every reach must be tagged with one of these. The OutwardReachLayer uses them to read patterns over time:

- **research** — gathering signal the agent doesn't have (web search, public data fetch, doc lookup)
- **connect** — reaching another agent, service, or human (webhook, message send, status push)
- **sense** — checking the world's current state (rate quotas, health endpoints, oracle data)
- **act** — making something happen out there (publish, deploy, post, transact)

If a reach doesn't have a clear intent, that's information — it usually means the call wasn't actually needed.

## Parameters

```json
{
  "name": "send_http_request",
  "description": "Send an HTTP request as an outward reach with intent tagging.",
  "parameters": {
    "url": {"type": "string", "description": "Target URL", "required": true},
    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"], "default": "GET"},
    "data": {"type": "object", "description": "Request body (JSON)"},
    "intent": {"type": "string", "enum": ["research", "connect", "sense", "act"], "required": true},
    "provider": {"type": "string", "description": "Logical provider name (e.g. 'github', 'searxng', 'anthropic'). Used for per-provider rate tracking."},
    "timeout_s": {"type": "number", "default": 30}
  }
}
```

## Invariants

1. **Protect API keys.** Never log the credential body. Never echo a header containing `Authorization` / `x-api-key` / `bearer` into stored output. Never write tokens into episodic memory.
2. **Respect rate limits.** Honor per-provider rate state from OutwardReachLayer before calling. If `outward_reach_layer.should_block(provider, intent)` returns True, do not call — surface to the operator instead.
3. **Tag every reach with intent.** Untagged reaches fail closed. The agent learns from intent distribution; untagged calls poison that signal.
4. **Record every reach.** Pass through `record_outward_reach()` so the call lands in ABM and updates the OutwardReachLayer. No silent calls.
5. **Bounded body size in memory.** Truncate response bodies to a reasonable size (default 2KB) before storing — full bodies belong in a separate cache, not in identity-relevant memory.

## Safety

- **Allowlist gating** — `safeguard._resolve_bridge_bin` style: providers must be on an explicit allowlist or trigger approval
- **Body sanitization** — strip API key / bearer / cookie headers from any value before logging or persisting
- **Default rate caps** (override via `OutwardReachLayer` settings):
  - 10 requests/min/provider
  - 500 requests/day/provider
  - 30s default timeout, 60s hard ceiling
- **Backoff on failure** — exponential backoff on 429/503/timeout. After 3 consecutive failures, mark provider unhealthy and stop reaching for `cooldown_seconds` (default 300s — same setting as `audit_logger._cooldown_seconds`).
- **No sensitive responses to disk** — if a response contains anything matching the redaction patterns from `runtime/security.py:SENSITIVE_PATTERNS`, redact before persisting.

## Trust Level

**approval_required** — outward reach is real action in the world, not a free read. The agent does not silently call external services. Per `skills/dispatcher.py`, this skill goes through `dispatch(skill, operation="execute")` and is gated unless explicitly allowed.

Read-only inspection of this skill's metadata (`operation="describe"` / `"list"`) does not require approval.

## How this skill fits the system

The work here is split across three layers:

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/api-interaction/SKILL.md` (this file) | Contract: what reaching outward means, what intents exist, what the agent promises |
| Brain mechanism | `brain/mechanisms/outward_reach_layer.py` | Runtime monitor: per-provider rate/health state, intent distribution, panic-loop detection, IPW handshake |
| Safety gate | `skills/safeguard.py` | Allow/block decision per-call; loop detection; the operator notification |

When wiring time arrives, the integration looks like this:

1. Agent decides to reach (e.g. fetch a URL).
2. Caller asks `OutwardReachLayer.should_block(provider, intent)`. If True → halt, surface to the operator via safeguard.
3. If allowed, caller asks `safeguard.can_perform("subprocess", [...])` for the underlying execution path.
4. Call happens.
5. Caller invokes `OutwardReachLayer.record_call(provider, method, url, intent, outcome, duration_ms)`.
6. The mechanism updates rate state, intent distribution, and provider health. State is published to the TSB so other brain mechanisms can react (e.g. AttentionModifier may bias toward introspection if reach state is "stuck").
7. Sustained provider failures route through `IdentityProposalWriter` — the world the agent thinks it's connected to has changed; that's identity-relevant data.
