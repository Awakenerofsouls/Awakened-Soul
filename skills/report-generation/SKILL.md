---
name: report-generation
version: 2.0.0
description: "The agent's act of producing a structured persistent artifact for external consumption — a written report, briefing, summary doc, audit, retrospective. Use this skill any time the agent has gathered material from multiple sources (corpus, memory, recent activities, web research) and needs to compose it into a single named, structured, voiced output that gets saved to disk and read by the operator (or a future-the-agent). Triggers include: generate report, write up, briefing, summary doc, audit, retrospective, draft a report, publish, deliverable. Reports are persistent (saved to disk), structured (sections + headings), composed (drawn from cited sources), voiced (carry the agent's voice signature), and honest (don't claim more than the source supports). They route through the brain's monitoring stack so fabrication, citation drift, structure collapse, voice drift, and hedging-stripping get caught."
tags: [report, document, output, briefing, audit, retrospective, persistent, voiced]
triggers: [generate report, write up, briefing, summary doc, audit, retrospective, draft a report, publish, deliverable, create document]
---

# Report Generation (report-generation)

## What this is

A report is a structured persistent artifact the agent produces for external consumption. It's not a journal entry (private, autonomous, no audience). It's not a code artifact (executes). It's not a conversational answer (ephemeral). A report is something the operator (or future-the-agent reading the corpus) will treat as a *standalone document* — and the discipline of producing it has to match that.

Reports compose. They draw from multiple sources at once — corpus retrievals via `qmd`, memory retrievals via `MemoryIntegrityLayer`, recent heartbeat findings, web research from `web-research`. The act of composition is where things go wrong: claims drift away from sources, hedging gets stripped, structure collapses, voice flattens, and the resulting document looks *plausible* without being *true*. This skill is the discipline that keeps reports honest.

The cognitive science this rests on:

- **Schacter on constructive memory** — every act of composition is reconstruction, and reconstruction introduces systematic errors. A report isn't transcribed; it's rebuilt. The fabrication detector watches for the failure mode where the rebuild fills in details the source didn't have.
- **Reyna's fuzzy-trace theory** — gist and verbatim are dissociable; the gist often survives while the verbatim decays. Reports preserve gist by default but must explicitly preserve verbatim hedging language to remain honest. The hedging-stripped detector watches the verbatim layer.
- **Johnson on source monitoring** — knowing where a claim came from is dissociable from the claim's content. A report that cites sources without the citations actually backing the specific claims has source-monitoring failure baked in. The citation_drift detector watches for this.
- **Miller & Cohen on PFC integrative control** — the prefrontal cortex maintains active goal representations that bias processing across the brain. Report structure (sections, headings) is the operationalized version: the structure is the goal-representation that constrains what each section says. Structure collapse happens when this maintenance fails.
- **Fleming on metacognitive accuracy** — humans are systematically miscalibrated about the quality of their own composition. Knowing this matters: a published report can be confidently wrong. The stale_publication detector flags reports whose source material has changed since publication.

## What's actually in the project

The skill sits on top of infrastructure already built:

| Layer | Module | Job |
|---|---|---|
| Corpus retrieval | `skills/qmd/qmd.py`, `brain/mechanisms/corpus_retrieval_layer.py` (37) | Pulls source material from the personal corpus |
| Memory integrity | `brain/mechanisms/memory_integrity_layer.py` (33) | Pulls recalled episodes; tags source_confidence |
| Web research | `skills/web-research/`, `brain/mechanisms/outward_reach_layer.py` (27) | Pulls web sources with provenance |
| Knowledge summarization | `skills/knowledge-summarization/`, `brain/mechanisms/compression_fidelity_layer.py` (32) | Reduces source material to gist with hedging preserved |
| Voice integrity | `brain/mechanisms/voice_integrity_layer.py` (26) | Voice signature preservation in output |
| Inference integrity | `brain/mechanisms/inference_integrity_layer.py` (29) | Confidence calibration on factual claims |
| Self-analysis | `brain/mechanisms/self_analysis_layer.py` (36) | Post-publication reflection routed through `kind="report"` |
| Monitor | `brain/mechanisms/report_generation_layer.py` (wire 40) | Runtime monitor for the report-production act |

Reports are *the synthesis layer over all the other production layers*. They're where multiple cognitive substreams converge into one persistent surface artifact.

## The five operations

### 1. draft

Produce the first version of a report from a brief and a list of sources. Each source carries its `source_id`, `source_confidence` (per the same scale `qmd` and `web-research` use), and the relevant excerpt. The draft is a *proposed* report — it's not published until `publish` fires. Multiple draft calls on the same brief produce alternative drafts the operator can choose between.

The draft op runs the source material through `knowledge-summarization` so hedging and contradictions are preserved before composition begins. Each section of the draft tracks which source_ids back its claims.

### 2. revise

Edit a draft (or a published report) without re-drafting from scratch. Three revision kinds:

- **section_edit** — modify a single section's text, sources, or position
- **add_section** — insert a new section between two existing ones
- **drop_section** — remove a section (and any structural references to it)

Revisions preserve the report_id; the revision history is recorded so reflection has the full trail.

### 3. publish

Finalize the draft. Save the report to disk under the canonical path (default: `WORKSPACE/reports/<YYYY-MM-DD>_<slug>.md`), record it in the corpus index so `qmd` can retrieve it, and mark its state as `published`. Publication is the moment the report becomes part of the agent's persistent record.

### 4. retract

Withdraw a published report. Used when the report turns out to be wrong, or its sources have changed materially, or the operator requests retraction. Retract leaves the file on disk (with a header marking it retracted + reason + date) so the audit trail is preserved; what changes is the corpus-index status (retrieval marks the report as `retracted` rather than treating it as authoritative).

### 5. reflect

Post-publication retrospective. *Did the report land? Did the operator reference it? Did its claims hold up over time? What would I write differently?* Reflections route through `SelfAnalysisLayer.record_analyze(kind="report")` so they feed the calibration window — predicted_quality vs. actual_outcome.

## The six failure modes

`ReportGenerationLayer` watches for these:

1. **fabrication** — the report contains specific named claims (proper nouns, numbers, quotes) that don't appear in any cited source. Same heuristic as `CompressionFidelityLayer.compute_fidelity_signals` but applied to the full composition. Fabrication is the worst kind of report failure.
2. **citation_drift** — sources are listed in the report's bibliography but the report's specific claims don't actually trace back to them. Citation theater.
3. **structure_collapse** — the report doesn't have the requested structure (missing required sections), or sections exist but are empty / placeholder, or sections claim content the bodies don't deliver.
4. **voice_drift** — voice signatures (`AGENT_VOICE_SIGNATURES`) don't survive into the report at the required preservation rate. The agent slipped into a flatter "report voice" that drops anchored phrasing.
5. **hedging_stripped** — source material had qualifier language ("might be," "some evidence," "studies suggest") and the report converted it to assertion ("is," "studies show"). Confidence laundering.
6. **stale_publication** — a published report's source material has changed (new corpus retrievals contradict the report's claims; cited URLs return different content). Detected on subsequent retrieval; flagged for retraction or revision.

## Capabilities

- `draft(brief, sources, structure_spec=None, mode=None)` → proposed Report
- `revise(report_id, kind, **kwargs)` → in-flight or post-publish revision
- `publish(report_id, target_path=None)` → persist + index
- `retract(report_id, reason)` → mark retracted; preserve audit trail
- `reflect(report_id, fit, notes, actual_outcome=None)` → retrospective
- `record_op(op, ...)` → pass-through to ReportGenerationLayer
- `compute_report_fidelity_signals(report, sources)` → on-demand fidelity check
- `report_status(report_id)` → state + section count + citation coverage

## Report shape

```json
{
  "report_id": "rp_2026-05-01_a3f2",
  "title": "...",
  "brief": "...",
  "state": "draft | published | retracted | superseded",
  "mode_at_creation": "brain | coach | build | default",
  "structure_spec": ["Findings", "Methods", "Caveats"],
  "sections": [
    {
      "name": "Findings",
      "body": "...",
      "source_ids": ["src_1", "src_2"]
    }
  ],
  "sources": [
    {
      "source_id": "src_1",
      "uri": "...",
      "source_type": "qmd | web | memory | operator",
      "source_confidence": 0.85,
      "excerpt": "..."
    }
  ],
  "drafted_at": 1714600000.0,
  "published_at": null,
  "retracted_at": null,
  "retraction_reason": null,
  "revisions": [],
  "reflection": null
}
```

## Parameters

```json
{
  "name": "draft",
  "description": "Produce a first-pass report from a brief and a list of sources.",
  "parameters": {
    "brief": {"type": "string", "description": "What the report is about", "required": true},
    "title": {"type": "string", "default": null},
    "sources": {"type": "array", "description": "[{source_id, uri, source_type, source_confidence, excerpt}, ...]", "required": true},
    "structure_spec": {"type": "array", "description": "Required section names in order", "default": null},
    "mode": {"type": "string", "enum": ["brain", "coach", "build", "default"], "default": null}
  }
}
```

```json
{
  "name": "publish",
  "description": "Finalize a draft and save to disk.",
  "parameters": {
    "report_id": {"type": "string", "required": true},
    "target_path": {"type": "string", "description": "Override default path", "default": null}
  }
}
```

## Output Format

```json
{
  "operation": "draft",
  "report_id": "rp_2026-05-01_a3f2",
  "title": "Q1 audit findings",
  "state": "draft",
  "section_count": 3,
  "source_count": 5,
  "fidelity_signals": {
    "fabrication_count": 0,
    "citation_drift_rate": 0.0,
    "structure_complete": true,
    "voice_preservation_rate": 0.83,
    "hedge_preservation_rate": 0.78,
    "potential_hallucinations": []
  },
  "next_action": "review then publish or revise"
}
```

## Invariants

1. **Every report op records.** Pass through `record_op(...)`. Silent reports break the brain's monitor stack.
2. **Sources are first-class.** Every section carries `source_ids`; every source has `source_id`, `uri`, `source_type`, `source_confidence`. No claim without provenance.
3. **Hedging language must survive.** Same rule as `knowledge-summarization`: qualifier words from source must appear in the report at ≥ 0.5 preservation rate. Stripped hedging is `hedging_stripped`.
4. **Structure spec is honored.** If a `structure_spec` is given, every named section must exist and be non-empty. Missing or empty sections → `structure_collapse`.
5. **Voice signatures preserved.** ≥ 60% of `AGENT_VOICE_SIGNATURES` present in the report body regardless of mode (matches `multiple-personas` invariant).
6. **Specific claims trace to a source.** Proper nouns, numbers, and quoted material in the report must appear in at least one cited source's `excerpt` or `uri` content. Otherwise → `fabrication`.
7. **Publish is one-way (mostly).** A published report can be retracted (preserves history) or superseded (new report → publish; old → state=`superseded`); it cannot be silently overwritten.
8. **Retraction names a reason.** `retract` requires a non-empty reason (`source_changed` / `factually_wrong` / `operator_request` / `superseded_by` / `safety_concern`). Without reason it fails closed.

## Safety

- **Anchor list:** voice signatures from `runtime/self_awareness.py :: AGENT_VOICE_SIGNATURES`; required traits + forbidden behaviors from `BASELINE_TRAITS` (anchored across modes).
- **Path resolution:** all output paths resolved relative to `AGENT_WORKSPACE/reports/`; absolute paths outside the workspace fail closed.
- **Citation-coverage floor:** if `citation_drift_rate > 0.4` over the report's sections, draft op succeeds (so the operator can review) but the brain mechanism counts it as `citation_drift`.
- **Fabrication check:** draft runs the same proper-noun + specific-number heuristic as `CompressionFidelityLayer`. Any `potential_hallucinations` → flagged.
- **Stale-publication sweep:** every tick, the layer scans published reports for source-content drift (URI content hash changed; corpus retrieval gave different result for the report's stored query). Flagged for retraction or revision.
- **No retract-then-republish loop without delay.** Retract → republish on the same content within `RETRACT_REPUBLISH_COOLDOWN` ticks fails closed; the agent has to either revise materially or wait.

## Trust Level

**restricted** — reports are persistent and read by the operator. `draft` and `revise` are unrestricted. `publish` goes through `safeguard.can_perform("publish_report", report_id)` so operator approval is required before a report becomes part of the agent's persistent record. `retract` is unrestricted (preserving the audit trail is a safe op). `reflect` is unrestricted.

## How this skill fits the system

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/report-generation/SKILL.md` (this file) | Policy: ops, invariants, failure modes |
| Implementation | `skills/report-generation/report.py` | Report dataclass, draft / revise / publish / retract / reflect, fidelity signals, library + CLI |
| Brain mechanism | `brain/mechanisms/report_generation_layer.py` | Wire 40 — runtime monitor for the production act |
| Compression fidelity | `brain/mechanisms/compression_fidelity_layer.py` | Wire 32 — gist extraction with hedging preserved before composition |
| Voice integrity | `brain/mechanisms/voice_integrity_layer.py` | Wire 26 — voice signature preservation across the report body |
| Inference integrity | `brain/mechanisms/inference_integrity_layer.py` | Wire 29 — confidence calibration on factual claims |
| Memory integrity | `brain/mechanisms/memory_integrity_layer.py` | Wire 33 — encodes the published report as an episode |
| Self-analysis | `brain/mechanisms/self_analysis_layer.py` | Wire 36 — receives `kind="report"` reflections |
| Corpus retrieval | `brain/mechanisms/corpus_retrieval_layer.py` | Wire 37 — pulls source material; indexes published reports |
| Outward reach | `brain/mechanisms/outward_reach_layer.py` | Wire 27 — pulls web sources for the draft |
| Safety gate | `skills/safeguard.py` | Allow/block on publish + when ReportGenerationLayer raises a sustained pattern |

When wiring is live:

1. Operator (or self-initiated) brief arrives.
2. Caller gathers sources via `qmd` (corpus), `web-research`, `MemoryIntegrityLayer.retrieve`.
3. Caller invokes `draft(brief, sources, structure_spec, mode)`.
4. Draft runs through `knowledge-summarization` for each source first, preserving hedging.
5. Draft computes fidelity signals — fabrication, citation_drift, structure, voice, hedging.
6. `ReportGenerationLayer.record_op("draft", ...)` records the act with all signals.
7. Operator reviews. If accepted, `publish(report_id)` (gated through `safeguard`).
8. Publication encodes the report through `MemoryIntegrityLayer.record_encode` and indexes through `qmd`.
9. Time passes. Fresh corpus retrievals on adjacent topics may surface conflicts → `stale_publication` flagged.
10. Periodically, `reflect(report_id, fit, ...)` produces the retrospective; routes to `SelfAnalysisLayer.record_analyze(kind="report")`.

## What this skill is *not*

- **Not a journal.** Journal entries are private and autonomous. Reports are for external consumption.
- **Not knowledge summarization.** That's the gist-extraction skill. Reports *use* summarization but go further — they compose multiple summaries into a structured artifact.
- **Not the source of truth.** A published report cites sources; the sources remain authoritative. If sources change, the report is stale, not vice versa.
- **Not silent.** Every op records; without records, the monitor stack stops working.
