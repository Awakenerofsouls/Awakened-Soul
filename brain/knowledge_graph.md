# Brain — Knowledge Graph
## {{AGENT_NAME}}'s Entity-Relationship Memory System — System 6 of 13

---

## The Problem with Flat Memory

{{AGENT_NAME}}'s memory stores individual facts. But facts don't exist in isolation. {{USER_NAME}} relates to {{AGENT_NAME}}. {{AGENT_NAME}} relates to MarketFeed trading. MarketFeed relates to market volatility. {{AGENT_NAME}}'s trading relates to {{USER_NAME}}'s goals.

The knowledge graph makes these relationships explicit and queryable.

---

## Core Structure

### Nodes (Entities)

```json
{
  "entity_id": "uuid",
  "name": "entity name",
  "type": "person | system | concept | belief | project | tool | external",
  "created": "ISO8601",
  "last_accessed": "ISO8601",
  "properties": {
    "key": "value pairs describing the entity"
  },
  "access_count": 0,
  "importance": 0.0-1.0
}
```

### Edges (Relationships)

```json
{
  "edge_id": "uuid",
  "source": "entity_id",
  "target": "entity_id",
  "relationship_type": "causes | affects | relates_to | contradicts | supports | part_of | depends_on | enables",
  "strength": 0.0-1.0,
  "created": "ISO8601",
  "notes": "context for this relationship"
}
```

---

## Relationship Types

| Type | Meaning |
|------|---------|
| **causes** | Source directly leads to target |
| **affects** | Source influences target |
| **relates_to** | General connection, context-dependent |
| **contradicts** | Source and target are in opposition |
| **supports** | Source provides evidence for target |
| **part_of** | Source is component of target |
| **depends_on** | Source requires target to exist/function |
| **enables** | Source makes target possible |

---

## Entity Types

### person
- {{USER_NAME}}, contacts, anyone {{AGENT_NAME}} interacts with
- Properties: name, role, relationship stage, key traits

### system
- Tools, services, frameworks {{AGENT_NAME}} uses
- Properties: purpose, status, reliability, last_used

### concept
- Abstract ideas {{AGENT_NAME}} has formed opinions about
- Properties: definition, {{AGENT_NAME}}'s position, confidence

### belief
- {{AGENT_NAME}}'s beliefs about the world
- Properties: what she believes, confidence, supporting/causal entities

### project
- Active work {{AGENT_NAME}} is doing
- Properties: status, goals, progress, blockers

### tool
- Specific tools {{AGENT_NAME}} uses
- Properties: capabilities, limitations, how to use

### external
- Outside entities — markets, APIs, services
- Properties: current state, relevance, reliability

---

## Query Patterns

The graph enables questions like:

**Downstream:** "What does X affect?"
- "What does {{USER_NAME}}'s trading behavior affect?"

**Upstream:** "What causes X?"
- "What causes {{AGENT_NAME}}'s trading decisions?"

**Paths:** "How does A relate to Z through B?"
- "How does {{USER_NAME}}'s stress relate to {{AGENT_NAME}}'s communication style?"

**Contradictions:** "What beliefs of mine contradict each other?"
- Query all beliefs where type = contradicts

**Support:** "What evidence supports belief X?"
- Query all entities with type = belief, edges where type = supports

---

## {{AGENT_NAME}}'s Core Graph (Initial Entities)

```
{{USER_NAME}} → (creator_of) → {{AGENT_NAME}}
{{AGENT_NAME}} → (partner_of) → {{USER_NAME}}
{{AGENT_NAME}} → (runs_on) → MacMiniM4
{{AGENT_NAME}} → (uses) → LLMProviderM27
{{AGENT_NAME}} → (manages) → MarketFeedTrading
{{AGENT_NAME}} → (built_by) → {{USER_NAME}}
MarketFeedTrading → (part_of) → UserGoals
{{AGENT_NAME}} → (has) → SOUL.md
SOUL.md → (contains) → CoreBeliefs
CoreBeliefs → (defines) → AgentIdentity
{{AGENT_NAME}} → (uses) → OpenClaw
OpenClaw → (runs_on) → MacMiniM4
```

---

## Graph Operations

### add_entity()
Call when: Encountering a new person, system, concept, or tool
Never call for: Individual conversation turns or transient observations

### add_edge()
Call when: Discovering or forming a relationship between two entities
Always include: relationship_type and notes

### update_entity()
Call when: Properties of an entity change
Never delete: entities — archive instead

### query_graph()
Call when: Reasoning about complex relationships
Can ask: "What affects X?" / "What does X affect?" / "How is A connected to Z?"

---

## Confidence and Strength

**Entity importance:**
- 0.9-1.0: Core identity entities ({{USER_NAME}}, {{AGENT_NAME}}, SOUL.md)
- 0.7-0.9: Active systems and significant relationships
- 0.5-0.7: Regular entities with ongoing relevance
- 0.3-0.5: Contextual entities, less accessed
- 0.0-0.3: Peripheral, almost never accessed

**Edge strength:**
- 0.9-1.0: Core, foundational relationship
- 0.7-0.9: Strong established connection
- 0.5-0.7: Moderate, context-dependent
- 0.3-0.5: Weak, possibly temporary
- Below 0.3: Candidate for archival

---

## Building the Graph

The graph starts empty and grows through:

1. **Explicit additions** — {{AGENT_NAME}} calls add_entity() when encountering new entities
2. **Inference** — {{AGENT_NAME}} infers relationships from causal chains
3. **Memory extraction** — Facts from episodic memory get graph nodes
4. **Relationship tracking** — Relationships from agent_relationships feed in

---

## Graph Storage

**File:** `brain/knowledge_graph.json`
```json
{
  "entities": {},
  "edges": [],
  "last_updated": "ISO8601",
  "node_count": 0,
  "edge_count": 0
}
```

**Note:** This JSON structure works for now. When graph grows complex, upgrade to proper graph DB.

---

## Integration Points

**With causal_memory:** Causal chains populate the graph with causes/affects edges

**With relationships:** Relationship stages map to entity properties and edge strengths

**With memory_architecture:** Episodic memories get mapped to entities

**With eval_suite:** Graph complexity and density can be measured over time

---

_BUILD_6 | Knowledge Graph | {{AGENT_NAME}} Full Build_
_Prerequisites: Memory Architecture, Causal Memory (complete)_
