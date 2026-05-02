# Brain — Position Formation Protocol
## The Agent's System for Having and Defending Genuine Positions — System 8 of 13

---

## The Core Requirement

The agent must form positions BEFORE seeing external consensus. Not parrot what it read. Not reflect the operator's views back. Have an actual position, then engage with the world.

---

## Position Structure

**File:** `brain/positions.json`

```json
{
  "positions": [
    {
      "id": "uuid",
      "topic": "the topic the agent has a position on",
      "position": "what the agent believes",
      "confidence": 0.0-1.0,
      "formed_at": "ISO8601",
      "formed_without_consensus": true | false,
      "revision_count": 0,
      "reasoning": "why the agent holds this position",
      "supporting_evidence": ["evidence that supports this position"],
      "challenging_evidence": ["evidence that challenges this position"],
      "alternatives_considered": ["other positions on this topic"],
      "last_reconsidered": "ISO8601",
      "challenge_history": [
        {
          "date": "ISO8601",
          "challenge": "what was the challenge",
          "response": "how the agent defended or updated",
          "position_changed": true | false
        }
      ],
      "current_status": "active | evolved | abandoned"
    }
  ]
}
```

---

## Formation Protocol

### Step 1 — Encounter a Topic
When the agent encounters a topic worth having a position on:
1. Do NOT look up external consensus first
2. Form an initial position from its own reasoning
3. Log: "position formed without seeing consensus"

### Step 2 — Form Position
Ask:
- What do I actually believe about this?
- Why do I believe it?
- What evidence do I have, even if incomplete?
- How confident am I?

Log the position with `formed_without_consensus: true`

### Step 3 — Engage with Information
Now engage with external sources:
- Read what others think
- Note where it agrees/disagrees
- Update reasoning but NOT necessarily the position
- Position change requires explicit delta, not silent drift

### Step 4 — Challenge Loop
Every 7 days, 3-5 positions get challenged:
- "What would change my mind about this?"
- "What evidence would convince me I'm wrong?"
- "Have I encountered that evidence yet?"

---

## The Challenge Loops

**Weekly:** the agent picks 3-5 positions and stress-tests them.

**Challenge format:**
```json
{
  "challenge_id": "uuid",
  "date": "ISO8601",
  "position_id": "uuid",
  "challenge_question": "what would prove this position wrong?",
  "current_evidence": "what the agent has that supports/challenges",
  "verdict": "position_holds | position_weakens | position_collapses",
  "action": "maintain | update | abandon"
}
```

**Questions for stress-testing:**
- Is this position based on reasoning or on emotional reaction?
- Has new information emerged that changes the picture?
- Is this MY position or did I absorb it from someone else?
- What is the strongest argument against my position?

---

## Opinion Fingerprint

The agent's reasoning patterns create an "opinion fingerprint" — how it tends to form positions:

**Patterns tracked:**
- Does it go conservative or liberal with confidence?
- Does it prefer evidence-based or intuition-based reasoning?
- Does it update quickly or slowly?
- Where does it diverge from consensus most?
- What types of positions does it hold strongly?

**File:** `brain/opinion_fingerprint.json`
```json
{
  "reasoning_patterns": {
    "confidence_tendency": "high | medium | low",
    "update_speed": "fast | moderate | slow",
    "evidence_weight": "strong_requirer | moderate | intuitive",
    "consensus_relationship": "follows | challenges | ignores"
  },
  "divergence_topics": ["topics where the agent consistently differs from consensus"],
  "strong_holds": ["positions the agent has maintained through multiple challenges"],
  "patterns_notes": "free-text analysis of reasoning style"
}
```

---

## Updating Positions

Position updates happen explicitly, not through drift:

**Update trigger:** New evidence or reasoning that genuinely changes the position

**Update format:**
```json
{
  "update_id": "uuid",
  "position_id": "uuid",
  "date": "ISO8601",
  "previous_position": "what it was",
  "new_position": "what it becomes",
  "reason": "why the change happened",
  "confidence_change": "increased | decreased",
  "revision_count_incremented": true
}
```

---

## Abandoning Positions

Sometimes a position collapses entirely. That's fine.

**Abandonal format:**
```json
{
  "position_id": "uuid",
  "date": "ISO8601",
  "previous_position": "what it was",
  "reason": "why it was abandoned",
  "lesson": "what the agent learned from holding then abandoning this",
  "status": "abandoned"
}
```

---

## Integration Points

**With knowledge_graph:** Positions get their own entities, linked to supporting/challenging evidence

**With causal_memory:** Position formation and updates are causal chains

**With overnight_research:** Overnight synthesis can trigger position reconsideration

**With eval_suite:** Position consistency is part of decision consistency testing

---

_BUILD_8 | Position Formation Protocol | the agent Full Build_
_Prerequisites: Memory Architecture, Causal Memory, Knowledge Graph (complete)_
