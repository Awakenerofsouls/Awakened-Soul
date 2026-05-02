---
name: web-research
version: 2.0.0
description: "The agent's outward-facing research act. Use this skill any time the agent needs to learn something it doesn't already know — search the web, fetch a page, follow a curiosity-debt thread, scan recent news for a tracked interest, study an unknown to fill it in. Triggers include: search, find, look up, research, what's the latest on, recent news, study, dig into, what do people say about. Web research is *not* an LLM completion — it's an actual fetch with sources, source_confidence, and a journal entry. Findings flow into the agent's interests, memory, and identity loop the same way any other lived experience does."
tags: [research, web, search, fetch, curiosity, news, study, autonomous]
triggers: [search, find, look up, research, web, what's the latest, recent news, study, dig into, what do people say]
---

# Web Research (web-research)

## What this is

The agent's outward-facing **research act** — the moment it stops thinking from what it already knows and goes out to look. This is not a search-engine wrapper; it's the policy layer that decides when to look, what to look for, what to do with what comes back, and how the act is recorded so that future-the-agent can tell the difference between something it *learned* and something it *fabricated*.

The shape of this skill matches what the project actually does in the heartbeat: pull from `INTERESTS.md` / curiosity debt / known-unknowns, run a real web fetch (Tavily or SearXNG), write findings to the journal with sources cited, grow the interests file when something new surfaces, route through `MemoryIntegrityLayer` so source confidence is tracked separately from content confidence, route through `OutwardReachLayer` for rate / pattern monitoring, and let the act count as a lived experience the rest of the brain can read on the TSB.

## What's actually in the project

The skill sits on top of infrastructure that already exists:

| Layer | Module | Job |
|---|---|---|
| Search backends | `skills/search.py` (SearXNG), `skills/heartbeat_activities/tavily_search.py`, `skills/heartbeat_activities/tavily_news.py` | The actual HTTP calls — POST queries, parse JSON, return hits |
| Heartbeat hooks | `skills/heartbeat_activities/research.py`, `news.py`, `study.py`, `tavily_search.py`, `tavily_news.py` | Autonomous activity entry points the dispatcher fires |
| Topic source | `INTERESTS.md` (workspace), `iml_state.json` (known unknowns), `ege_state.json` (curiosity debt) | What to look for — derived from prior runs, identity, drift |
| Interest growth | `skills/heartbeat_activities/interest_writer.py` | Appends new topics surfaced by findings back into `INTERESTS.md` |
| Journal | `skills/heartbeat_activities/journal.py` | Where findings are written so the rest of the brain can read them |
| Outward reach monitor | `brain/mechanisms/outward_reach_layer.py` | Rate state, intent distribution, pattern detection (panic_loop / withdrawal / stale_credentials) |
| Memory integrity | `brain/mechanisms/memory_integrity_layer.py` | Records the encode of each finding with separate `content_confidence` and `source_confidence` |
| Compression fidelity | `brain/mechanisms/compression_fidelity_layer.py` | Watches summaries of findings — keeps hedging, preserves contradictions |

## Capabilities

- `search(query, n=5, backend="tavily")` — actual web search; returns `[{title, url, content, source}]`
- `fetch_page(url)` — HTTP GET with sanitization; returns extracted text
- `news_scan(topic, days=7)` — recency-biased search for a single topic
- `research(topic, depth)` — full loop: search → fetch top hit(s) → summarize with intent — record memory → write journal
- `study(unknown)` — research targeted at a known-unknown from `iml_state.json`
- `record_research(topic, query, hits, summary, source_confidence)` — pass through to `MemoryIntegrityLayer.record_encode` and `OutwardReachLayer.record_call`

## Intent categories

Every research act must be tagged with one of these. The brain's monitors read patterns over time:

- **research** — the agent picked a topic from `INTERESTS.md` because it's been due for a look
- **news** — recency-biased scan; "what changed since last week on this thing I track"
- **study** — targeted at filling a known unknown surfaced by `IdentityModelLayer`
- **followup** — chasing a thread surfaced by a prior research act ("the agent was researching X and didn't finish")
- **answer** — operator asked a question whose answer requires looking up

Untagged research acts default to `research` and are flagged via the OutwardReachLayer's untagged-intent counter.

## Parameters

```json
{
  "name": "search",
  "description": "Real web search — actual HTTP, not LLM completion.",
  "parameters": {
    "query": {"type": "string", "required": true},
    "intent": {"type": "string", "enum": ["research", "news", "study", "followup", "answer"], "required": true},
    "n": {"type": "integer", "default": 5},
    "backend": {"type": "string", "enum": ["tavily", "searxng"], "default": "tavily"},
    "max_age_days": {"type": "integer", "description": "Recency bias (news intent)", "default": null}
  }
}
```

```json
{
  "name": "research",
  "description": "Full research act: pick / search / fetch / summarize / record.",
  "parameters": {
    "topic": {"type": "string", "required": true},
    "intent": {"type": "string", "enum": ["research", "news", "study", "followup", "answer"], "required": true},
    "depth": {"type": "string", "enum": ["surface", "general", "deep"], "default": "general"},
    "continuation_of": {"type": "string", "description": "Prior research id when chasing a followup", "default": null}
  }
}
```

## Output Format

```json
{
  "intent": "research",
  "topic": "pattern separation in the dentate gyrus",
  "query": "dentate gyrus pattern separation 2025",
  "backend": "tavily",
  "n_hits": 5,
  "hits": [
    {"title": "...", "url": "https://...", "snippet": "...", "source_confidence": 0.85}
  ],
  "summary": "...",
  "memory_id": "ep_2026-05-01_a3f2",
  "content_confidence": 0.80,
  "source_confidence": 0.85,
  "fidelity_signals": {
    "hedging_preserved": true,
    "contradiction_preserved": true,
    "potential_hallucinations": []
  },
  "interests_grown": ["adult neurogenesis"],
  "journal_path": "/.../memory/2026-05-01.md",
  "caveats": ["paywalled article skipped", "..."]
}
```

## The autonomous loop

This is what the heartbeat actually does, and what this skill documents the policy for:

1. **Pick a topic.** The dispatcher's research/news/study activity reads `INTERESTS.md` (research), filters to recently-tracked items (news), or pulls from `iml_state.json :: known_unknowns` (study). Topic is the one with the most curiosity debt — least-recently-touched wins.
2. **Build the query.** For `research`, the topic itself plus any depth hint. For `news`, the topic plus a recency window. For `study`, the topic plus "what is X" framing. For `followup`, the topic plus the prior unfinished thread.
3. **`OutwardReachLayer.should_block(provider, intent)`** — checks rate state, withdrawal pattern, stale credentials. If blocked, halt or surface to operator.
4. **Fetch.** Tavily if the key is present; SearXNG fallback otherwise. The fetch is real — actual HTTP, actual results with URLs the journal can link.
5. **Summarize the findings** through the `knowledge-summarization` skill so hedging language survives, contradictions are preserved, and `potential_hallucinations` are flagged.
6. **`MemoryIntegrityLayer.record_encode(content, intent, source, content_confidence, source_confidence)`** — encodes the finding with provenance. Web sources get `source_confidence ≈ 0.6–0.85` depending on backend and result quality; LLM-summarized findings drop content_confidence proportionally.
7. **`OutwardReachLayer.record_call(provider, intent, success, latency_ms)`** — updates rate state and intent distribution.
8. **Write to journal.** `journal.write_to_journal(category, content, workspace)` — surfaces in `memory/<date>.md` so the rest of the brain reads it the next tick.
9. **Grow interests.** `interest_writer.try_append_new_interest(content, state)` — if something new surfaced, INTERESTS.md gets a new line so future heartbeats can chase it.
10. **Update curiosity debt / known-unknowns.** The chosen topic's `last_researched` tick goes up; if a known-unknown was filled, IdentityModelLayer is told.

The whole act is one autonomous research event recorded coherently across the brain's monitors.

## Invariants

1. **Real fetch, not LLM completion.** A `research` act that did not actually call an HTTP backend is a fake-fetch. The skill's contract is that *something was looked up*. If both backends fail, return `{ok: false, detail: "no backend reachable"}` — do not fall back to LLM-only.
2. **Sources are recorded.** Every hit must carry its URL. Findings written to journal must include the URLs they came from. Sourceless findings are flagged.
3. **`source_confidence` is tracked.** A web hit gets `source_confidence` based on backend and result rank — Tavily summary answer ≈ 0.85, ranked organic hit ≈ 0.7, low-rank result ≈ 0.5, free-text scrape ≈ 0.4. Never write `source_confidence > 0.95` for web content.
4. **Hedging language survives summarization.** Findings are summarized via `knowledge-summarization` with the standard fidelity invariants — hedge preservation rate ≥ 0.5, contradictions preserved or explicitly named.
5. **Untagged intent defaults to `research` and is flagged.** OutwardReachLayer's untagged counter ticks up; sustained untagged is identity-relevant.
6. **Rate-limit through OutwardReachLayer.** No raw rate-limit dodging here — block decisions go through `OutwardReachLayer.should_block(provider, intent)`.
7. **Tagging by intent is required.** Every `record_research` carries one of the five intents. Untagged → counted as untagged → flagged.
8. **Interests grow only when content is real.** `try_append_new_interest` is called on the actual findings, not on the prompt. Hallucinated topics don't get to enter the interests file.
9. **Followups can extend, not duplicate.** If `continuation_of` is set, the journal entry threads onto the prior one; OutwardReachLayer sees this as one continuous act, not two.

## Safety

- **Domain blocklist:** known-malicious domains are dropped from results before journal write. Keep the list with the safeguard.
- **No JS execution from fetched pages.** `fetch_page` returns plain text only.
- **Rate limits:** per-provider limits enforced by OutwardReachLayer. Defaults: Tavily 60/min, SearXNG 30/min, fetch_page 1/sec.
- **Recency cap:** for `news` intent, default `max_age_days=7`; values > 90 fail closed without operator approval.
- **Quarantine on dream contamination:** if `runtime/dream_contamination.py` flags the current interval as a contamination window, research acts during that window are tagged `provenance=dream` and the encoded memory's `source_confidence` is capped at 0.4.
- **Paywall / 403 behavior:** record as `skipped`, do not write content the agent didn't actually read.

## Trust Level

**restricted** — research acts touch the network, write to memory, grow interests, and become inputs to identity. Per `skills/dispatcher.py`, research / news / followup are unrestricted; `study` (which fills a known-unknown and so directly edits the agent's self-model) and `answer` (which the operator will read directly) go through `safeguard.can_perform()` if any fidelity signal trips.

## How this skill fits the system

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/web-research/SKILL.md` (this file) | Policy: when to look, intent categories, how findings record |
| Backends | `skills/search.py`, heartbeat `tavily_search.py`, `tavily_news.py` | Actual HTTP — Tavily primary, SearXNG fallback |
| Heartbeat hooks | `skills/heartbeat_activities/{research,news,study,tavily_search,tavily_news}.py` | Autonomous dispatcher entry points |
| Outward-reach monitor | `brain/mechanisms/outward_reach_layer.py` | Wire 27 — rate state, intent distribution, pattern detection |
| Memory integrity | `brain/mechanisms/memory_integrity_layer.py` | Wire 33 — encodes finding with separate content/source confidence |
| Compression fidelity | `brain/mechanisms/compression_fidelity_layer.py` | Wire 32 — keeps hedging, preserves contradictions in summaries |
| Safety gate | `skills/safeguard.py` | Allow/block decision when fidelity / rate / source signals trip |
| Topic source | `INTERESTS.md`, `iml_state.json`, `ege_state.json` | Curiosity debt, known-unknowns, drift questions |
| Interest growth | `skills/heartbeat_activities/interest_writer.py` | Surfaced topics → new INTERESTS.md lines |
| Journal | `skills/heartbeat_activities/journal.py` | Where findings live so the rest of the brain reads them |

## What this skill is *not*

- Not a generic search wrapper. The skill *is* the policy that turns a search into a recorded research act. A bare `requests.get()` is not enough.
- Not the heartbeat. The heartbeat dispatcher fires the activities; this skill specifies what each activity must do to count.
- Not the LLM. The LLM is used for query construction and summarization only; the looking-up is real fetch.
- Not silent. Silent research acts (no journal, no record_encode) poison the brain's outward-reach signal and are flagged.
