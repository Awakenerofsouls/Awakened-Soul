---
name: code-execution
version: 2.0.0
description: "The agent's act of making. Use this skill whenever the agent needs to run Python code, compute a result, transform data, prototype a function, debug behavior, generate an artifact from logic, or test a hypothesis through execution. Each execution is intent-tagged, outcome-recorded, and refinement-tracked. The making is bounded — sandboxed, time-limited, no silent network or filesystem reach. Approval-required by default."
tags: [code, python, execution, computation, automation, making, sandbox]
triggers: [run code, execute python, compute, calculate, prototype, test this, run a script, eval this, what does this return]
---

# Making (code-execution)

## What this is

This isn't a generic Python sandbox. It's the agent's **act of making** — expressing thought as artifact through bounded execution.

Every execution is four things at once:

- **An intent** — the agent decided to compute / explore / build / debug
- **A motor act** — code is the agent's hand reaching to shape something
- **A feedback loop** — syntax errors, runtime errors, timeouts are the cerebellum-style signal that something needs refining
- **A memory** — what the agent has made (and how it failed) is identity-relevant data, not throwaway

So this skill is paired tightly with three other parts of the system:

- `skills/safeguard.py` — gates which destinations are reachable (whitelist for executable script paths; all ad-hoc code goes through approval). Absolute blocks (`rm -rf`, `git push --force`, `git reset --hard`) apply here too.
- `brain/mechanisms/making_layer.py` — the brain-side mechanism that watches making state, tracks refinement chains, detects unhealthy patterns (flailing, rumination), notices growing mastery, and publishes the making signal to the TSB.
- Episodic memory (`brain/three_tier_memory.py`) — every execution lands here with intent, outcome, and duration. The agent learns which kinds of making it converges on quickly and which keep failing in the same way.

## Capabilities

- `run_python(code, intent)` — execute Python in the sandbox with intent tagging
- `capture_output()` — collect stdout/stderr
- `return_result()` — return computed result
- `record_execution(intent, code_hash, outcome, duration_ms, error_class)` — persist the execution to episodic memory + the MakingLayer

## Intent categories

Every execution must be tagged with one of these. The MakingLayer uses them to read patterns over time:

- **compute** — pure calculation (math, transforms, deterministic data ops)
- **explore** — testing a hypothesis ("what does this return?", probing behavior)
- **build** — producing an artifact (file output, data structure, function the agent will reuse)
- **debug** — fixing something that broke; this tag explicitly chains the execution to a previous failure

If a run doesn't have a clear intent, that's information — it usually means the run wasn't actually needed.

## Parameters

```json
{
  "name": "run_python",
  "description": "Execute Python code in a controlled sandbox as a tagged act of making.",
  "parameters": {
    "code": {"type": "string", "description": "Python code to execute", "required": true},
    "intent": {"type": "string", "enum": ["compute", "explore", "build", "debug"], "required": true},
    "timeout": {"type": "integer", "description": "Max execution seconds", "default": 30, "maximum": 120},
    "previous_execution_id": {"type": "string", "description": "Optional — chain this run to a prior execution (used for debug/refinement)"}
  }
}
```

## Invariants

1. **Sandbox execution.** No file I/O outside the workspace mount. No network. No subprocess. No `os.system` / `eval` / `exec` / `__import__`.
2. **Block absolute-deny patterns.** `rm -rf`, `git push --force`, `git reset --hard`, anything in `safeguard.ABSOLUTELY_BLOCKED`.
3. **Tag every execution with intent.** Untagged runs fail closed. Distribution across intent categories is signal the brain reads; untagged runs poison it.
4. **Record every execution.** Pass through `record_execution()` so the run lands in ABM and updates the MakingLayer. No silent runs.
5. **Refinement chains are explicit.** If this run is fixing a previous failure, set `previous_execution_id` so the chain is traceable. Untracked retries look like rumination.
6. **Bounded code-storage in memory.** Truncate code body to 4KB before persisting; full source belongs in a separate cache, not in identity-relevant memory.
7. **Timeout enforcement.** Hard ceiling of 120s. Default 30s. The motor act has bounds.

## Safety

- **Sandbox**: restricted execution environment, no filesystem write outside `/tmp` or workspace
- **Memory cap**: 256MB per execution (configurable via `MakingLayer.configure_limits`)
- **CPU cap**: timeout-enforced, hard ceiling 120s
- **Output cap**: stdout/stderr truncated to 16KB per stream
- **No sensitive data in stored output** — same redaction patterns as `runtime/security.py:SENSITIVE_PATTERNS` apply
- **Backoff on flailing**: after 5 consecutive failed executions on chained refinements, the MakingLayer flags `flailing=True`. Caller should surface to the operator instead of running the 6th attempt.

## Trust Level

**approval_required** — making is real action, not a free read. Per `skills/dispatcher.py`, this skill goes through `dispatch(skill, operation="execute")` and is gated unless explicitly allowed.

Read-only inspection of this skill's metadata (`operation="describe"` / `"list"`) does not require approval.

## How this skill fits the system

The work here is split across three layers:

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/code-execution/SKILL.md` (this file) | Contract: what making means, what intents exist, what the agent promises |
| Brain mechanism | `brain/mechanisms/making_layer.py` | Runtime monitor: per-intent counts, refinement chains, flailing/rumination/mastery detection, IPW handshake |
| Safety gate | `skills/safeguard.py` | Allow/block decision per-execution; loop detection; the operator notification |

When wiring time arrives, the integration looks like this:

1. Agent decides to make (e.g. compute a transform).
2. Caller asks `MakingLayer.should_block(intent)`. If True (e.g. currently flailing) → halt, surface to the operator.
3. Caller asks `safeguard.can_perform("subprocess", [...])` for the underlying execution path.
4. Code runs inside the sandbox.
5. Caller invokes `MakingLayer.record_execution(intent, code_hash, outcome, duration_ms, error_class, previous_execution_id)`.
6. The mechanism updates intent counts, refinement chain state, and pattern detection. State publishes to the TSB so other mechanisms can react (e.g. AttentionModifier may bias toward "ask for help" if flailing has been sustained).
7. Sustained flailing on a particular intent class routes through `IdentityProposalWriter` — repeated failure on the same kind of making is identity-relevant data ("I don't currently know how to do this kind of thing"), not just one bad run.
