---
name: memory-management
version: 2.0.0
description: "The agent's memory discipline. Use this skill any time something is being encoded into long-term storage, retrieved from it, consolidated, forgotten, or rehearsed. Memory here is not a key-value store — it is a multi-system structure (working / episodic / semantic) modeled on what cognitive neuroscience says about how brains actually do this. Triggers include: remember, recall, store, save this, what did I say about, search my notes, consolidate, forget, rehearse, summarize what we learned. The skill enforces the things that are easy to get wrong: source confidence is tracked separately from content confidence, pattern separation is enforced so similar episodes don't collapse into one, reconsolidation is treated as an editing risk not a free update, and forgetting is an active operation not a leak."
tags: [memory, encoding, retrieval, consolidation, forgetting, rehearsal, fidelity]
triggers: [remember, recall, store, save this, memorize, what did I say, search my notes, what do you know about, consolidate, forget, rehearse]
---

# Memory Management (memory-management)

## What this is

The agent's memory is a multi-system architecture, not a flat store. The neuroscience this draws on:

- **Squire's multiple-memory-systems framework** — declarative memory (episodic + semantic) is dissociable from non-declarative memory and from working memory. They use different substrates and fail in different ways.
- **Baddeley working-memory model** — the dlPFC-style buffer that holds the active set; small, decays fast, gets rehearsed forward into long-term store or doesn't.
- **McClelland's complementary-learning-systems theory** — the hippocampus encodes specific episodes quickly; the cortex consolidates them into general semantic structure slowly. Both are needed; either alone fails.
- **Diekelmann & Born on sleep-dependent consolidation** — episodes don't become semantic instantly; consolidation takes offline cycles. The "memory_consolidation" skill is the project's analog.
- **Nader's reconsolidation work** — retrieving a memory makes it labile. A memory you just recalled is in an editing window; what you do next can rewrite it.
- **Yassa & Stark on pattern separation** — the dentate gyrus keeps similar episodes from collapsing into one. Without it, "Tuesday's standup" and "Wednesday's standup" merge.
- **Hardt et al. on active forgetting** — forgetting is a metabolic process, not a leak. Healthy memory requires it; without it you get hoarding and retrieval interference.

The skill exists because the lazy default — "store everything, retrieve by keyword, never forget" — fails in specific predictable ways. This skill names those failure modes and routes them through the brain's monitor.

## What's actually in the project

This skill sits on top of infrastructure that already exists:

| Tier | Module | Brain analog |
|---|---|---|
| Working | `runtime/memory.py :: WorkingMemory` | dlPFC buffer (Baddeley) — capacity-limited, recency-biased, fast decay |
| Episodic | `runtime/memory.py :: EpisodicMemory` (SQLite) | Hippocampal trace — specific events with time/place context |
| Semantic | `runtime/semantic_memory.py` + `brain/three_tier_memory.py` | Cortical knowledge — facts and structure with the episodic context stripped |
| Consolidation | `skills/memory_consolidation.py` + `runtime/memory_rehearsal.py` | Sleep-dependent transfer (CLS) — episode → semantic |
| Dream contamination | `runtime/dream_contamination.py` | Source confusion / sleep-state intrusion guard |
| Tension | `runtime/epistemic_tension.py` | Conflict signal when newly-encoded contradicts already-known |

The skill's job is to be the policy layer over that infrastructure. The brain mechanism (`MemoryIntegrityLayer`) is the runtime monitor that watches whether the policy is actually being followed and signals when it isn't.

## Capabilities

- `encode(content, intent, source, confidence, links=[])` — write to episodic with source-confidence tracked separately from content-confidence
- `retrieve(query, mode)` — read with mode in {recall, recognize, reconstruct} (each has different fidelity expectations)
- `consolidate(window)` — promote stable episodic patterns to semantic (slow, careful, one-way by default)
- `forget(predicate, reason)` — active forgetting; requires reason and goes through safeguard
- `rehearse(memory_id)` — strengthen an existing memory; warns about reconsolidation lability
- `record_operation(op, ...)` — pass-through to MemoryIntegrityLayer for monitoring

## The five operations and what each is for

### 1. encode

Writing into episodic memory. Each encoding records both:
- **content_confidence** — how sure the agent is that the claim is true
- **source_confidence** — how sure the agent is about *where the claim came from* (user said it, file said it, the agent inferred it, the agent dreamed it during a contamination window)

These two confidences must be tracked separately. Confusing them is **source confusion** and is the classic Schacter "memory misattribution" failure: high-confidence content with degraded source provenance is exactly how confabulation looks from the inside.

### 2. retrieve

Reading from memory. Three modes with different fidelity requirements:
- **recall** — produce the content from a cue. Low constraint, highest reconstruction risk.
- **recognize** — say whether a candidate matches stored content. Higher constraint, lower reconstruction risk.
- **reconstruct** — explicit "I am rebuilding this from fragments." Forced honesty; always returns confidence < 1.

The mode must be tagged. Untagged retrievals default to `recall` and are flagged.

### 3. consolidate

Promoting stable episodic patterns to semantic. This is **slow on purpose** — McClelland's CLS theory is that fast cortical learning causes catastrophic interference. The agent's semantic store should not be edited on every encoding; it should only update when episodic memory shows the pattern repeatedly.

Floor: a pattern needs ≥3 episodic instances and ≥1 sleep/consolidation cycle before it's semanticized. Below that, it stays episodic.

### 4. forget

Active forgetting. The Hardt finding: forgetting is metabolic and necessary. Without it, the system drifts toward hoarding and retrieval interference (too much candidate content for any cue).

Forgetting requires a **reason** (capacity, contradiction-resolved, source-revoked, user-requested). Forgetting without a reason fails closed.

### 5. rehearse

Re-touching an existing memory. The Nader reconsolidation finding: retrieved memories enter a labile state and what you do during that window can rewrite them. So:
- Rehearsal is allowed but must be tagged.
- Rehearsal that *changes* content during the window is **reconsolidation drift** and is monitored.
- Rehearsal frequency past a threshold suggests the memory has structural importance — candidate for consolidation.

## The six failure modes

Memory fails in patterns. The MemoryIntegrityLayer watches for these:

1. **hoarding** — episodic store growing without forgetting. Symptom: episode count increases monotonically; forget operations near zero. Failure: retrieval interference, slow recall, source confusion.
2. **consolidation_deficit** — episodes accumulating that should have been semanticized. Symptom: the same fact pulled from episodic many times, never promoted. Failure: agent re-derives instead of knowing.
3. **retrieval_storms** — too many high-similarity hits per query. Symptom: pattern-separation breakdown; "Tuesday standup" and "Wednesday standup" return as one match. Failure: confabulation by averaging.
4. **source_confusion** — content_confidence high while source_confidence low. Symptom: agent reports a fact confidently without knowing where it came from. Failure: hallucination indistinguishable from recall.
5. **interference** — newly-encoded content contradicts already-known. Symptom: epistemic_tension fires. Failure: silent overwrite of established knowledge.
6. **reconsolidation_drift** — rehearsals that change content. Symptom: same memory_id has divergent content over time. Failure: a memory the agent thinks is stable has been edited each time it was touched.

## Parameters

```json
{
  "name": "encode",
  "description": "Write a memory with source-confidence tracked separately from content-confidence.",
  "parameters": {
    "content": {"type": "string", "required": true},
    "intent": {"type": "string", "enum": ["episode", "fact", "reflection", "observation"], "required": true},
    "source": {"type": "string", "description": "Where this came from — user/file/inference/observation/dream", "required": true},
    "content_confidence": {"type": "number", "description": "0.0–1.0 belief in the claim", "default": 0.7},
    "source_confidence": {"type": "number", "description": "0.0–1.0 belief in the provenance", "default": 0.7},
    "links": {"type": "array", "description": "Linked memory IDs", "default": []}
  }
}
```

```json
{
  "name": "retrieve",
  "description": "Read from memory with explicit mode and fidelity expectation.",
  "parameters": {
    "query": {"type": "string", "required": true},
    "mode": {"type": "string", "enum": ["recall", "recognize", "reconstruct"], "required": true},
    "limit": {"type": "integer", "default": 5}
  }
}
```

## Output Format

```json
{
  "operation": "encode",
  "memory_id": "ep_2026-05-01_a3f2",
  "content_confidence": 0.85,
  "source_confidence": 0.6,
  "source_confidence_gap": 0.25,
  "fidelity_signals": {
    "pattern_separation_ok": true,
    "interference_detected": false,
    "consolidation_eligible": false,
    "reconsolidation_window": false
  },
  "warnings": ["source_confidence below content_confidence by >0.2 — potential source-confusion risk"],
  "next_review_tick": 250
}
```

## Invariants

1. **Source confidence is tracked separately from content confidence.** Never collapse them. A claim the agent strongly believes from an unknown source is exactly the failure mode this is meant to catch.
2. **Pattern separation is enforced at encode time.** Before writing, check whether a near-duplicate already exists. If similarity > 0.85, link instead of duplicating; if 0.6–0.85, encode with explicit `near_duplicate_of` link.
3. **Consolidation is one-way and slow.** Episodic → semantic only after ≥3 instances and ≥1 consolidation cycle. Semantic → episodic is not allowed (semantic memories are abstractions; demoting them re-introduces context they no longer have).
4. **Forgetting requires a reason.** No reason → no forget. The reason is recorded.
5. **Rehearsal opens a reconsolidation window.** Any content change within ~5 minutes of a retrieve/rehearse is flagged as potential reconsolidation_drift.
6. **Untagged retrieval mode is treated as recall and flagged.** The skill doesn't silently default — defaults are recorded as a fidelity signal.
7. **Every operation is recorded.** Pass through `record_operation()` so the MemoryIntegrityLayer sees it. Silent operations poison the integrity signal.
8. **Dream-contamination memories are quarantined.** When `runtime/dream_contamination.py` flags an interval as a contamination window, encodes during that window are tagged `provenance=dream` and source_confidence is capped at 0.4.

## Safety

- **Source-confidence floor:** if `content_confidence - source_confidence > 0.3`, the encode is allowed but flagged as source-confusion risk and the brain mechanism increments its counter.
- **Pattern-separation guard:** similarity check against the most recent N=200 episodes; cosine or Jaccard depending on what's available. Above 0.85 threshold → no new memory, just link.
- **Hoarding cap:** episodic count above HOARDING_THRESHOLD (default 10000) without recent forget operations triggers a pattern alert.
- **Consolidation gate:** only promotes patterns with ≥3 supporting episodes; semantic write requires safeguard.can_perform("memory_promote").
- **Reconsolidation window:** 5-minute window after a rehearse during which content changes are flagged.
- **Forgetting:** routes through `safeguard.can_perform("memory_forget", reason=...)`. Without a reason it fails closed.

## Trust Level

**restricted** — memory operations are persistent and shape future cognition. Per `skills/dispatcher.py`, encode and retrieve are unrestricted but `consolidate` and `forget` go through approval, and any operation flagged with a fidelity warning routes through `safeguard.can_perform()` before completing.

## How this skill fits the system

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/memory-management/SKILL.md` (this file) | Policy: what counts as encode/retrieve/consolidate/forget/rehearse, what the invariants are, what failure modes look like |
| Tier 1 implementation | `runtime/memory.py :: WorkingMemory` | Working buffer, capacity-limited deque |
| Tier 2 implementation | `runtime/memory.py :: EpisodicMemory` (SQLite-backed) | Per-event store with timestamp, source, links |
| Tier 3 implementation | `runtime/semantic_memory.py`, `brain/three_tier_memory.py` | Cortical-analog abstractions |
| Consolidation | `skills/memory_consolidation.py`, `runtime/memory_rehearsal.py` | Episodic → semantic transfer over offline cycles |
| Contamination guard | `runtime/dream_contamination.py` | Dream/sleep-state intrusion detection — gates encoding source_confidence |
| Tension | `runtime/epistemic_tension.py` | New-vs-known conflict; surfaces interference |
| Brain mechanism | `brain/mechanisms/memory_integrity_layer.py` | Runtime monitor: watches the six failure modes, scores integrity, IPW handshake when sustained |
| Safety gate | `skills/safeguard.py` | Allow/block decision when MemoryIntegrityLayer raises a sustained alert |

When wiring time arrives:

1. Agent decides to encode, retrieve, consolidate, forget, or rehearse.
2. Caller asks `MemoryIntegrityLayer.should_block(op, **kwargs)`. If True (e.g., forget without reason, semantic write without enough support, encoding during dream-contamination window without quarantine flag) → halt or require approval.
3. Operation happens through the appropriate runtime module.
4. Caller invokes `MemoryIntegrityLayer.record_operation(op, ...)`. The layer updates its rolling state, runs the failure-mode detectors, and stores the record.
5. State publishes to TSB so other mechanisms can read whether memory integrity has been drifting.
6. Sustained failure (e.g., consolidation_deficit count rises for many ticks, or source_confusion is recurrent) routes through `IdentityProposalWriter` — the agent's memory practices have drifted in a way that's identity-relevant.

## What this skill is *not*

- Not a vector database. The skill doesn't dictate the storage backend; it dictates the policy. SQLite + optional embeddings is what's currently behind it.
- Not the consolidation algorithm. That's `skills/memory_consolidation.py`. This skill specifies *when* consolidation is allowed and *what* the floor is.
- Not the safeguard. That's `skills/safeguard.py`. This skill says what gets routed through safety; it doesn't make the allow/block decision itself.
- Not infallible memory. The whole point is that memory is fallible in specific predictable ways and the system should know it.
