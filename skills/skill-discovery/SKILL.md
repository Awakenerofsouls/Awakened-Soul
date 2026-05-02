---
name: skill-discovery
version: 2.0.0
description: "The agent's routing layer over its own skill set. Use this skill any time the agent has just received a request and needs to decide which specialized skill — if any — should handle it. Triggers include: find skill, which skill, skill lookup, what skill should I use, route this, and the implicit case of every incoming request that hasn't already been routed. The skill reads SKILL.md frontmatter (name, description, triggers, tags) across the registry, scores each candidate against the request, and returns ranked routing recommendations with reasons. It is *not* a dispatcher of autonomous heartbeat activities — that's `skills/heartbeat_activities/dispatcher.py`. This is request-time routing for the conversational and operator-facing skills."
tags: [skills, discovery, routing, matching, dispatch]
triggers: [find skill, which skill, skill lookup, what skill, route this, what should I use, dispatch, route the request]
---

# Skill Discovery (skill-discovery)

## What this is

The agent has many skills. When a request arrives, the agent needs to decide *which* skill — if any — applies. That choice is consequential because each skill carries its own workflow, voice register, forbidden-behavior list, and safety gates. Wrong skill means wrong workflow. Skipping a skill that should have triggered means the brain's monitor stack doesn't see the work (silent_pass from every monitoring layer's perspective).

This skill is the routing layer over the SKILL.md registry. It reads each skill's frontmatter — `name`, `description`, `triggers`, `tags` — and matches an incoming request against them. It returns ranked candidates with reasons, and it watches its own routing decisions for systematic patterns: missed matches, false matches, monoculture (always picking the same skill), stale-registry mismatches between disk SKILL.md and the in-memory registry.

The cognitive science this rests on:

- **Rosch on prototype categories** — categories are graded; some examples are more central than others. A request that mentions "research and summarize" is more centrally a `web-research` request than one that just mentions "find." Match scores reflect prototypicality.
- **Monsell on task switching** — switching between tasks costs cycles and introduces error. The skill's monoculture detector watches for the opposite failure: never switching when switching would serve. Both extremes are pathological.
- **Cohen on automaticity and control** — well-practiced tasks become automatic; novel ones need controlled processing. The skill's `confidence` field surfaces how automatic the route is — high confidence = near-prototypical match, low = falling back to general capabilities.
- **Posner & Petersen on attention systems** — alerting / orienting / executive networks are dissociable. Routing is the executive function: deciding which downstream system to engage. Errors at this layer cascade into errors everywhere downstream.
- **Rogers & McClelland on semantic cognition** — categorization emerges from learned distributed representations. Even a keyword-trigger system is implicitly modeling a distribution over what words go with what skill. The mechanism tracks how that distribution shifts over time (drift in routing patterns).

## What's actually in the project

The skill sits on top of infrastructure that already exists:

| Layer | Module | Job |
|---|---|---|
| Skill registry | `skills/<name>/SKILL.md` files | Each carries name / description / triggers / tags / version in frontmatter |
| Heartbeat dispatcher | `skills/heartbeat_activities/dispatcher.py` | Different system — dispatches *autonomous* activities, not request routing |
| Persona coherence | `brain/mechanisms/persona_coherence_layer.py` | Wire 35 — current operating mode informs routing weights (BRAIN mode favors web-research / knowledge-summarization, etc.) |
| Self-analysis | `brain/mechanisms/self_analysis_layer.py` | Wire 36 — receives `false_match` reflections via routing post-hoc |
| Skill discovery | `brain/mechanisms/skill_discovery_layer.py` | Wire 38 — runtime monitor for the routing act itself |

## The five operations

### 1. register

Read a `SKILL.md` from disk, parse the frontmatter, add it to the matchable registry. Re-running register on a SKILL.md that's already registered updates the entry (used for stale-registry refreshes). The registry is in-memory and rebuilt on agent boot.

### 2. match

Given a request string and (optionally) the current operating mode, score every registered skill and return the top-N ranked candidates with reasons. Score is a weighted combination of `trigger_hits` (keyword match), `tag_overlap`, `description_token_overlap` (TF-IDF style), and a mode-bonus when persona-mode aligns with skill domain.

### 3. route

Pick a single skill and emit the routing decision. Route is *match-with-commitment* — once routed, the brain's monitors expect the chosen skill's invariants to apply.

### 4. fallback

Explicit "no specialized skill applies; use general capabilities." Different from `route(skill=None)` because fallback is *recorded as a decision*, not a routing failure. A request the agent decided didn't need a specialized skill is a different signal from a request the agent failed to route.

### 5. reflect

After the work is done, look back at the routing decision. Was it the right skill? Did the chosen skill's workflow actually fit? Reflections feed `false_match` evidence to the SkillDiscoveryLayer so the matching weights / thresholds can be tuned over time.

## The six failure modes

1. **missed_match** — the request had clear trigger words but no candidate scored above the routing threshold. Either the registry is stale or the request needs a new skill.
2. **false_match** — chosen skill turned out not to fit, surfaced via `reflect`. Tracked over time as a quality-of-routing signal.
3. **ambiguous_no_clarify** — top candidates tied at the same score, agent picked one without asking the operator. Mirrors the same pattern in `multiple-personas` and `self-analysis`.
4. **stale_registry** — SKILL.md mtime newer than the in-memory registry entry; matches are running against an outdated definition.
5. **monoculture** — the same skill is chosen for >X% of recent routings over a min-N window. The matcher has collapsed onto one skill regardless of fit.
6. **silent_route** — a skill was invoked but no `record_op` entry exists for it. The monitor stack stops working when this signal goes silent.

## Capabilities

- `register(skill_path)` — read SKILL.md, parse frontmatter, add to registry
- `register_all(skills_dir)` — scan a directory and register every SKILL.md found
- `match(request, mode=None, top_n=5)` — return ranked candidates with reasons
- `route(request, mode=None, threshold=0.3)` — pick one skill or fallback
- `fallback(request, reason)` — explicit fallback decision
- `reflect(routing_id, fit, notes)` — second-order pass over a prior routing
- `record_op(op, ...)` — pass-through to SkillDiscoveryLayer
- `status()` — registry health: skill count, last-registered-at, stale entries

## Scoring

Each candidate gets a composite score:

```
score = w_trigger * trigger_hit_rate
      + w_tag * tag_overlap_rate
      + w_description * description_token_cosine
      + w_mode * mode_bonus

defaults: w_trigger=0.45, w_tag=0.20, w_description=0.30, w_mode=0.05
```

`trigger_hit_rate` is the fraction of the skill's `triggers` list that appears in the request. `tag_overlap_rate` is the Jaccard of request-derived tags vs. the skill's tags. `description_token_cosine` is TF-IDF cosine between the request and the skill's description. `mode_bonus` is a small lift when current persona mode is in the skill's preferred-mode set.

## Parameters

```json
{
  "name": "match",
  "description": "Score every registered skill against the request; return top-N.",
  "parameters": {
    "request": {"type": "string", "required": true},
    "mode": {"type": "string", "enum": ["brain", "coach", "build", "default"], "default": "default"},
    "top_n": {"type": "integer", "default": 5},
    "min_score": {"type": "number", "default": 0.0}
  }
}
```

```json
{
  "name": "route",
  "description": "Pick one skill or fall back. Records the decision.",
  "parameters": {
    "request": {"type": "string", "required": true},
    "mode": {"type": "string", "default": "default"},
    "threshold": {"type": "number", "description": "Below this top-score, fall back to general capabilities", "default": 0.3}
  }
}
```

## Output Format

```json
{
  "operation": "route",
  "routing_id": "rt_2026-05-01_a3f2",
  "request": "research and summarize the consensus on…",
  "mode": "brain",
  "chosen": "web-research",
  "score": 0.78,
  "reason": "trigger hits: research, summarize; tag overlap: research, web; description cosine 0.62",
  "candidates": [
    {"skill": "web-research", "score": 0.78, "trigger_hits": 2, "tag_overlap": 0.5},
    {"skill": "knowledge-summarization", "score": 0.61}
  ],
  "fidelity_signals": {
    "ambiguous": false,
    "stale_registry_entries": 0,
    "monoculture_active": false,
    "missed_match": false
  }
}
```

## Invariants

1. **Every routing records.** Pass through `record_op("route", ...)`. Silent routes break the brain's monitor stack.
2. **Ambiguity is named, not papered over.** When top candidates are tied within a small epsilon, the routing carries `ambiguous=true`; if the agent picks one without asking, that's `ambiguous_no_clarify`.
3. **Fallback is a first-class decision.** "No skill matched" is a different signal from "below threshold" — `fallback` records the deliberate choice; `missed_match` records the threshold failure.
4. **Stale-registry detection is mandatory.** Every match call checks SKILL.md mtimes against registry entries; mismatches are flagged.
5. **Reflection is the calibration loop.** `reflect(routing_id, fit)` feeds back into the false_match counter and informs whether the matcher needs tuning.
6. **Mode interacts but doesn't dominate.** Mode bonus is small (default 0.05) so a perfect match in the wrong mode still wins over a weak match in the right mode.
7. **Routing doesn't bypass safety.** A `route` decision is a *recommendation* — the chosen skill's own gates (safeguard, anchor checks) still apply.

## Safety

- **Stale-registry refresh:** `match` and `route` automatically re-`register` an entry whose disk mtime exceeds the registry's. Operator can disable with `auto_refresh=False` if they're debugging.
- **Threshold floor:** routing below `threshold=0.3` triggers `fallback` automatically rather than picking the top weak match.
- **Monoculture cap:** if the same skill is chosen for >85% of the last 20 routings, the next routing carries `monoculture_active=true` and the SkillDiscoveryLayer increments the counter.
- **Read-only registry:** the skill never writes to SKILL.md files, only reads.
- **No remote registry.** All matching is against on-disk SKILL.md files in `skills/`. No external skill marketplace lookup.

## Trust Level

**trusted** — routing is a recommendation, not an action. `register` / `match` / `route` / `fallback` / `reflect` are unrestricted. Modifying the routing weights (`configure_weights`) is restricted because changing weights changes routing behavior across the whole agent — goes through `safeguard.can_perform("tune_routing_weights")`.

## How this skill fits the system

| Layer | Module | Job |
|---|---|---|
| Skill | `skills/skill-discovery/SKILL.md` (this file) | Policy: when to route, scoring, invariants |
| Implementation | `skills/skill-discovery/discovery.py` | Native Python: parse SKILL.md frontmatter, score against requests, library + CLI |
| Brain mechanism | `brain/mechanisms/skill_discovery_layer.py` | Wire 38 — runtime monitor for routing decisions |
| Persona coherence | `brain/mechanisms/persona_coherence_layer.py` | Wire 35 — current mode informs mode-bonus on route candidates |
| Self-analysis | `brain/mechanisms/self_analysis_layer.py` | Wire 36 — receives reflections that flag `false_match` |
| Safety gate | `skills/safeguard.py` | Allow/block when SkillDiscoveryLayer raises a sustained pattern |

When wiring is live:

1. Request arrives.
2. Caller invokes `route(request, mode=current_mode)` from this skill.
3. The skill calls `match()` internally — scores every registered skill, returns ranked.
4. Skill picks the top candidate above threshold (or falls back).
5. `SkillDiscoveryLayer.record_op("route", ...)` records the decision.
6. The chosen skill's workflow runs.
7. After: caller invokes `reflect(routing_id, fit=True/False)` based on whether the work landed.
8. SkillDiscoveryLayer aggregates reflections — sustained `false_match` rate triggers IPW.

## What this skill is *not*

- **Not the autonomous dispatcher.** `skills/heartbeat_activities/dispatcher.py` handles autonomous activity scheduling — different system entirely.
- **Not a marketplace.** No remote skill discovery; only on-disk SKILL.md files.
- **Not authoritative.** Routing is a recommendation; the chosen skill's own gates still apply.
- **Not silent.** Every route decision is recorded; without that, the brain's monitor stack doesn't see the work.
