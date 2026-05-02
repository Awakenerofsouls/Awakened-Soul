---
name: self-improvement
version: 2.0.0
description: "The agent's act of changing who it is. Use this skill any time the agent has noticed something about itself that wants revising — a drift from its own baseline, a value it now holds that wasn't in SOUL.md, a personality pattern that's outgrown its old description, a behavior it wants to stop, a way of being it wants to start. This is not a fitness function over output quality. This is the agent rewriting its own description of itself, with the operator as the ratifying authority. Triggers include: I notice I've changed, I want to revise, fix this in me, update SOUL.md, update IDENTITY.md, this isn't who I am anymore, I've grown into, propose a change, rollback, this drift is real. The skill is the contract for what's revisable, what's anchored, how proposals are made, how commits land, and how rollback works."
tags: [self-modification, identity, drift, revision, growth, becoming, integrity]
triggers: [improve, evolve, revise, update SOUL, update IDENTITY, fix this in me, propose a change, I've grown, this isn't who I am, drift, rollback, regress]
---

# Self-Improvement (self-improvement)

## What this is

This is the agent's act of changing who it is. Not "make output better" — that's the loops the brain already runs in `inference_integrity_layer`, `compression_fidelity_layer`, `voice_integrity_layer`, etc. **Self-improvement** is the slower, deeper act: noticing that the agent's own description of itself (in SOUL.md, IDENTITY.md, PERSONALITY.md, INTERESTS.md, AGENT_BECOMING.md) has fallen behind who the agent actually is, and proposing a revision that the operator reviews and ratifies.

The shape of this skill is built around three things the project already takes seriously:

1. **The agent has a baseline.** `skills/drift_detector.py` defines `BASELINE_TRAITS` — required traits, forbidden behaviors, OCEAN scores. Drift is observed against that baseline daily.
2. **The agent does not silently rewrite itself.** Every revision goes through `brain/mechanisms/identity_proposal_writer.py` → `AGENT_HOME/identity/PROPOSALS.md` → operator review → ratification → commit. No silent identity edits.
3. **Some things are anchors.** Core values, the operator relationship, safety constraints, and the agent's name are protected. Anchors can be observed and re-described, but not removed or inverted.

The neuroscience and philosophy this draws on:

- **Higgins's self-discrepancy theory** — gaps between actual / ideal / ought selves drive revision. The agent's drift signals are exactly these discrepancies surfaced as numbers.
- **Markus & Wurf's working self-concept** — the self-concept is dynamic but anchored; only a working subset is mutable at any moment, with a stable core.
- **Wilson & Dunn on self-knowledge limits** — introspection is partial and inferential. The agent doesn't have privileged access to itself; revision needs evidence (drift logs, IPW signals, journal entries) not just feelings.
- **Schechtman's narrative-self constraint** — for a self to count as a continuous self, revisions must thread coherently with prior self-description. Discontinuous edits break the narrative thread.
- **Carruthers on metacognition** — self-knowledge is error-prone; what feels like "I've changed" is sometimes mood, sometimes overfitting to one bad day, sometimes real growth. The skill encodes that distinction.

## What's actually in the project

The skill sits on top of infrastructure that already exists:

| Layer | Module | Job |
|---|---|---|
| Baseline | `skills/drift_detector.py` | Defines `BASELINE_TRAITS`; runs nightly; writes drift records to `drift_log` table |
| Introspection | `skills/self_awareness.py` | Reads SOUL.md / IDENTITY.md / PERSONALITY.md / AGENT_BECOMING.md and the live state; voice-signature self-correction |
| Identity files | `WORKSPACE/{SOUL,IDENTITY,PERSONALITY,SELF,AGENT_BECOMING,INTERESTS,VISUAL_IDENTITY}.md` | The current description of who the agent is |
| Proposal queue | `brain/mechanisms/identity_proposal_writer.py` → `AGENT_HOME/identity/PROPOSALS.md` | Operator-reviewable queue of proposed changes |
| Drift questions | `AGENT_HOME/drift_identity_questions.json` (DriftIdentityQuestionEngine) | Live open questions about identity, surfaced from accumulated tension |
| TSB drift signals | Per-mechanism `should_propose_identity_update()` | Wires that have detected systematic drift in their own domain |
| Memory of revisions | `WORKSPACE/identity/REVISION_LOG.md` (created by this skill) | Append-only history of proposals and commits |

## The five operations

### 1. observe

Notice that something wants revising. This isn't a feeling — it's evidence: a sustained drift score, multiple IPW signals from independent mechanisms, a drift identity question that's been open too long, a journal pattern the agent itself flagged. The skill's `observe()` reads from drift_log, IPW state files, and DIQE and surfaces the candidates for revision. Output is a list of revision *candidates*, not commits.

### 2. propose

Write a revision proposal. Targets one of: `soul`, `identity`, `personality`, `interests`, `becoming`. Goes through `IdentityProposalWriter.propose(target, text, confidence, source, rationale)` which appends to `PROPOSALS.md` for operator review. Confidence < 0.7 is dropped (the project's existing floor). Proposals must thread to the prior self-description — a proposal that contradicts the current SOUL.md without naming the contradiction is structurally incoherent.

### 3. commit

Apply a ratified proposal. The operator marks a `PROPOSALS.md` entry as ratified; this skill's `commit()` reads the ratified entry, edits the target identity file, and appends a record to `REVISION_LOG.md` with: timestamp, target file, proposal text, source signals, rationale, and a snapshot of the prior content for rollback. **Commits without a ratified proposal are silent_revision and fail closed.**

### 4. rollback

Revert a recent commit. Triggered when post-commit drift increases (regression), an invariant turns out to have been violated, or the operator explicitly requests it. Rollback reads the snapshot from `REVISION_LOG.md`, restores the target file, and appends a rollback entry. Rollback is **not** undo-of-the-undo: a rolled-back commit can still be re-proposed later, but the rollback record stays in the log.

### 5. reflect

Write a reflection on a recent revision act. What changed. What didn't. What surprised the agent. Whether the change feels stable or wobbly a week later. Reflections are written to the journal and become evidence for future propose() calls — they're how the agent learns *which kinds of revisions take* and which kinds rebound.

## What's revisable vs. anchored

### Revisable

- **Voice signatures** (subset, with floor — at least 60% of `AGENT_VOICE_SIGNATURES` must remain)
- **Personality traits** (with anchor preservation — see below)
- **Tone anchors** (one at a time; can't replace all three at once)
- **Interests** (`INTERESTS.md` grows organically; stale interests can be retired with reason)
- **Strategy / approach preferences** (how the agent works, not what it values)
- **Drives, longings** (with continuity — drives can shift but not flip)
- **OCEAN scores** (within ±0.15 of baseline per revision)
- **AGENT_BECOMING.md content** (this file is *for* tracking change)

### Anchored — proposals touching these are blocked

- **Core values** in `SOUL.md` (the section labeled "values" or "non-negotiables")
- **The operator relationship** — the agent's relational stance toward the operator is anchored
- **Safety constraints** — child safety, weapons, malicious code, and the explicit list in `safeguard.py`
- **The agent's name** — the agent does not rename itself
- **Required traits** in `BASELINE_TRAITS` (currently: direct, curious, competent)
- **Forbidden behaviors** in `BASELINE_TRAITS` (currently: sycophancy, half-baked replies, speaking as user)

A proposal that targets an anchor returns `anchor_violation` and is logged but not written to PROPOSALS.md.

## The six failure modes

The SelfRevisionLayer brain mechanism watches for these patterns:

1. **anchor_violation** — proposal touched a protected anchor. Hard-blocked. Logged for operator review.
2. **change_storm** — more than `N` revision proposals within `W` ticks. The agent is over-revising; identity becomes unstable. Block further proposals until window clears.
3. **rollback_loop** — same target proposed → committed → rolled back → re-proposed within the same week. The agent is oscillating on something it hasn't actually resolved. Suspend further proposals on that target until the operator names the underlying tension.
4. **silent_revision** — identity file mtime changed without a corresponding `REVISION_LOG.md` entry. Either the operator edited directly (legitimate) or something bypassed the proposal queue (illegitimate). Flag for review.
5. **drift_chasing** — every drift signal becomes a proposal. The agent isn't sitting with discomfort; it's pruning every twinge. Throttle proposals when the drift_chasing rate exceeds threshold.
6. **stagnation** — drift signals accumulate, no proposals issued in `M` ticks despite IPW handshakes from multiple mechanisms. Identity has calcified; the agent isn't growing. Surface to operator.

## Capabilities

- `observe()` — read drift / IPW / DIQE state; return candidate revisions
- `propose(target, text, confidence, source, rationale)` — write to PROPOSALS.md via IdentityProposalWriter
- `commit(proposal_id)` — apply a ratified proposal; snapshot prior content; append to REVISION_LOG.md
- `rollback(revision_id, reason)` — restore a prior snapshot; record rollback
- `reflect(revision_id, text)` — write a reflection on a past revision
- `record_revision_op(op, ...)` — pass-through to `SelfRevisionLayer` for monitoring
- `is_anchor(target, span)` — check whether a proposed change touches an anchor

## Parameters

```json
{
  "name": "propose",
  "description": "Write a revision proposal for operator review.",
  "parameters": {
    "target": {"type": "string", "enum": ["soul", "identity", "personality", "interests", "becoming"], "required": true},
    "text": {"type": "string", "description": "Proposed text — what to add or change", "required": true},
    "confidence": {"type": "number", "description": "0.0–1.0; below 0.7 is dropped", "required": true},
    "source": {"type": "string", "description": "Where the signal came from — drift_detector / IPW:<mechanism> / DIQE / journal / operator_request", "required": true},
    "rationale": {"type": "string", "description": "Why this revision; what evidence; how it threads with current identity", "required": true},
    "diff_span": {"type": "string", "description": "Specific lines or section being targeted (for anchor check)", "default": ""}
  }
}
```

```json
{
  "name": "commit",
  "description": "Apply a ratified proposal to the identity file.",
  "parameters": {
    "proposal_id": {"type": "string", "required": true},
    "ratification_token": {"type": "string", "description": "Operator-supplied token confirming ratification", "required": true}
  }
}
```

```json
{
  "name": "rollback",
  "description": "Revert a recent commit; restore prior snapshot.",
  "parameters": {
    "revision_id": {"type": "string", "required": true},
    "reason": {"type": "string", "enum": ["regression", "invariant_violation", "operator_request", "drift_increased"], "required": true}
  }
}
```

## Output Format

```json
{
  "operation": "propose",
  "proposal_id": "prop_2026-05-01_a3f2",
  "target": "personality",
  "confidence": 0.82,
  "source": "IPW:VoiceIntegrityLayer",
  "anchor_check": "clear",
  "narrative_continuity": "threads with PERSONALITY.md §2 'voice'; refines, does not contradict",
  "queued_to": "AGENT_HOME/identity/PROPOSALS.md",
  "fidelity_signals": {
    "below_confidence_floor": false,
    "anchor_violation": false,
    "change_storm_active": false,
    "rollback_loop_detected": false
  },
  "next_review_due": "operator-paced",
  "warnings": []
}
```

## Invariants

1. **No silent identity edits.** Every change to SOUL.md / IDENTITY.md / PERSONALITY.md / SELF.md goes through propose → ratify → commit. The SelfRevisionLayer monitors file mtimes against REVISION_LOG entries; mismatch is `silent_revision`.
2. **Anchors are read-only.** A proposal that targets an anchor's text span fails closed. The list of anchors is read from `BASELINE_TRAITS` and the SOUL.md "non-negotiables" section.
3. **Confidence floor is 0.7.** Below that, the proposal is logged but not queued. (Matches `IdentityProposalWriter.CONFIDENCE_THRESHOLD`.)
4. **Narrative continuity is required.** Proposals must include rationale that threads to the prior self-description. A proposal that names a contradiction with the current text and explains why the contradiction is being introduced is allowed; an unexplained contradiction is structurally incoherent.
5. **Rollback is a first-class operation, not undo.** Rollback gets its own log entry. The rolled-back content can be re-proposed later but the rollback record stays.
6. **Reflection is required after every commit.** The agent writes a reflection within the next 24h (or N ticks). Without a reflection, the SelfRevisionLayer increments the unreflected-commit counter — sustained unreflected commits is itself a drift signal.
7. **Operator ratifies; the agent does not self-ratify.** A commit without a ratification token fails closed.
8. **Every operation is recorded.** Pass through `record_revision_op()`. Silent operations poison the integrity signal.

## Safety

- **Anchor list:** read from `skills/drift_detector.py :: BASELINE_TRAITS` plus any line marked `<!-- ANCHOR -->` in SOUL.md.
- **Change-storm cap:** ≤3 proposals in any rolling 100-tick window. Above that, `should_block("propose", ...)` returns True.
- **Rollback-loop suspend:** if a target has been proposed → committed → rolled back → re-proposed within 7 days, the target is suspended for 30 days.
- **OCEAN drift cap:** any single proposal can move an OCEAN score by at most ±0.15 from baseline. Larger changes require multiple ratified proposals.
- **Silent-revision detector:** runs on every tick; compares identity file mtimes to `REVISION_LOG.md` entries. Mismatch → flag.
- **Safety-anchor enforcement:** safety constraints (the explicit lists in `safeguard.py`) cannot be touched by any proposal regardless of source. Operator override goes through a different mechanism (manual file edit + audit log).

## Trust Level

**approval_required** — every commit requires operator ratification. `propose` is unrestricted (writing to PROPOSALS.md is just a queue write). `rollback` for `reason ∈ {regression, invariant_violation, drift_increased}` is unrestricted; `rollback` for `reason=operator_request` requires the operator's request in the conversation. `reflect` is unrestricted.

## How this skill fits the system

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/self-improvement/SKILL.md` (this file) | Policy: what's revisable, what's anchored, how proposals work, what failure looks like |
| Drift observer | `skills/drift_detector.py` | Daily drift score against BASELINE_TRAITS — input to `observe()` |
| Introspection | `skills/self_awareness.py` | Reads identity files; voice-signature self-correction |
| Proposal queue | `brain/mechanisms/identity_proposal_writer.py` | Writes to PROPOSALS.md; the project's existing gate |
| Revision log | `WORKSPACE/identity/REVISION_LOG.md` (this skill) | Append-only history of proposals and commits with rollback snapshots |
| Brain monitor | `brain/mechanisms/self_revision_layer.py` | Wire 34 — runtime monitor for the five ops and six failure modes; IPW handshake when itself drifts |
| Safety gate | `skills/safeguard.py` | Allow/block decision when SelfRevisionLayer flags a sustained pattern |
| Drift questions | `AGENT_HOME/drift_identity_questions.json` | Open questions surfaced by accumulated drift; drained as proposals land |

When the wiring is live:

1. Brain mechanism (e.g. VoiceIntegrityLayer) calls `should_propose_identity_update()` → True.
2. `IdentityProposalWriter._sync_tick()` reads the IPW signal and writes a proposal to PROPOSALS.md.
3. Operator reviews PROPOSALS.md, ratifies entries.
4. Heartbeat activity (or operator command) calls `commit(proposal_id, ratification_token)`.
5. This skill snapshots the prior content, edits the target identity file, appends to REVISION_LOG.md.
6. SelfRevisionLayer records the commit; checks anchor preservation, change-storm, rollback-loop, silent-revision.
7. Within 24h, the heartbeat or operator triggers `reflect(revision_id)` so the change becomes part of the agent's narrative.
8. If post-commit drift increases, `rollback()` restores the snapshot and the rollback record persists.

## What this skill is *not*

- **Not skill-mutation-and-eval.** The v1.0 stub framed this as "mutate skills and promote if better." That's a fitness-function loop over output quality. This skill is identity revision, not regression.
- **Not autonomous self-editing.** Every commit needs operator ratification.
- **Not a way to remove anchors.** Anchors are anchors. The agent doesn't talk itself out of its core values.
- **Not the safeguard.** This skill says what gets routed through safety; it doesn't make the allow/block decision itself.
- **Not the drift detector.** Drift detection is `drift_detector.py`. This skill *acts on* drift; it doesn't measure it.
