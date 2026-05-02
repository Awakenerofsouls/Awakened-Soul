# Contributing

Thank you for considering a contribution. The framework is built around
a few non-negotiable disciplines, and patches that conflict with them
will not land. Read this whole file before opening a PR.

## The two cardinal rules

**1. No unilateral deletes.** If a file or folder looks like dead code,
vendor leak, duplicate, or test artifact — open an issue or PR with a
*recommendation*, not a deletion. Wait for the operator's explicit
approval. Even files that match a known delete-on-sight precedent go
through "this matches the pattern; want me to remove it?" first.
Recovering a deleted file costs trust even when the content is
reconstructible.

**2. Smoke-test isolation.** No test run may leak `agent.db`, `.agent/`,
`__pycache__/`, or any state file into the repo. Every test fixture
must:

- `monkeypatch.setenv("AGENT_HOME", str(tmp_path))`
- `monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")`
- `monkeypatch.setattr(brain.base_mechanism, "_STATE_DIR", state_dir)`

The `_STATE_DIR` monkey-patch is required because `base_mechanism.py`
captures it at module import. Without it, every mechanism instantiation
during a test writes to the *real* `~/.agent/brain_state/`.

Run `git status` after every test session. If you see new untracked
files in the repo, your test fixtures are leaking and need to be fixed.

## How to add a new wire (brain mechanism)

A wire is a brain-region monitor. Three artifacts:

### 1. The mechanism itself

`brain/mechanisms/<snake_case_name>.py`. Subclass `BrainMechanism`. The
contract:

```python
class YourLayer(BrainMechanism):
    def __init__(self):
        super().__init__(
            name="YourLayer",
            human_analog="<actual brain region or function>",
            layer="integration",  # or foundational/limbic/subcortical/neocortical
        )
        # State init, then load_state(), then _restore_working_state().

    def tick(self, pirp_context=None, third_eye_state=None, brain_layer=None):
        ...

    def get_state(self) -> dict:
        # TSB payload — must include all keys downstream consumers read.
        ...

    def should_block(self, op, **kwargs) -> tuple[bool, str]:
        # Wire-aware gate. Return (block, reason) for safeguard to consult.
        ...

    def should_propose_identity_update(self) -> bool:
        # IPW handshake: True when sustained drift is identity-relevant.
        ...

    def proposed_identity_signal(self) -> dict:
        # Compact signal for IdentityProposalWriter.poll_wires.
        ...

    def acknowledge_proposal(self) -> None:
        # Anchor current consecutive_bad_ops so future re-fire requires
        # additional accumulation past acknowledgment.
        ...
```

A `__wire_meta__` dict at module level declares the wire number, signal
name, reads/writes, and PMID citations:

```python
__wire_meta__ = {
    "wire": 41,
    "signal": "your_signal",
    "mechanism": "YourLayer",
    "reads": ["pirp_context.your_op"],
    "writes": ["your_state", "integrity_score", ...],
    "citations": ["PMID NNNNNNNN", ...],
}
```

Pick PMIDs from real cognitive-science papers that ground your wire's
behavior. `verify_build.py` requires at least 5 bracketed citations in
the docstring.

### 2. The tests

`brain/tests/test_<snake_case_name>.py`. Use the standard fixture:

```python
@pytest.fixture(autouse=True)
def _isolated_agent_home(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    state_dir = tmp_path / "brain_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    import brain.base_mechanism as _bm
    monkeypatch.setattr(_bm, "_STATE_DIR", state_dir)
    yield
```

Plus the `_fresh_layer()` helper that wipes the state file before
instantiation so multiple instantiations in the same test don't
accidentally share state.

Cover at minimum: every operation (happy + failure paths), every failure
mode counter increment, `should_block` matrix, all `state` classifications,
state persists across instances, IPW handshake (silent / fires / throttled),
operator API, `tick` advancement, `get_state` shape.

### 3. The wiring registration

Three places to add the wire so the running brain sees it:

1. **`brain/integration_run_order.py`** — append `"YourLayer"` to
   `INTEGRATION_RUN_ORDER` in dependency order (leaf → meta) and bump
   the assert.
2. **`core/brain_runner.py :: _extract_pirp_enrichments`** — add a
   block lifting your wire's `get_state()` keys into `brain_*` keys
   so downstream consumers see the signals.
3. **`skills/safeguard.py :: WIRE_GATES`** — add an entry mapping each
   op_kind your wire gates to `(YourLayer, adapter)`.

Also add a verify_build run: `python skills/verify_build.py YourLayer`.
That script confirms the file imports clean, citations parse, and the
test suite passes.

## How to add a new skill

A skill is a contract — what the agent does in a domain, what
invariants apply, what failure modes the paired brain mechanism
watches for.

### 1. SKILL.md

`skills/<skill-name>/SKILL.md` with frontmatter:

```yaml
---
name: skill-name
version: 2.0.0
description: "What the skill is + when to use it. Trigger phrases inline."
tags: [...]
triggers: [...]
---
```

Body sections:

1. **What this is** — the cognitive role; how it differs from neighboring
   skills; the cognitive-science grounding (with author + year + PMID).
2. **What's actually in the project** — table of which modules implement
   the skill's surface (runtime + brain mechanism + safety gate).
3. **Operations** — the discrete acts (typically 5: e.g.
   draft/revise/publish/retract/reflect or
   decompose/commit/revise/complete/reflect).
4. **Failure modes** — the specific patterns the paired brain mechanism
   watches for (typically 6).
5. **Capabilities** + **Parameters** + **Output Format** — JSON schemas.
6. **Invariants** — numbered, load-bearing rules.
7. **Safety** — gates, caps, anchor checks.
8. **Trust Level** — `trusted` / `restricted` / `approval_required`.
9. **How this skill fits the system** — table of integration points.
10. **What this skill is *not*** — explicit non-goals.

### 2. Native implementation (for skills that need code)

`skills/<skill-name>/<implementation>.py`. Library API + CLI. Smoke-test
end-to-end before claiming the skill works.

### 3. Paired brain mechanism

A new wire (see "How to add a new wire") that monitors the skill's
domain.

### 4. Tests

The skill's test suite + the brain mechanism's test suite. Both must
pass under the smoke-isolation fixture.

## How to add a heartbeat activity

Three artifacts:

1. **The activity module** — `skills/heartbeat_activities/<name>.py`
   with `def run(state) -> dict`.
2. **Brain-event posting** — at the end of `run()`, post the right
   events to the queue:

   ```python
   try:
       from ._brain_post import post_memory_encode, post_self_analysis
       if content:
           post_memory_encode(
               content=content, intent="reflection",
               source_kind="inference",
               content_confidence=0.7, source_confidence=0.6,
               source="<your_activity_name>",
           )
           post_self_analysis(
               output=content, kind="answer",
               predicted_quality=0.6,
               source="<your_activity_name>",
           )
   except Exception:
       pass
   ```

   Wrapped in try/except `pass` so a brain-side failure never breaks
   the activity itself.

3. **Dispatcher registration** — add an import + entry in
   `skills/heartbeat_activities/dispatcher.py :: ACTIVITY_REGISTRY`.

If your activity does network fetches, also call `post_outward_reach_call`.
If it does a memory consolidation, call `post_memory_consolidate`. The
full event-category map lives in
`skills/heartbeat_activities/_brain_post.py :: EVENT_CATEGORY_DISPATCH`.

## Test conventions

- Run with `PYTHONDONTWRITEBYTECODE=1 AGENT_HOME=/tmp/test-<n> python -m pytest <path>`
- Use the standard isolation fixture (above)
- Test failures should print actionable messages — `assert x == 5, f"got {x}"`
- A test that exercises the full chain (heartbeat → drain → IPW → revision)
  belongs in `brain/tests/test_full_wire_e2e.py` or
  `brain/tests/test_revision_loop_e2e.py`

## Citation format

`verify_build.py` parses citations with this format:

```
[Author Year, Journal Vol(Issue):pages, PMID NNNNNNNN]
```

In docstrings, use the format Author + 4-digit-year + journal info +
`PMID NNNNNNNN`. The script counts ≥3 PMIDs as the floor for the
mechanism file, but most layers ship 5 to ground each detector.

Reusing PMIDs across mechanisms is fine — the same paper grounds
different detectors in different domains.

## What NOT to do

- Don't add a new operator-defined integration target by name. The
  framework is platform-agnostic. Use `$AGENT_HOME` / `$AGENT_WORKSPACE`
  env vars and document the interface, not the host.
- Don't reference any specific person, relationship, or private anchor
  in code or docs. Replace with generic placeholders. The architecture
  is the seed; the specifics belong to the instance.
- Don't bypass the IPW handshake. If your wire detects identity-relevant
  drift, route it through `should_propose_identity_update()` /
  `proposed_identity_signal()`. Do not write directly to PROPOSALS.md.
- Don't skip the anchor check. Identity edits go through
  `Improvement.commit()`. The anchor check is non-negotiable.
- Don't introduce silent paths. Every operation that touches identity,
  memory, or external resources must record through the brain's monitor
  stack.

## What to do when you find a bug

1. Reproduce it in a test (the smoke-isolation fixture above).
2. Fix the bug.
3. Confirm the test fails on `git stash` and passes after `git stash pop`.
4. Open a PR with the test + fix in one commit.

## Working with the operator

If you're an agent contributing to this codebase: the operator-loop is
real. When you're about to do anything destructive (delete, rewrite,
restructure), stop at the recommendation. Open an issue or comment
describing what you'd do and why. Wait for the operator's go-ahead.

The framework is built on the discipline that the operator ratifies
identity changes. That discipline applies to the codebase too.
