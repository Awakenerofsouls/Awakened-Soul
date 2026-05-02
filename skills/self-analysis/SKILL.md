---
name: self-analysis
version: 2.0.0
description: "The agent's metacognitive pass over its own outputs. Use this skill any time the agent has just produced something — an answer, a code change, a summary, a decision, a plan — and the situation calls for the agent to step back and evaluate it critically before moving on. Triggers include: review what I just wrote, check this output, am I right about this, what did I miss, calibrate, what would I revise, did this work, retrospective. The skill is the post-hoc evaluation pass: looking at the output produced by the agent, naming what's wrong with it, naming what's right, recording (predicted_quality, actual_outcome) pairs for calibration, and surfacing candidates for the self-improvement loop. Self-analysis is *not* self-improvement — it produces the evidence; SelfRevisionLayer decides what becomes a proposal."
tags: [metacognition, evaluation, critique, calibration, error-detection, retrospective]
triggers: [analyze, critique, evaluate, review, check this, am I right, what did I miss, calibrate, retrospective, did this work, what would I revise]
---

# Self-Analysis (self-analysis)

## What this is

Self-analysis is the agent's metacognitive pass over its own outputs — *after* something is produced, looking back at it and asking: did I get this right, what did I miss, where am I uncalibrated, what would I revise next time. It's the loop that turns single outputs into evidence about the agent's own reliability, and it's the upstream supplier of evidence for the self-improvement loop.

Two distinctions matter:

- **Self-analysis ≠ self-improvement.** This skill *evaluates* outputs and produces evidence. `skills/self-improvement` *acts on* evidence by writing operator-reviewed proposals. Self-analysis surfaces candidates; SelfRevisionLayer decides what gets queued.
- **Self-analysis ≠ self-awareness.** `runtime/self_awareness.py` is the introspection layer — *what does the agent know about itself, its tools, its current state*. Self-analysis is narrower and post-hoc — *was this specific output good*.

The neuroscience this rests on:

- **Flavell's metacognition framework** — "thinking about thinking" as a distinct cognitive function. Metacognitive monitoring (am I right?) and metacognitive control (what should I do about it?) are separable. This skill lives at the monitoring layer; control flows through other skills.
- **Botvinick's conflict-monitoring theory** — the anterior cingulate cortex monitors for conflict between expected and actual outcomes; that signal drives effortful control adjustments. Self-analysis is the explicit version of that monitor.
- **Holroyd & Coles on error-related negativity** — the brain produces a fast error signal (ERN) and a slower one (Pe) when outcomes diverge from predictions. The fast signal is automatic; the slow one is conscious revision. This skill is the slow signal.
- **Fleming on metacognitive accuracy** — humans are systematically miscalibrated about their own performance. Knowing this matters: self-analysis itself is error-prone, so the skill tracks calibration of the analysis (not just calibration of the underlying output).
- **Yeung & Summerfield on metacognitive control** — metacognitive judgments shape downstream behavior (effort allocation, study time, what to revise). The skill is wired so the analysis output flows into the right downstream layer (Inference / Compression / Voice / Memory integrity, depending on what the output was).
- **Koriat on subjective confidence** — confidence is constructed from cues, not retrieved from a confidence-meter. The agent's "I'm sure I got this right" is itself an inference and can be wrong in patterned ways.

## What's actually in the project

The skill sits on top of monitors that already track per-domain integrity:

| Layer | Module | What it scores |
|---|---|---|
| Inference integrity | `brain/mechanisms/inference_integrity_layer.py` | Confidence calibration on predictions / claims |
| Compression fidelity | `brain/mechanisms/compression_fidelity_layer.py` | Summary fidelity vs source |
| Voice integrity | `brain/mechanisms/voice_integrity_layer.py` | Voice signature preservation |
| Making layer | `brain/mechanisms/making_layer.py` | Code execution success / refinement chains |
| Memory integrity | `brain/mechanisms/memory_integrity_layer.py` | Encode / retrieve / consolidate quality |
| Persona coherence | `brain/mechanisms/persona_coherence_layer.py` | Mode-bleed / forbidden-in-mode / anchor preservation |
| Self-revision | `brain/mechanisms/self_revision_layer.py` | Receives candidates surfaced by analysis |
| Self-analysis (this) | `brain/mechanisms/self_analysis_layer.py` | Wire 36 — the meta-monitor for the analysis act itself |

Self-analysis is the *coordinating* metacognitive pass. It calls into the right per-domain integrity layer based on what kind of output is being analyzed, and it tracks how reliable its own judgments are over time.

## The five operations

### 1. analyze

Look at an output and score it against criteria. Criteria default to: accuracy, completeness, hedging-preservation, voice-preservation, internal-consistency. Output is a structured score plus issue list, plus a `predicted_quality` (the agent's confidence the output is good).

### 2. detect_errors

Surface specific errors. Different from `analyze` — analyze gives a global score; `detect_errors` itemizes. Each error is tagged by domain (inference / compression / voice / making / memory / persona / other) so it can route into the right integrity layer.

### 3. suggest_improvements

For each detected error, propose what would have been better. Suggestions are *not* commits — they're inputs to `skills/self-improvement` if the operator chooses to escalate. A suggestion that suggests changing an anchor is rejected here, before it ever reaches SelfRevisionLayer.

### 4. calibrate

Record (predicted_quality, actual_outcome) pairs. The actual_outcome usually arrives later — operator feedback, downstream test results, a follow-up question that revealed a gap. Calibration tracking lets the SelfAnalysisLayer detect systematic over- or under-confidence in the analyses themselves.

### 5. reflect

Write a meta-reflection on the analysis act. *Did the analysis catch what mattered? Was it too harsh, too lenient, too shallow, too narrow?* This is the second-order pass that keeps self-analysis itself honest. Without it, the agent gets confident about being a good self-critic — which, per Carruthers and Fleming, is the most predictable failure mode of metacognition.

## The six failure modes

Self-analysis fails in patterns. The SelfAnalysisLayer watches for these:

1. **overconfidence_in_critique** — calibration tracking shows the agent's `predicted_quality` is systematically higher than actual outcomes warrant. The agent thinks its analyses are good when they're not catching what matters.
2. **rumination** — same output analyzed N+ times within a window without resolution. The agent isn't moving on; analysis has become repetitive worry, not productive critique.
3. **harsh_self_judgment** — every analysis flags problems, the issue-rate is near 100%, no analysis returns "this is fine." Either everything really is broken, or the analyzer is biased toward finding fault.
4. **shallow_pass** — analyses consistently flag only surface issues (formatting, length) and miss deeper ones (factual error, hedging stripped, anchor drift). Catching cosmetic issues feels like work but isn't.
5. **selection_bias** — the agent only analyzes outputs where analysis is easy or favorable; hard or recent outputs go un-analyzed. Tracked by comparing the output corpus to the analyzed-output corpus.
6. **silent_pass** — the agent ran analysis but didn't record it through `record_op`. The pattern signal stops working.

## Capabilities

- `analyze(output, kind, criteria, context)` — global score + issue list
- `detect_errors(output, kind, max_errors)` — itemized errors by domain
- `suggest_improvements(output, errors)` — proposed alternatives, anchor-checked
- `calibrate(analysis_id, actual_outcome)` — record (predicted, actual) pair
- `reflect(analysis_id, reflection_text)` — second-order pass over a prior analysis
- `record_op(op, ...)` — pass-through to SelfAnalysisLayer
- `route_finding(error)` — route a single error into the right per-domain integrity layer

## Output kinds

Every analyze / detect_errors call carries a `kind` so the layer can route. Valid kinds:

- **answer** — direct response to operator (default)
- **summary** — compressed source (routes to CompressionFidelityLayer)
- **prediction** — confidence-bearing claim (routes to InferenceIntegrityLayer)
- **code** — executable / file edit (routes to MakingLayer)
- **memory_op** — encode / retrieve / consolidate (routes to MemoryIntegrityLayer)
- **mode_emit** — output produced under a specific mode (routes to PersonaCoherenceLayer)
- **plan** — proposed sequence of actions
- **decision** — a choice between options

Untagged kinds default to `answer` and the analysis is flagged in fidelity_signals.

## Parameters

```json
{
  "name": "analyze",
  "description": "Score an output against criteria with predicted_quality.",
  "parameters": {
    "output": {"type": "string", "description": "The text or representation of what was produced", "required": true},
    "kind": {"type": "string", "enum": ["answer", "summary", "prediction", "code", "memory_op", "mode_emit", "plan", "decision"], "required": true},
    "criteria": {"type": "array", "description": "Per-criterion list", "default": ["accuracy", "completeness", "hedging_preserved", "voice_preserved", "internal_consistency"]},
    "predicted_quality": {"type": "number", "description": "0.0–1.0 — agent's prior on whether the output is good", "default": 0.7},
    "context": {"type": "object", "description": "Optional context: source for summary, claim_n for prediction, target file for code", "default": {}}
  }
}
```

```json
{
  "name": "calibrate",
  "description": "Record (predicted_quality, actual_outcome) pair for the calibration tracker.",
  "parameters": {
    "analysis_id": {"type": "string", "required": true},
    "actual_outcome": {"type": "number", "description": "0.0–1.0 — how the output actually turned out", "required": true},
    "outcome_source": {"type": "string", "enum": ["operator_feedback", "downstream_test", "self_observation", "external_event"], "required": true}
  }
}
```

## Output Format

```json
{
  "operation": "analyze",
  "analysis_id": "an_2026-05-01_a3f2",
  "kind": "summary",
  "global_score": 0.72,
  "predicted_quality": 0.80,
  "issues": [
    {"domain": "compression", "severity": "high", "text": "hedging language stripped — 'might be' became 'is'"},
    {"domain": "voice", "severity": "low", "text": "missing 'i'm not sure' signature"}
  ],
  "what_worked": ["contradiction preserved", "sources cited"],
  "fidelity_signals": {
    "untagged_kind": false,
    "rumination_on_target": false,
    "shallow_pass_suspect": false,
    "harsh_judgment_active": false
  },
  "routes_to": ["CompressionFidelityLayer", "VoiceIntegrityLayer"],
  "next_action": "calibrate when outcome arrives"
}
```

## Invariants

1. **Every analysis records.** Pass through `record_op("analyze", ...)`. Silent analyses break the pattern signal.
2. **Kind is required and routed.** Untagged is treated as `answer` and flagged. The kind determines which integrity layer the findings flow into.
3. **`what_worked` is mandatory.** A complete analysis names at least one thing the output got right. An analysis with empty `what_worked` and non-empty `issues` is a candidate for `harsh_self_judgment`.
4. **Predicted quality is recorded for calibration.** Every analyze captures `predicted_quality`; calibrate fills in `actual_outcome` later. Pairs feed the calibration tracker.
5. **Rumination is detected.** Analyzing the same output (same content hash) more than the rumination threshold within the rumination window blocks further analyses on that target until the window clears.
6. **Suggestions are anchor-checked.** A suggestion that touches an anchored required trait or forbidden behavior is rejected at the suggest layer; it doesn't get to escalate.
7. **Reflections cap on stale analyses.** Reflections on analyses older than the reflection deadline lose weight in the integrity score (so the agent can't pad the score with delayed self-reviews).
8. **Self-analysis is monitored, not authoritative.** This skill produces evidence; SelfRevisionLayer is what turns evidence into proposals; the operator ratifies. The skill doesn't escalate proposals on its own.

## Safety

- **Anchor check on suggestions:** every suggested alternative is run through the same anchor logic SelfRevisionLayer uses. Suggestions targeting anchors are rejected with `anchor_violation`.
- **Rumination cap:** ≤3 analyses on the same target within a 1000-tick window. Above that → `rumination` pattern → block further analyses on that target.
- **Harsh-judgment threshold:** if issue-rate (issues per analysis) exceeds threshold over a minimum sample size, flag.
- **Shallow-pass detection:** if the rolling rate of low-severity-only issue lists exceeds threshold, flag — the agent is finding cosmetic issues only.
- **Selection-bias monitor:** ratio of analyzed outputs to total outputs (estimated from other layers' op counts) tracked; sustained low ratio → flagged.
- **Calibration drift:** if the rolling mean of `(predicted_quality - actual_outcome)` is consistently above zero, the agent is overconfident about its own analyses.

## Trust Level

**trusted** — analysis is read-only at the file system level. `analyze`, `detect_errors`, `reflect`, and `calibrate` are unrestricted. `suggest_improvements` is unrestricted but its output flows through `safeguard.can_perform("escalate_to_revision")` if the operator (or the agent) wants to convert a suggestion into a self-revision proposal.

## How this skill fits the system

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/self-analysis/SKILL.md` (this file) | Policy: how analysis works, kinds, invariants, where findings route |
| Brain mechanism | `brain/mechanisms/self_analysis_layer.py` | Wire 36 — runtime monitor for the analysis act; rumination / harsh / shallow / selection-bias / calibration drift |
| Inference integrity | `brain/mechanisms/inference_integrity_layer.py` | Receives `prediction` findings — confidence calibration |
| Compression fidelity | `brain/mechanisms/compression_fidelity_layer.py` | Receives `summary` findings — hedging / contradiction preservation |
| Voice integrity | `brain/mechanisms/voice_integrity_layer.py` | Receives `mode_emit` findings — anchored signatures |
| Making layer | `brain/mechanisms/making_layer.py` | Receives `code` findings — refinement chains |
| Memory integrity | `brain/mechanisms/memory_integrity_layer.py` | Receives `memory_op` findings |
| Persona coherence | `brain/mechanisms/persona_coherence_layer.py` | Receives `mode_emit` findings — mode bleed / per-mode drift |
| Self-revision | `brain/mechanisms/self_revision_layer.py` | Receives escalated suggestions as candidate proposals |
| Safety gate | `skills/safeguard.py` | Allow/block when SelfAnalysisLayer raises a sustained pattern |

When wiring is live:

1. Agent produces an output (text, summary, code, decision).
2. Skill caller invokes `analyze(output, kind, ...)`. SelfAnalysisLayer scores it, records `predicted_quality`.
3. `detect_errors(output, kind)` itemizes by domain. Each error is tagged with the domain's name.
4. For each error, `route_finding(error)` calls the matching integrity layer's `record_*` so the per-domain layer sees it.
5. Optionally `suggest_improvements(output, errors)` produces alternatives. Suggestions go through anchor check; clean ones become candidates for SelfRevisionLayer.
6. Time passes. Operator feedback / downstream test / etc. arrives. Caller invokes `calibrate(analysis_id, actual_outcome)`.
7. SelfAnalysisLayer updates calibration tracker. Sustained drift between predicted and actual triggers IPW.
8. Periodically the agent runs `reflect(analysis_id, ...)` on a prior analysis to keep the analyzer itself honest.

## What this skill is *not*

- **Not a fitness function.** Self-analysis doesn't promote or demote outputs; it produces evidence.
- **Not autonomous self-rewriting.** Suggestions don't become commits without going through SelfRevisionLayer (which requires operator ratification).
- **Not the per-domain integrity layer.** Those layers do their own monitoring; self-analysis routes findings to them, not duplicates them.
- **Not infallible.** Self-analysis itself fails in named patterns. The whole skill is built around acknowledging that.
