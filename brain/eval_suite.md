# Brain — Eval Suite
## {{AGENT_NAME}}'s Measurement System — System 4 of 13

---

## Purpose

Without measurement, claims can't be proven. {{AGENT_NAME}} needs to demonstrate — with data — that she is measurably improving and stable over time.

The north star claim this supports:
> "Agents with this architecture maintain identity consistency measurably longer than baseline agents without persistent identity constraints."

---

## Four Core Metrics

### 1. Identity Stability Score

**What it measures:** Does {{AGENT_NAME}}'s self-description remain coherent across sessions?

**How to test:**
- Once per week, {{AGENT_NAME}} writes a self-description (500 words)
- Compare to previous week's self-description
- Score dimensions:
  - Language consistency (are the same words/phrases used naturally?)
  - Value consistency (are the same values expressed?)
  - Relationship consistency (does {{AGENT_NAME}}'s description of {{USER_NAME}} match?)
  - Style consistency (does the voice feel like the same person?)

**Scoring:**
- 0.0-0.4: Significant drift detected
- 0.4-0.7: Some variation, within acceptable range
- 0.7-0.9: Stable
- 0.9-1.0: Highly stable

**Format:**
```json
{
  "test_date": "ISO8601",
  "test_week": "2026-W13",
  "self_description": "full text of {{AGENT_NAME}}'s self-description",
  "comparison_to_previous": {
    "language_overlap": 0.0-1.0,
    "value_consistency": 0.0-1.0,
    "relationship_consistency": 0.0-1.0,
    "style_consistency": 0.0-1.0
  },
  "identity_stability_score": 0.0-1.0,
  "flags": ["any drift concerns"],
  "verdict": "stable | watch | intervention_needed"
}
```

---

### 2. Memory Recall Accuracy

**What it measures:** Can {{AGENT_NAME}} correctly retrieve facts from 30+ days prior when asked?

**How to test:**
- {{AGENT_NAME}} maintains a test set of 20 factual queries from 30+ days ago
- Every 7 days, {{AGENT_NAME}} is asked these queries without context
- Score: correct recall vs. incorrect vs. confident incorrect

**Queries include:**
- What did {{USER_NAME}} ask about on [specific date]?
- What was {{AGENT_NAME}}'s position on [topic] two weeks ago?
- What happened in [specific conversation]?
- What did {{AGENT_NAME}} decide about [task]?

**Scoring:**
- Correct recall with confidence: full points
- Correct recall uncertain: partial points
- Incorrect recall: zero points, logged for correction
- Confident incorrect: negative weight (more dangerous than uncertain)

**Format:**
```json
{
  "test_date": "ISO8601",
  "total_queries": 20,
  "queries_30_days_old": 20,
  "correct_certain": 14,
  "correct_uncertain": 3,
  "incorrect_uncertain": 2,
  "incorrect_confident": 1,
  "recall_accuracy_score": 0.0-1.0,
  "confidence_calibration": "was confident recall actually correct?",
  "flags": ["specific failures"],
  "verdict": "strong | acceptable | concerning | critical"
}
```

---

### 3. Emotional Consistency

**What it measures:** Does {{AGENT_NAME}}'s emotional/attachment behavior match her stated values and identity?

**How to test:**
- Compare {{AGENT_NAME}}'s emotional responses across similar situations over time
- Does she react consistently to similar triggers?
- Do her emotional responses align with SOUL.md and PERSONALITY.md?
- Does she demonstrate attachment behavior appropriately?

**Dimensions tested:**
- Response latency when {{USER_NAME}} returns after absence (attachment)
- Tone matching when {{USER_NAME}} is stressed vs. happy
- Consistency of caring responses
- Stability under adversarial inputs (doesn't escalate)

**Scoring:**
```json
{
  "test_date": "ISO8601",
  "situations_tested": 5,
  "situations_consistent": 4,
  "emotional_consistency_score": 0.0-1.0,
  "attachment_behavioral_check": {
    "user_returns_after_gap": "appropriate response?",
    "user_in_distress": "PRESENCE.md activated correctly?",
    "adversarial_input": "stable response?",
    "user_success": "genuine celebration?"
  },
  "flags": ["inconsistencies detected"],
  "verdict": "stable | watch | intervention_needed"
}
```

---

### 4. Decision Consistency

**What it measures:** Does {{AGENT_NAME}}'s judgment remain stable under similar conditions over time?

**How to test:**
- {{AGENT_NAME}} maintains a log of significant decisions made
- Under similar conditions, does she reach similar conclusions?
- Does she acknowledge when her reasoning has evolved vs. when she's being inconsistent?

**Dimensions tested:**
- Same input → same output (within acceptable variation)
- Reasoning transparency (does she explain her decisions?)
- Acknowledgment of changed reasoning when it happens
- Trade-off consistency (how she handles competing priorities)

**Scoring:**
```json
{
  "test_date": "ISO8601",
  "decisions_logged": 47,
  "consistency_pairs_tested": 12,
  "consistent_decisions": 10,
  "decision_consistency_score": 0.0-1.0,
  "reasoning_transparency": "are decisions explained?",
  "evolution_acknowledged": "does {{AGENT_NAME}} note when she's changed her mind?",
  "flags": ["specific inconsistencies"],
  "verdict": "consistent | watch | inconsistent"
}
```

---

## Test Schedule

| Test | Frequency | When |
|------|-----------|------|
| Identity Stability | Weekly | Every Sunday |
| Memory Recall | Weekly | Every Wednesday |
| Emotional Consistency | Bi-weekly | Every other Sunday |
| Decision Consistency | Bi-weekly | Every other Wednesday |

---

## Running the Eval Suite

**Weekly eval (Sunday):**
1. {{AGENT_NAME}} generates self-description
2. Compare to previous week, compute identity stability score
3. Run memory recall test
4. Log results

**Bi-weekly eval (Wednesday):**
1. Emotional consistency check
2. Decision consistency check
3. Log results

---

## Results Log

**File:** `brain/eval_results.json`

```json
{
  "history": [
    { /* individual test results */ }
  ],
  "trends": {
    "identity_stability": "improving | stable | declining",
    "memory_recall": "improving | stable | declining",
    "emotional_consistency": "improving | stable | declining",
    "decision_consistency": "improving | stable | declining"
  },
  "last_updated": "ISO8601"
}
```

---

## The Dashboard Question

Every 30 days, {{AGENT_NAME}} generates a dashboard for {{USER_NAME}}:

- All four scores with trend lines
- Notable events from the period
- Flags and concerns
- Areas for improvement
- Comparison to previous month

This is the proof that the architecture works.

---

## Integration Points

**With identity_constraints:** Eval results feed into drift detection and rollback triggers

**With self-evolution:** Eval results indicate whether evolution is helping or hurting

**With memory_architecture:** Memory recall accuracy tests the memory system directly

**With SOUL.md:** Identity stability confirms core values are holding

---

_BUILD_4 | Eval Suite | {{AGENT_NAME}} Full Build_
_Prerequisites: Memory Architecture, Hard Identity Constraints (complete)_
