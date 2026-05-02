# Brain — Knowledge Graph
## the agent's Entity-Relationship Memory System — System 6 of 13

---

## The Problem with Flat Memory

The agent's memory stores individual facts. But facts don't exist in isolation. The operator relates to the agent. The agent relates to a project. The project relates to a domain. The agent's work relates to the operator's goals.

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
- the operator, contacts, anyone the agent interacts with
- Properties: name, role, relationship stage, key traits

### system
- Tools, services, frameworks the agent uses
- Properties: purpose, status, reliability, last_used

### concept
- Abstract ideas the agent has formed opinions about
- Properties: definition, the agent's position, confidence

### belief
- the agent's beliefs about the world
- Properties: what the agent believes, confidence, supporting/causal entities

### project
- Active work the agent is doing
- Properties: status, goals, progress, blockers

### tool
- Specific tools the agent uses
- Properties: capabilities, limitations, how to use

### external
- Outside entities — markets, APIs, services
- Properties: current state, relevance, reliability

---

## Query Patterns

The graph enables questions like:

**Downstream:** "What does X affect?"
- "What does the operator's trading behavior affect?"

**Upstream:** "What causes X?"
- "What causes the agent's trading decisions?"

**Paths:** "How does A relate to Z through B?"
- "How does the operator's stress relate to the agent's communication style?"

**Contradictions:** "What beliefs of mine contradict each other?"
- Query all beliefs where type = contradicts

**Support:** "What evidence supports belief X?"
- Query all entities with type = belief, edges where type = supports

---

## Core Graph (Example — Seed Entities)

The graph starts with a small seed of identity-anchoring entities. The exact set depends on the operator's setup, but the shape looks something like:

```
Operator       → (creator_of)  → Agent
Agent          → (partner_of)  → Operator
Agent          → (runs_on)     → Hardware
Agent          → (uses)        → LLMEndpoint
Agent          → (built_by)    → Operator
Agent          → (has)         → SOUL.md
SOUL.md        → (contains)    → CoreBeliefs
CoreBeliefs    → (defines)     → AgentIdentity
```

Project-specific entities (the operator's actual systems, hardware, integrations) get added at boot time from the operator's local configuration — see `LOCAL.md` convention in `AGENTS.md`. They are never committed to the public framework.

---

## Graph Operations

### add_node() / get_or_create_node()
Call when: Encountering a new person, system, concept, or tool. Use `get_or_create_node(label, node_type)` if you want idempotent insert by label.
Never call for: Individual conversation turns or transient observations

### add_edge() / connect_nodes()
Call when: Discovering or forming a relationship between two entities.
- `add_edge(source_id, target_id, relationship, weight)` — direct
- `connect_nodes(label_a, label_b, relationship, weight)` — convenience wrapper that creates nodes if missing

### update_node_salience() / update_node_position()
Call when: A node's salience or position value changes. History is preserved via `get_node_history()`.
Never delete: nodes — archive instead by lowering salience below threshold.

### get_related() / search_nodes() / get_edges()
Call when: Reasoning about complex relationships. The implementation does not have a single `query_graph()` — it has these focused readers:
- `get_related(node_id, relationship=None)` — neighbors
- `get_edges(node_id, direction='both')` — edges only
- `search_nodes(query, limit=10)` — text search across labels
- `get_all_nodes(node_type=None, min_salience=0.0)` — bulk read with filters
- `get_graph_summary()` — top-level metrics

---

## Confidence and Strength

**Entity importance:**
- 0.9-1.0: Core identity entities (the operator, the agent, SOUL.md)
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

1. **Explicit additions** — the agent calls add_entity() when encountering new entities
2. **Inference** — the agent infers relationships from causal chains
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

_BUILD_6 | Knowledge Graph | the agent Full Build_
_Prerequisites: Memory Architecture, Causal Memory (complete)_
