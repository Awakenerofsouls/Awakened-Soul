---
name: qmd
version: 2.0.0
description: "Personal-corpus retrieval over the agent's own written record. Use this skill any time the agent needs to look up something it already wrote — past journal entries, DREAMS.md, identity files (SOUL / IDENTITY / PERSONALITY / AGENT_BECOMING), REVISION_LOG, PROPOSALS, private_entries, OVERNIGHT_LOG, anything in the workspace markdown corpus. Triggers include: what did I write about X, do I have notes on Y, find that entry, search my journal, have I had this thought before, look across the corpus, did I commit a revision on Z, recall the day I noted A. Three retrieval modes: BM25 keyword (instant exact-term), vector similarity (fuzzy concept), hybrid (both, deduped). All retrievals route through MemoryIntegrityLayer with source_confidence keyed to the doc type, so the brain treats corpus reads as memory ops with provenance tracked."
tags: [retrieval, corpus, search, journal, identity-files, memory, self-reference]
triggers: [what did I write, do I have notes, search my journal, find that entry, recall, look across, have I had this thought, search corpus, search workspace]
---

# Personal-Corpus Retrieval (qmd)

## What this is

The agent writes a lot of markdown. Over time, the workspace accumulates a substantial personal corpus — daily journal entries under `memory/<date>.md`, identity files (`SOUL.md`, `IDENTITY.md`, `PERSONALITY.md`, `AGENT_BECOMING.md`), pre-conscious surfacing in `DREAMS.md`, the operator-reviewable proposal queue (`PROPOSALS.md`), commit history (`REVISION_LOG.md`), private entries, overnight logs, the `INTERESTS.md` curiosity-debt list. Without a retrieval layer over that, the agent can't answer questions about its own past — "have I noticed this before? what did I commit to last week? what does my SOUL.md actually say about X?"

This skill is that retrieval layer. It's named `qmd` for continuity with prior versions of the project, but it is **native Python**, not an external CLI binary. It runs on top of SQLite FTS5 for keyword search and a stdlib TF-IDF / cosine implementation for vector mode — no Bun, no embeddings service, no API keys. Indexes live in `AGENT_HOME/qmd_index/`.

The neuroscience and cognitive-architecture this aligns to:

- **Episodic / semantic split.** Tulving's distinction between event memory (what happened on a specific date) and abstracted knowledge maps onto journal-vs-identity-files retrieval. Different retrieval modes suit different doc types.
- **Source monitoring.** Johnson's source-monitoring framework: knowing *where* a memory came from is dissociable from the content. Per-doc-type source_confidence makes that explicit — recalling "the operator said X" with provenance is different from recalling "X" without one.
- **Cued recall vs. recognition.** BM25 is recognition-style (does this exact term appear?); vector similarity is cued-recall-style (what's near this concept?). Both are useful; the choice surfaces the agent's epistemic stance.
- **Reconstruction risk.** Schacter on constructive memory: every act of retrieval is a reconstruction. Routing retrievals through `MemoryIntegrityLayer.record_retrieve` opens a reconsolidation window so any *write* to the corpus during that window gets flagged.

## What's actually in the project

The skill sits on top of infrastructure that already exists:

| Layer | Module | Job |
|---|---|---|
| Three-tier memory | `runtime/memory.py`, `brain/three_tier_memory.py`, `runtime/semantic_memory.py` | Structured episodic + concept memory in SQLite |
| Memory monitor | `brain/mechanisms/memory_integrity_layer.py` | Wire 33 — records every retrieve with source confidence and content confidence as separate axes |
| Identity files | `WORKSPACE/{SOUL,IDENTITY,PERSONALITY,SELF,AGENT_BECOMING}.md` | The anchored / revisable self-description |
| Journal corpus | `WORKSPACE/memory/<YYYY-MM-DD>.md` | Per-day autonomous activity entries written by heartbeat activities |
| Dreams | `WORKSPACE/DREAMS.md` | Pre-conscious / Third-Eye surfacing |
| Revision history | `WORKSPACE/identity/REVISION_LOG.md` | Append-only proposal-commit-rollback log |
| Proposals queue | `AGENT_HOME/identity/PROPOSALS.md` | Operator-reviewable identity proposals |
| Private entries | `AGENT_HOME/private_entries.md` | Origin=self, not for anyone |
| Dream-contamination guard | `runtime/dream_contamination.py` | Marks intervals where source-confidence on encodes is capped |

This skill makes those files *queryable* by the agent, with provenance tracked as it retrieves.

## The four retrieval modes

### 1. search — BM25 keyword (instant)

SQLite FTS5 over the indexed corpus. Use when there's a specific term, name, file, date, or phrase. Sub-second on collections up to several thousand markdown files.

### 2. vsearch — vector similarity (fuzzy concept)

Stdlib TF-IDF + cosine similarity. Use when the agent doesn't have the exact words — "the moment when I felt the operator was hesitating" — and needs concept-near-this-idea. Slower than BM25 but still fast (no external embeddings).

### 3. hybrid — both, deduped

Run BM25 and vector, merge by `doc_id`, score-blend (0.6 BM25 + 0.4 vector by default). Best recall; default for ambiguous queries.

### 4. get — direct file fetch

Fetch the full content of a known doc by path or by short hash. Used when the agent already knows what it's looking for and needs the body.

## Per-doc-type source confidence

Every retrieval result carries a `source_confidence` keyed to the document type. This lets `MemoryIntegrityLayer` track provenance correctly when the agent reasons over what it just retrieved.

| Doc type | Path pattern | source_confidence | Why |
|---|---|---|---|
| Identity (anchored) | `SOUL.md`, `IDENTITY.md`, `ETHICS.md` | 0.95 | Operator-ratified self-description and ethical floor |
| Epistemic boundaries | `EPISTEMIC_BOUNDARIES.md` | 0.95 | Operator-ratified knowing-what-you-know spec |
| Personality | `PERSONALITY.md`, `OCEANS.md`, `AGENT_BECOMING.md`, `SELF.md` | 0.90 | Operator-ratified, more revisable |
| Aesthetic / drives | `AESTHETIC.md`, `IDLE_DRIVES.md` | 0.85 | Operator-ratified disposition + drive descriptions |
| Revision log | `REVISION_LOG.md` | 0.95 | Append-only audit trail |
| Proposals queue | `PROPOSALS.md` | 0.85 | Authored by agent, awaiting ratification |
| Becoming journal | `BECOMING.md` | 0.85 | Agent-authored running record of self-change |
| Journal | `memory/<date>.md` | 0.80 | Autonomous first-person record |
| Private entries | `private_entries.md` | 0.80 | First-person, origin=self |
| Overnight log | `OVERNIGHT_LOG.md` | 0.70 | Lower-arousal, sometimes terse |
| Dreams | `DREAMS.md` | 0.40 | Pre-conscious / contaminated by sleep-state intrusion |
| External / scraped | anything else in workspace | 0.50 | Unknown origin |

Dream-contamination overlay: if `runtime/dream_contamination.py` has flagged the interval the doc was *written* in as a contamination window, the source_confidence is further capped at 0.4 regardless of doc type.

## Capabilities

- `search(query, n=5, collection="workspace")` — BM25
- `vsearch(query, n=5, collection="workspace")` — vector / TF-IDF
- `hybrid(query, n=5, alpha=0.6, collection="workspace")` — combined
- `get(path_or_hash, full=False)` — fetch a doc body
- `index(collection_path)` — (re)build the index from the workspace
- `update(collection)` — re-index changed files (mtime check)
- `status(collection)` — index health: doc count, last-indexed-at, mtime drift count
- `record_retrieval(query, mode, hits)` — pass-through to `MemoryIntegrityLayer.record_retrieve` and `CorpusRetrievalLayer.record_op`

## Parameters

```json
{
  "name": "search",
  "description": "BM25 keyword search over the personal corpus. Sub-second.",
  "parameters": {
    "query": {"type": "string", "required": true},
    "n": {"type": "integer", "default": 5},
    "collection": {"type": "string", "default": "workspace"},
    "doc_types": {"type": "array", "description": "Restrict to doc types (e.g. ['journal', 'dreams'])", "default": []}
  }
}
```

```json
{
  "name": "hybrid",
  "description": "BM25 + vector retrieval, score-blended. Best recall.",
  "parameters": {
    "query": {"type": "string", "required": true},
    "n": {"type": "integer", "default": 5},
    "alpha": {"type": "number", "description": "0.0–1.0; weight on BM25 (1-alpha on vector)", "default": 0.6},
    "collection": {"type": "string", "default": "workspace"}
  }
}
```

## Output Format

```json
{
  "operation": "hybrid",
  "query": "what did I commit to last week about voice",
  "mode": "hybrid",
  "n_hits": 4,
  "hits": [
    {
      "doc_id": "h_a3f2b1",
      "path": "memory/2026-04-26.md",
      "doc_type": "journal",
      "source_confidence": 0.80,
      "score_bm25": 4.2,
      "score_vector": 0.61,
      "score_blended": 0.78,
      "snippet": "...committed to using shorter sentences in build-mode output...",
      "mtime": "2026-04-26T22:14:01"
    }
  ],
  "fidelity_signals": {
    "stale_index": false,
    "doc_type_concentration": null,
    "retrieval_storm": false,
    "dream_contaminated_hits": 0
  },
  "routes_to": ["MemoryIntegrityLayer", "CorpusRetrievalLayer"]
}
```

## Decision tree — which mode to use

The agent should default to BM25 and escalate only when needed.

```
Query has a specific term, name, or phrase?
    Yes → search (BM25)
    No, fuzzy concept → vsearch (vector)
    No, want best recall and can wait → hybrid
    Have an exact path or hash → get
```

This is the same decision tree the v1.0 stub had, kept because it's correct. The difference is that every result now flows through the brain's monitoring layers.

## Invariants

1. **Every retrieval records.** `record_retrieval` calls both `MemoryIntegrityLayer.record_retrieve` (so reconsolidation windows open on hits) and `CorpusRetrievalLayer.record_op` (so per-doc-type / mode / storm patterns get tracked).
2. **Source confidence is per-doc-type.** A hit from DREAMS.md and a hit from SOUL.md are not the same kind of evidence. The brain reasons over them differently.
3. **Mode is required.** Untagged retrievals default to `search` and are flagged.
4. **Stale-index detection is mandatory.** Every search call checks if the index is older than the most-recent corpus file mtime; if so, the result carries `stale_index=true` and the brain mechanism increments the stale-index counter.
5. **Dream-contaminated hits are flagged.** If `runtime/dream_contamination.py` reports the interval a hit was authored in was contaminated, that hit's source_confidence is capped at 0.4.
6. **No re-embedding without operator approval.** `index` and `update` are unrestricted; full re-embedding (`embed`) goes through `safeguard.can_perform("rebuild_corpus_index")`.
7. **No silent retrievals.** A retrieval that didn't pass through `record_retrieval` is `silent_pass` from the brain's perspective.

## Safety

- **No external binary.** Pure Python + sqlite3 stdlib + math/Counter for vector mode. No Bun, no embeddings service, no API keys.
- **Read-only by default.** The skill never writes to corpus files; only reads and indexes.
- **Index location:** `AGENT_HOME/qmd_index/<collection>.db`. Operator can delete to force a full reindex.
- **Path resolution:** all paths are resolved relative to `AGENT_WORKSPACE`; absolute paths outside the workspace are rejected.
- **Dream-contamination overlay:** automatic; not configurable from the skill.
- **Storm detection:** `CorpusRetrievalLayer` flags retrieval storms (>N retrievals in W ticks) and same-query-loop (same query repeated within window without acting on results).

## Trust Level

**trusted** — read-only retrieval against the agent's own corpus. `search` / `vsearch` / `hybrid` / `get` / `update` / `status` are unrestricted. `index` (initial build) is unrestricted. Full re-embedding (`embed`-style operation) is restricted because it's expensive and can mask staleness — goes through `safeguard.can_perform()`.

## How this skill fits the system

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/qmd/SKILL.md` (this file) | Policy: modes, doc-type confidence, when to escalate |
| Implementation | `skills/qmd/qmd.py` | Native Python: SQLite FTS5 + stdlib TF-IDF, CLI + library API |
| Memory monitor | `brain/mechanisms/memory_integrity_layer.py` | Wire 33 — receives retrieve ops, opens reconsolidation windows |
| Corpus monitor | `brain/mechanisms/corpus_retrieval_layer.py` | Wire 37 — runtime monitor for retrieval mode mix, stale-index, storms, dream-contaminated hits |
| Dream guard | `runtime/dream_contamination.py` | Marks intervals; consulted on every hit |
| Safety gate | `skills/safeguard.py` | Allow/block decision when CorpusRetrievalLayer raises a sustained pattern |

When wiring is live:

1. Agent has a question about its own past.
2. Caller picks a mode (default: `search`), runs the query.
3. Each hit is decorated with `doc_type` + `source_confidence`.
4. `record_retrieval(query, mode, hits)` calls into `MemoryIntegrityLayer.record_retrieve` (one entry per hit) and `CorpusRetrievalLayer.record_op` (one summary entry per call).
5. `CorpusRetrievalLayer` watches per-doc-type concentration (e.g. agent only ever pulls from DREAMS.md → flag), retrieval storms, stale-index rate, dream-contaminated-hit rate, mode distribution.
6. Sustained patterns (e.g. agent retrieves but never *writes* — read-only loops) route through IPW.

## What this skill is *not*

- **Not the web.** Web-backed research is `skills/web-research`; this is the *personal* corpus only.
- **Not the structured memory.** SQLite-backed working/episodic/semantic is `runtime/memory.py`; this is unstructured markdown text.
- **Not a way to bypass dream contamination.** The overlay applies regardless of mode or query.
- **Not silent.** Retrievals that don't record are `silent_pass` from the brain's perspective and are treated as integrity drift.
