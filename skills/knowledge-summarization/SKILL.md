---
name: knowledge-summarization
version: 2.0.0
description: "Compression with fidelity. Use this skill whenever the agent needs to summarize a long article, condense a conversation, extract key points from documents, generate a briefing from multiple sources, digest research, or otherwise reduce a large body of information to its load-bearing structure. Each compression is intent-tagged, source-tracked, and fidelity-checked: hedging language must survive, contradictions must be preserved, claims must be in the source. The whole point isn't shorter text — it's faithful compression."
tags: [summarize, compression, briefing, extraction, fidelity]
triggers: [summarize, condense, brief, extract, key points, gist, digest, tldr, what's this about]
---

# Compression with Fidelity (knowledge-summarization)

## What this is

This isn't a generic summarizer. It's the agent's **act of compression** — taking a large body of source material and reducing it to its load-bearing structure while keeping faith with what was actually there.

Every compression is four things at once:

- **A reduction** — most of the source is being dropped, intentionally
- **A judgment** — what counts as load-bearing vs. what counts as fluff is a choice
- **A risk** — the dropped content is gone from the reader's view; the summary IS the source for them
- **A fidelity check** — what survived must actually be what was said, not what would have made the summary cleaner

The failure modes here aren't drift or overconfidence — they're specific to compression:

- **Confidence laundering** — source says "might be X / possibly Y / some studies suggest"; summary says "is X / Y / studies show"
- **Structural smoothing** — source has contradiction or tension; summary picks one side without acknowledging
- **Hallucination via interpolation** — coherent-sounding text in the summary that wasn't in the source
- **Critical drop** — short summary of long source on high-stakes intent compressed past where the load-bearing detail survived
- **Recency/primacy bias** — first/last paragraphs get weight that the middle didn't deserve to lose

So this skill is paired tightly with three other parts of the system:

- `skills/safeguard.py` — gates whether a summary can be published; sustained low-fidelity flags route to approval
- `brain/mechanisms/compression_fidelity_layer.py` — the brain-side mechanism that tracks compression ratio, hedging preservation, contradiction preservation, and fidelity over time
- `skills/data-analysis/` and `brain/mechanisms/inference_integrity_layer.py` — sister skill, sister mechanism. Different act (compression vs. inference), same epistemic care.

## Capabilities

- `summarize_text(text, intent)` — compress a single source with intent tagging
- `extract_key_points(text)` — pull out the load-bearing claims with their hedging intact
- `generate_briefing(sources, intent)` — multi-source digest (each source separately tracked)
- `record_compression(intent, source_hash, source_len, summary_len, fidelity_signals)` — persist the compression to ABM + CompressionFidelityLayer

## Intent categories

Every compression must be tagged with one of these. The CompressionFidelityLayer reads patterns over time:

- **brief** — short summary for action ("what does this mean for me right now?")
- **extract** — pull out specific facts/claims (highest fidelity bar)
- **digest** — comprehensive summary preserving structure
- **synthesize** — combine multiple sources into one coherent view (highest hallucination risk)

If a compression doesn't fit one of these, that's information — usually means the request wasn't well-formed.

## Parameters

```json
{
  "name": "summarize_text",
  "description": "Compress source material with intent tagging and fidelity tracking.",
  "parameters": {
    "text": {"type": "string", "description": "Source text to compress", "required": true},
    "intent": {"type": "string", "enum": ["brief", "extract", "digest", "synthesize"], "required": true},
    "max_length": {"type": "integer", "description": "Max output length in words", "default": 150},
    "preserve_hedging": {"type": "boolean", "description": "Force hedging-word preservation (extract default true)", "default": true}
  }
}
```

## Output Format

```json
{
  "intent": "extract",
  "summary": "...",
  "key_points": ["..."],
  "compression_ratio": 0.08,
  "fidelity_signals": {
    "source_hedge_count": 5,
    "summary_hedge_count": 4,
    "source_contradiction_markers": 2,
    "summary_contradiction_markers": 2,
    "hedge_preservation_rate": 0.8,
    "contradiction_preserved": true,
    "potential_hallucinations": []
  },
  "caveats": ["section X had to be dropped due to length", "..."],
  "confidence": 0.85
}
```

## Invariants

1. **Hedging language must survive.** If the source says "might be" or "possibly" or "some evidence suggests," those qualifiers have to appear in the summary. Stripping hedging is confidence laundering and is the most common compression-fidelity failure.
2. **Contradictions must be preserved or explicitly flagged.** If the source has tension, the summary either keeps the tension or names it ("the source contradicts itself on X"). Smoothing is misrepresentation.
3. **Claims must be in the source.** Specific numbers, proper nouns, and verbatim phrases that appear in the summary must appear in the source. The CompressionFidelityLayer flags potential hallucinations heuristically; full semantic check requires LLM verification but heuristic-flag covers the obvious cases.
4. **High-stakes compression has a floor.** `extract` intent must have ≥5% retention or explicit operator approval. `synthesize` intent compressing >90% requires multiple-source verification.
5. **Caveats are not optional.** When sections of the source had to be dropped, the summary names what was cut.
6. **Tag every compression.** Untagged compressions fail closed. The agent doesn't summarize without naming what kind of summary it is.
7. **Record every compression.** Pass through `record_compression()` so the operation lands in ABM and updates the CompressionFidelityLayer. Silent compressions poison the fidelity signal.

## Safety

- Hedging-preservation default: ON for `extract`, ON for `digest`, OFF allowed for `brief` (with operator note)
- Hallucination heuristic: words in summary that look like proper nouns or specific numbers AND don't appear in source → flagged in `potential_hallucinations`
- Contradiction-marker check: count of contradiction markers (`but`, `however`, `although`, `yet`, `whereas`, `conflicts with`) in source vs summary; if source >2 and summary 0, flagged as `structural_smoothing`
- Compression-ratio floor: `extract` < 5% retention requires approval; `synthesize` < 10% requires multiple sources

## Trust Level

**trusted** for `brief` and `digest` (lower stakes — humans can re-read); **restricted** for `extract` and `synthesize` (these become canonical references). Per `skills/dispatcher.py`, `extract` and `synthesize` go through approval; `brief` and `digest` are unrestricted.

## How this skill fits the system

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/knowledge-summarization/SKILL.md` (this file) | Contract: what compression means, intent categories, fidelity invariants |
| Brain mechanism | `brain/mechanisms/compression_fidelity_layer.py` | Runtime monitor: per-compression fidelity scoring, hedge/contradiction preservation tracking, hallucination heuristics, IPW handshake |
| Safety gate | `skills/safeguard.py` | Allow/block decision when sustained low fidelity is detected |

When wiring time arrives:

1. Agent decides to compress (e.g. summarize a research article).
2. Caller asks `CompressionFidelityLayer.should_block(intent, source_len, target_len)`. If True (extract under retention floor, etc.) → halt or require approval.
3. Compression happens.
4. Caller invokes `CompressionFidelityLayer.record_compression(intent, source_text, summary_text, ...)`. The layer computes fidelity signals heuristically and stores the record.
5. State publishes to TSB so other mechanisms can read whether fidelity has been drifting.
6. Sustained low fidelity (rolling fidelity score below threshold) routes through `IdentityProposalWriter` — the agent's compressions are systematically over-compressing, smoothing, or hallucinating. That's identity-relevant data.
