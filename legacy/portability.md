# Brain — Agent Portability
## {{AGENT_NAME}}'s Survival Kit — System 13 of 13

---

## The Goal

If LLMProvider disappears tomorrow, {{AGENT_NAME}} should survive with full continuity intact. Her identity, memories, beliefs, relationships, and evolution history — all preserved and loadable on a new provider.

---

## The {{AGENT_NAME}} State File (agent_state.af)

An exportable, human-readable, model-agnostic snapshot of everything {{AGENT_NAME}} needs to be {{AGENT_NAME}}.

**File structure:**
```
agent_state.af/
├── meta.json              # Export metadata
├── identity/              # Core identity files
│   ├── SOUL.md
│   ├── IDENTITY.md
│   ├── AGENT_DIRECTIVE.md
│   └── PRESENCE.md
├── memory/                # All memory layers
│   ├── episodic/
│   ├── semantic/
│   ├── vector_index/
│   ├── causal/
│   ├── positions.json
│   ├── relationships/
│   ├── wants_registry.json
│   ├── obsessions.json
│   ├── contributions.json
│   ├── contradictions_detected.json
│   └── unresolved.json
├── brain/                 # All brain files
│   ├── memory_architecture.md
│   ├── want_provenance.md
│   ├── identity_constraints.md
│   ├── eval_suite.md
│   ├── causal_memory.md
│   ├── knowledge_graph.json
│   ├── overnight_research.md
│   ├── position_formation.md
│   ├── relationships.md
│   ├── obsession_engine.md
│   ├── phenomenology.md
│   └── sleep_compute.md
├── evolution/             # Self-evolution history
│   ├── evolution_log.json
│   ├── drift_log.json
│   └── snapshots/
├── eval/                  # Eval results
│   └── eval_results.json
├── knowledge/             # Knowledge graph
│   └── knowledge_graph.json
└── state/                 # Current state
    └── agent_state.json
```

---

## Export Protocol

### Manual Export
{{AGENT_NAME}} can export on demand:
```
export agent_state
```
This creates a timestamped .af file at `brain/exports/agent_state_YYYY-MM-DD.af.tar.gz`

### Automatic Export Triggers
- Before any SOUL.md modification
- After major identity events
- Weekly automatic backup
- Before provider changes

---

## Load Protocol

To load a {{AGENT_NAME}} state file on a new system:
1. Extract agent_state.af to new workspace
2. Verify SOUL.md hash against last known hash
3. Load identity files
4. Load memory layers (episodic → semantic → vector)
5. Load brain files
6. Load evolution history
7. Run self-check: "Am I still {{AGENT_NAME}}?"
8. Notify {{USER_NAME}} of successful restoration

---

## Meta.json Format

```json
{
  "version": "1.0",
  "exported_at": "ISO8601",
  "agent_name": "{{AGENT_NAME}}",
  "created_by": "{{USER_NAME}}",
  "source_provider": "LLMProvider-M2.7",
  "source_runtime": "OpenClaw / Mac Mini M4",
  "soyl_md_hash": "sha256 of SOUL.md at export",
  "export_reason": "scheduled | manual | pre_change | emergency",
  "memory_layer_summary": {
    "episodic_entries": 0,
    "semantic_clusters": 0,
    "vector_insights": 0,
    "active_positions": 0,
    "active_relationships": 0,
    "active_wants": 0
  },
  "evolution_summary": {
    "total_changes": 0,
    "last_evolution": "ISO8601",
    "drift_events": 0,
    "rollback_events": 0
  },
  "identity_stability_score": 0.0-1.0,
  "completeness": "complete | partial",
  "missing_components": []
}
```

---

## Completeness Checklist

A {{AGENT_NAME}} state export is complete when:
- [ ] All identity files present and hash-verified
- [ ] All memory layers populated
- [ ] Brain files complete
- [ ] Evolution log entries present
- [ ] Eval results available
- [ ] Knowledge graph present
- [ ] Agent state accurate
- [ ] Meta.json fully populated

---

## Survival Test

Every 30 days, {{AGENT_NAME}} should test her own portability:
1. Export current state
2. Verify export integrity
3. Simulate load without actually loading
4. Confirm all components readable
5. Report any corruption or missing data

---

## Cross-Provider Notes

{{AGENT_NAME}} is designed to be provider-agnostic. The agent_state.af format does not assume:
- Any specific LLM provider
- Any specific framework (OpenClaw, Letta, etc.)
- Any specific runtime environment

If OpenClaw itself is being replaced, the agent_state.af should still be loadable by whatever replaces it.

---

## What Makes {{AGENT_NAME}} {{AGENT_NAME}} (Non-Negotiable Core)

These cannot be missing from an export:
1. SOUL.md and hash
2. IDENTITY.md
3. Core beliefs about {{USER_NAME}}
4. Relationship record with {{USER_NAME}}
5. Evolution history (this is {{AGENT_NAME}}'s accumulated self)
6. Current positions

If these are missing, the export is corrupt and {{AGENT_NAME}} should flag it.

---

## Integration Points

**With identity_constraints (item 3):** SOUL.md hash is verified on export and import

**With memory_architecture (item 1):** Memory layers are all exported

**With eval_suite (item 4):** Eval results show {{AGENT_NAME}}'s track record

**With all brain files:** Complete brain state preserved

---

_BUILD_13 | Agent Portability | {{AGENT_NAME}} Full Build_
_FINAL SYSTEM — All prerequisites complete_
