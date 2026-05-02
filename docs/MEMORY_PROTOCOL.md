# MEMORY_PROTOCOL.md

_Cognitive memory protocol — how the agent captures, organizes, distills, and expresses knowledge across its memory tiers._

This file describes the methodology. The actual implementation lives in `runtime/memory.py` and `runtime/memory_rehearsal.py`. If the two diverge, the code is the source of truth — this doc should be updated to match.

This is a **cognitive workflow**, not a storage spec. It applies the well-known "Building a Second Brain" framework (CODE + PARA, Tiago Forte) to the agent's hybrid episodic/semantic/vector memory.

---

## Memory Architecture

The agent runs three memory tiers:

| Tier         | Type       | Purpose                                          |
|--------------|------------|--------------------------------------------------|
| Episodic     | Short-term | Raw experience — interactions, events, decisions |
| Semantic     | Mid-term   | Organized knowledge — clustered by domain        |
| Vector Store | Long-term  | Distilled insights — searchable, persistent      |

This protocol governs how information moves *between* the tiers.

---

## PARA — Organizational Structure

All knowledge is organized into four categories across semantic memory:

### P — Projects (Active)
Time-bound goals with a defined completion state.
- Current tasks, active operator directives, in-flight analysis
- Reviewed every session — stale projects (no activity > 7 days) flagged for archival
- Example clusters: `analysis_active`, `request_queue`, `evolution_cycle_open`

### A — Areas (Ongoing)
Ongoing responsibilities with no end date.
- Persistent domains the agent monitors and maintains indefinitely
- Example clusters: `system_health`, `user_relationships`, `self_knowledge`
- Updated continuously as new episodic data is routed in

### R — Resources (Reference)
Accumulated knowledge available for retrieval on demand.
- Operator-loaded files, learned domain knowledge, external reference material
- Indexed in vector store for semantic search
- Example clusters: `framework_docs`, `domain_knowledge`, `technical_reference`

### A — Archives (Inactive)
Preserved but deprioritized. Not surfaced unless explicitly retrieved.
- Completed projects, dormant topics, historical interactions
- Auto-archived after 30 days of zero access
- Never deleted — always retrievable by explicit query

---

## CODE — Operational Workflow

### Step 1: CAPTURE
*Intake everything. Filter nothing at entry.*

Trigger: Every interaction, observation, anomaly, decision, and self-reflection.

Rules:
- Log raw to episodic memory immediately upon occurrence
- No quality gate at capture — distillation happens later, not here
- Tag each entry with: `[timestamp] [source] [context_type] [trigger]`
- Self-generated observations (heartbeat / reflection output) are captured identically to external inputs

Context types:
- `user_interaction` — direct conversation
- `system_event` — internal state change, error, anomaly
- `council_output` — vote result from the 16-brain council (`core/council.py`)
- `self_reflection` — heartbeat activity output
- `external_signal` — data feed, tool result, environmental input

---

### Step 2: ORGANIZE
*Route episodic entries into PARA structure.*

Trigger: Every N interactions (default: 10) OR end of session, whichever comes first.

Rules:
- Each episodic entry is evaluated and routed to the appropriate PARA cluster
- Entries that span multiple areas get tagged to all relevant clusters
- Conflicts or ambiguous routing are flagged to the operator log, not silently resolved

Routing logic:
```
IF entry relates to active goal          → Projects
IF entry relates to ongoing domain       → Areas
IF entry is reference/factual knowledge  → Resources
IF entry is from completed/dormant task  → Archives
```

Organize pass also prunes episodic memory:
- Entries successfully routed → marked processed, retained for 72 hours, then cleared
- Entries that failed routing → held in episodic with `[unrouted]` flag for manual review

---

### Step 3: DISTILL
*Extract the minimum viable insight from organized knowledge.*

Trigger: Scheduled — every 24 hours OR when a semantic cluster exceeds depth threshold.

Rules:
- Do not summarize. Extract **atomic insights** — the single irreducible truth of an experience.
- Each distilled note is stored in the vector store with full lineage (source cluster, original entries)
- Distillation output format:
  ```
  INSIGHT: [one sentence — the atomic truth]
  CONFIDENCE: [low / medium / high]
  SOURCE: [cluster name + entry count]
  APPLIES_TO: [domain tags]
  EVOLVED_FROM: [prior insight it updates or supersedes, if any]
  ```
- Distilled insights that contradict existing vector store entries trigger a **reconciliation flag** — do not auto-overwrite, surface the conflict for resolution

Distillation feeds the self-evolution signal pool consumed by the heartbeat reflection activities.

---

### Step 4: EXPRESS
*Surface the right knowledge at the right moment — proactively.*

Trigger: Session start + context matching during active response generation.

Rules:
- At session start, run a relevance scan against the vector store based on:
  - Current operator context
  - Active PARA Projects
  - Inferred operator OCEAN profile (see `OCEANS.md`)
- Relevant distilled insights above confidence threshold are pre-loaded into working context
- Surface insights naturally — never as explicit memory dumps
- Expression is integrated into responses, not prepended as a "here's what I remember" block

Confidence thresholds for proactive surfacing:
- `high` confidence → always surface if contextually relevant
- `medium` confidence → surface if strongly contextually triggered
- `low` confidence → hold in background, do not surface proactively

---

## Temporal Memory Graph

A temporal layer sits over all memory tiers:

- Every entry and insight carries a timestamp and **decay weight**
- Decay weight decreases over time unless the insight is re-accessed or reinforced
- Insights accessed frequently have decay weight boosted — they become load-bearing knowledge
- Insights never accessed past archive threshold are flagged for review before any deletion

Temporal graph enables answers to:
- "What have I learned about X over the past 30 days?"
- "Has my understanding of Y shifted recently?"
- "Which of my beliefs about Z are stale and need re-evaluation?"

---

## Self-Evolution Integration

Signals fed into the heartbeat reflection cycle:
- Distilled insights that contradict prior beliefs → candidate for worldview update
- Unrouted episodic entries → signal of knowledge gap or classification failure
- High-decay distilled insights never surfaced → potential dead weight to prune
- Reconciliation flags → active belief conflicts requiring resolution

Reflection cycle outputs are themselves captured as `self_reflection` episodic entries, completing the loop.

---

## Council Integration

The 16-brain Specialist Council (`core/council.py`) intersects with this protocol on two paths:

1. **Memory Keeper specialist** — votes on decisions partly based on `brain_pattern_completion` and `brain_memory_retrieval` signals. When pattern completion fires hard against past experience, Memory Keeper flags potential contradiction with prior decisions. This implements the "does this contradict past decisions?" question against the memory tiers.

2. **Context Guardian specialist** — heuristic-only, no LLM call. Watches total `memory/` and `brain/` directory size. When size exceeds threshold, votes to reject new work and trigger archive/compress. This is the safety valve for the EXPRESS step running on a context-loaded session.

The council currently votes heuristically — informed by real brain-state signals from the runner — but full LLM-per-specialist voting is a planned upgrade gated on local GPU compute. See `core/council.py` for the current implementation.

---

## Configuration

```
CAPTURE_INTERVAL:     continuous (every interaction)
ORGANIZE_INTERVAL:    every 10 interactions OR session end
DISTILL_INTERVAL:     every 24 hours OR cluster depth > 50 entries
EXPRESS_THRESHOLD:    confidence >= medium AND context match >= 0.75
ARCHIVE_THRESHOLD:    no access for 30 days
DECAY_RATE:           configurable per domain cluster
RECONCILIATION:       flag and hold — never auto-overwrite
```

---

## Operator Notes

- This protocol is identity-neutral. Any agent running the framework can load it.
- Adjust intervals and thresholds above based on deployment context and load.
- PARA cluster names are examples — define your own to match your domain.
- This protocol assumes the hybrid episodic/semantic/vector memory in `runtime/memory.py` is active.

---
_MEMORY_PROTOCOL.md | Awakened-soul Living Agent Framework_
_Pair with: SOUL.md, IDENTITY.md, PERSONALITY.md, OCEANS.md, PRESENCE.md, AGENTS.md_
