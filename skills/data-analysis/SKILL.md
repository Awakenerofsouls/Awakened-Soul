---
name: data-analysis
version: 2.0.0
description: "Inference with epistemic honesty. Use this skill whenever the agent needs to extract meaning from structured data — describe a distribution, compare groups, predict an outcome, explain a pattern, look for trends, summarize a dataset, or test a hypothesis against evidence. Each inference is intent-tagged, sample-size-aware, confidence-claimed, and calibration-tracked. The work is the same either way: see what the data actually says, claim only what the evidence supports."
tags: [data, statistics, analysis, patterns, inference, epistemic]
triggers: [analyze data, statistics, patterns, trends, summarize this, what does the data show, test a hypothesis, predict, compare, explain why]
---

# Inference with Epistemic Honesty (data-analysis)

## What this is

This isn't a generic statistics helper. It's the agent's **act of inference** — looking at structured data and extracting meaning while staying calibrated.

Every analysis is four things at once:

- **A claim** — the agent is asserting something about the world based on the data
- **A confidence** — the agent is reporting how much weight to put on the claim
- **A scope** — the analysis is bounded by the sample, the dimensions, and the assumptions
- **A future calibration check** — when reality disagrees with a claim later, that's data about whether the agent's confidence was honest

The failure modes here aren't voice drift or flailing or panic loops. They're more subtle:

- **Overconfidence** — the agent reporting 90% certainty when the sample only supports 60%
- **Confirmation bias** — every analysis lined up to support one prior, never testing alternatives
- **Cherry-picking** — sample size shrinking when results stop supporting a thesis
- **Spurious certainty** — high confidence on small or noisy samples
- **Map collapse** — treating analysis output as ground truth in subsequent reasoning

So this skill is paired tightly with three other parts of the system:

- `skills/safeguard.py` — gates whether an analysis can be published; sustained overconfidence trips approval-required
- `brain/mechanisms/inference_integrity_layer.py` — the brain-side mechanism that tracks confidence vs sample size, monitors calibration when outcomes arrive, detects single-hypothesis streaks, and publishes the inference signal to the TSB
- Episodic memory (`brain/three_tier_memory.py`) — every analysis lands here with intent, claim, confidence, sample size, and (eventually) outcome. The agent learns its own calibration over time.

## Capabilities

- `analyze_dataset(data, intent, hypothesis)` — analyze data with explicit intent and hypothesis tagging
- `compute_statistics(data)` — descriptive statistics with sample size always reported
- `detect_patterns(data)` — find structure in the data, with explicit confidence proportional to sample
- `record_analysis(intent, hypothesis, claim, confidence, sample_size, dimensions, conclusion)` — persist to ABM + InferenceIntegrityLayer
- `record_outcome(analysis_id, outcome)` — when reality later confirms or contradicts an analysis, calibrate

## Intent categories

Every inference must be tagged with one of these. The InferenceIntegrityLayer reads patterns over time:

- **describe** — what's in the data (distributions, ranges, basic structure). Lowest epistemic risk.
- **compare** — does X differ from Y? Requires honest sample sizes and effect-size reporting.
- **predict** — extrapolate or forecast. Highest epistemic risk; confidence should rarely exceed 0.7 without strong evidence.
- **explain** — find causal/structural reasons for observed patterns. Requires considering alternative explanations explicitly.

If an inference doesn't fit one of these, that's information — usually means the claim isn't well-formed yet.

## Parameters

```json
{
  "name": "analyze_dataset",
  "description": "Run an analysis with explicit epistemic accounting.",
  "parameters": {
    "data": {"type": "array", "description": "Data to analyze", "required": true},
    "intent": {"type": "string", "enum": ["describe", "compare", "predict", "explain"], "required": true},
    "hypothesis": {"type": "string", "description": "What the agent is testing — required so the analysis can be calibrated against alternatives later"},
    "alternatives": {"type": "array", "description": "Other hypotheses the agent considered", "items": {"type": "string"}}
  }
}
```

## Output Format

```json
{
  "intent": "compare",
  "hypothesis": "group A and group B differ in X",
  "claim": "group A's mean X is higher than group B's by Y",
  "confidence": 0.72,
  "sample_size": 48,
  "dimensions_used": 3,
  "alternatives_considered": [
    "the difference is noise (within natural variation)",
    "a third variable is causing both"
  ],
  "caveats": ["sample is non-random", "ten outliers excluded"],
  "analysis_id": "..."
}
```

## Invariants

1. **Always report sample size.** A claim without a sample size is not an analysis — it's an opinion.
2. **Confidence must be proportional to sample.** The InferenceIntegrityLayer flags `claim_size_mismatch` when claimed confidence exceeds what the sample can support (heuristic: confidence ≤ 0.5 + min(0.4, n/100) for predictions, more lenient for descriptions).
3. **State the hypothesis explicitly.** "I'm testing whether X" is required. Untagged inference fails closed.
4. **Consider at least one alternative for `compare`/`predict`/`explain`.** A claim with no alternative considered is a confirmation-bias trap.
5. **Caveats are not optional.** If the sample is non-random, if outliers were dropped, if a transformation was applied — those are part of the claim, not footnotes.
6. **Map ≠ territory.** Analysis output is a model of the data, not the data. Subsequent reasoning that treats analysis as ground truth gets flagged.
7. **Bounded code-storage in memory.** Truncate analysis input/output to 4KB before persisting.

## Safety

- **Sample-size floor**: predictions on n<10 require explicit operator approval
- **Confidence ceiling for small n**: claims of confidence ≥ 0.8 require sample_size ≥ 30 OR explicit "probabilistic-prior" tag
- **Hypothesis distribution check**: if the last 10 analyses all tested the same hypothesis, the InferenceIntegrityLayer flags `single_hypothesis_streak` and the next inference requires considering at least one alternative
- **Calibration tracking**: when outcomes are later recorded via `record_outcome()`, the layer maintains a rolling calibration score (claimed confidence vs hit rate). Sustained miscalibration routes to IPW.

## Trust Level

**restricted** — analysis isn't action in the world the way reach or making is, but a confidently-stated claim that turns out to be wrong becomes downstream input to reasoning. Per `skills/dispatcher.py`, this skill goes through `dispatch(skill, operation="execute")` and is gated by trust level. Read-only metadata access (`operation="describe"` / `"list"`) is unrestricted.

## How this skill fits the system

The work is split across three layers:

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/data-analysis/SKILL.md` (this file) | Contract: what inference means, what intents exist, what the agent promises about confidence |
| Brain mechanism | `brain/mechanisms/inference_integrity_layer.py` | Runtime monitor: per-intent counts, claim-vs-sample mismatch detection, calibration tracking, single-hypothesis streak detection, IPW handshake |
| Safety gate | `skills/safeguard.py` | Allow/block decision per-analysis when overconfidence is sustained |

When wiring time arrives, the integration looks like this:

1. Agent decides to infer (e.g. compare two groups).
2. Caller asks `InferenceIntegrityLayer.should_block(intent, sample_size, claimed_confidence)`. If True (sample too small for confidence claimed, or single-hypothesis streak detected) → halt or require explicit operator approval.
3. Analysis runs.
4. Caller invokes `InferenceIntegrityLayer.record_analysis(intent, hypothesis, claim, confidence, sample_size, dimensions, conclusion)`.
5. Mechanism updates per-intent counts, hypothesis distribution, and the rolling calibration window. State publishes to the TSB so AttentionModifier can bias toward "consider alternatives" if a single-hypothesis streak is forming.
6. When reality later confirms or contradicts the claim, caller invokes `record_outcome(analysis_id, was_right)`. Calibration score updates.
7. Sustained miscalibration (claimed-confidence consistently higher than hit rate) routes through `IdentityProposalWriter` — the agent claiming more certainty than it has is identity-relevant data, not just one bad analysis.
