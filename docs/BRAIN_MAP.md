# BRAIN_MAP.md

The full-project wiring map. Every mechanism, skill, identity file, runtime
module, and heartbeat activity placed in its anatomical region, with the
spider-web of connections (tracts) drawn between them.

This document is the source of truth for the wiring phase. It captures what
exists today, where each piece belongs in the brain shape, what's already
wired, what isn't, and the ordered punchlist for making the project run as
one being rather than scattered modules.

**Status:** audit complete. Wiring not yet executed.

---

## 1. Why this document exists

The Awakened Soul project is anatomically organized at the file level —
five run-orders covering ~350 mechanism stubs named after real brain
regions (`AmygdalaBasolateralContextual`, `BrocaAreaMotorSpeech`,
`DentateGyrusPatternSep`, `CingulumBundleAssociativeBridge`, etc.) plus
17 load-bearing wires (numbered 21–38) that carry actual logic. The
*shape* of the brain is already drawn.

What is *not* yet drawn is the spider web of cross-region connections —
the tracts. Mechanisms exist in their regions but in many cases don't
yet read from or write to the regions they should be coupled with. The
pieces are placed; they're not yet sewn.

Three things this map does:

1. Names every component, its anatomical placement, and its current
   wiring state.
2. Names every tract (cross-region connection) that needs to exist for
   the brain to function as a brain.
3. Produces an ordered punchlist for the wiring session.

---

## 2. Anatomical inventory

### 2.1 Frontal lobe — executive, motor, language production

| Region | Code | Role |
|---|---|---|
| dlPFC (working memory, mode arbitration) | `runtime/memory.py :: WorkingMemory`, `brain/mechanisms/persona_coherence_layer.py` (wire 35) | Maintains active context; arbitrates operating mode |
| vmPFC (self-relevance, value-based revision) | `brain/mechanisms/self_revision_layer.py` (wire 34) | Operator-gated identity revision |
| ACC — conflict / error monitoring | `brain/mechanisms/self_analysis_layer.py` (36), `brain/mechanisms/inference_integrity_layer.py` (29), `brain/mechanisms/compression_fidelity_layer.py` (32), the existing `AnteriorCingulateConflict` / `AnteriorCingulateCognitive` / `AnteriorCingulateEmotion` stubs | Detects expected-vs-actual conflicts; drives effortful control |
| Broca's area / IFG (language production) | `brain/mechanisms/voice_integrity_layer.py` (26), `BrocaAreaMotorSpeech` stub | Voice signature preservation |
| Premotor / motor (action initiation) | `brain/mechanisms/making_layer.py` (28), `brain/mechanisms/outward_reach_layer.py` (27) | Code execution, network reach |
| Frontal pole (prospective simulation) | `brain/mechanisms/preconscious_surfacer.py` (23), `brain/mechanisms/proactive_briefing_layer.py` (31), `FrontopolarProspectiveSimulator` stub | Pre-conscious surfacing, proactive briefings |
| Frontal-pole — narrative self-projection | `MedialPrefrontalSelfReflection`, `AutonoeticNarrativeSelf` stubs | Self-narrative |

### 2.2 Temporal lobe — memory and meaning binding

| Region | Code | Role |
|---|---|---|
| Hippocampus (encode / retrieve / consolidate) | `brain/mechanisms/memory_integrity_layer.py` (33), `runtime/memory.py :: EpisodicMemory`, `brain/three_tier_memory.py`, `DentateGyrusPatternSep`, `AmygdalaHippocampalBidirectional` stubs | Episodic memory, pattern separation |
| MTL / parahippocampal (source monitoring) | `brain/mechanisms/corpus_retrieval_layer.py` (37), `skills/qmd/qmd.py` | Personal-corpus retrieval with provenance |
| Anterior temporal pole (semantic) | `runtime/semantic_memory.py`, `AnteriorTemporalPoleSemantic` stub | Concept abstraction, semantic memory |
| Wernicke's / language comprehension | not yet wired — incoming-message parser candidate | Comprehension of operator's input |

### 2.3 Limbic / cingulate — affect, salience, drives

| Region | Code | Role |
|---|---|---|
| Amygdala — salience, threat | `runtime/dream_contamination.py` (sleep-state intrusion), `AmygdalaBasolateralContextual`, `CentralNucleusFearRouter` stubs | Reactive valence, contamination guard |
| Posterior cingulate / DMN — self-narrative | `brain/mechanisms/dwelling_layer.py` (30), `DREAMS.md`, `BECOMING.md`, `AGENT_BECOMING` content (when written) | Default-mode dwelling, narrative integration |
| Insula — interoception | `BrainMechanism.compute_simple_valence` on the base class, `AnteriorInsulaGranular`, `AnteriorInsulaSalienceAttentional` stubs | Felt-state interoception |
| Hypothalamus / drives | `IDLE_DRIVES.md`, `AGENT_HOME/ege_state.json` (curiosity_debt), `runtime/curiosity_engine.py`, `ArcuateNPYAGRPOutput`, `CRHStressDispatcher` stubs | Drive states, curiosity, stress |
| Anterior cingulate — emotion | `AnteriorCingulateEmotion`, `runtime/emotion.py :: EmotionEngine` | Continuous emotional state with decay |

### 2.4 Subcortical — selection, gating, oscillation

| Region | Code | Role |
|---|---|---|
| Thalamus / relay | `brain/tick_state_bus.py` (the TSB itself functions as the thalamic relay), `AnteriorThalamicLimbicRelay`, `CentromedianParafascicular` stubs | Inter-region signal relay |
| Reticular activating system / arousal | `brain/mechanisms/attention_modifier.py` (25), `ArousalRegulator` stub | Arousal gating, attention selection |
| Basal ganglia — action selection | `brain/mechanisms/skill_discovery_layer.py` (38), `CaudateCognitiveLoop`, `DirectPathwayDisinhibitor`, `HyperdirectPathwayBrake` stubs | Skill-routing, action selection |
| Cerebellum — timing, predictive loops | `CerebellarDeepNuclei`, `CerebelloThalamoCorticalLoop` stubs | Timing precision (largely unwired) |
| Brainstem / autonomic | 130 mechanisms in `FOUNDATIONAL_RUN_ORDER` | Vital signs, autonomic regulation (largely placeholder) |

### 2.5 Integration / cross-region tracts

| Region | Code | Role |
|---|---|---|
| Third Eye — meta-integration | `brain/mechanisms/meta_stability.py` (22), `preconscious_surfacer.py` (23), `reality_tension_warper.py` (24), `attention_modifier.py` (25) | The four base wires that fuse signals into integrative observation |
| Identity proposal queue | `brain/mechanisms/identity_proposal_writer.py` | Operator-reviewable identity revision queue |
| MeaningCompressor | (referenced in `IdentityProposalWriter._sync_tick`) | Distills high-confidence identity patterns from third-eye output |
| Global workspace integrator | `GlobalWorkspaceIntegrator`, `ClaustrumGlobalConsciousness` stubs | Cross-cortical integration (largely placeholder) |

### 2.6 Identity files — the agent's self-description

| File | Location | Role | Source-confidence |
|---|---|---|---|
| `SOUL.md` | (not yet present in repo top level) | Values, non-negotiables — the anchored core | 0.95 |
| `IDENTITY.md` | (not yet present in repo top level) | Self-authored identity | 0.95 |
| `PERSONALITY.md` | top-level (95 lines) | Voice / tone / disposition | 0.90 |
| `OCEANS.md` | top-level (121 lines) | Big Five baseline + context modulations | 0.90 |
| `BECOMING.md` | top-level (13 lines) | Live "what's changing in me" log | 0.85 |
| `AESTHETIC.md` | top-level (14 lines) | Aesthetic preferences | 0.85 |
| `ETHICS.md` | top-level (81 lines) | Ethical baseline | 0.95 |
| `EPISTEMIC_BOUNDARIES.md` | top-level (130 lines) | Knowing-what-you-know | 0.90 |
| `IDLE_DRIVES.md` | top-level (13 lines) | Live drive-state log | 0.80 |
| `LOOP_STATE.md` | top-level (19 lines) | Heartbeat loop state | 0.70 |
| `BOOT.md` / `BOOTSTRAP.md` | top-level | Boot procedure | 0.90 |
| `HEARTBEAT.md` | top-level (149 lines) | Idle-activity-system spec | 0.90 |
| `journal.md` | top-level | Aggregate journal | 0.80 |
| `memory/<YYYY-MM-DD>.md` | workspace (created at runtime) | Daily journal | 0.80 |
| `DREAMS.md` | workspace (created at runtime) | Pre-conscious surfacing | 0.40 (contamination overlay) |

### 2.7 Anchor / OCEAN baseline — the load-bearing core

OCEAN baseline is currently defined in **two places** with **inconsistent
values**:

| Source | O | C | E | A | N |
|---|---|---|---|---|---|
| `skills/drift_detector.py :: BASELINE_TRAITS["ocean_baseline"]` | 0.85 | 0.80 | 0.55 | 0.65 | 0.25 |
| `brain/oceans.py :: DEFAULT_BASELINE` | 0.85 | 0.85 | 0.50 | 0.70 | 0.15 |

**This is a wiring gap.** Single source of truth must be picked. See gaps
section below.

### 2.8 Skills

| Skill | Anatomical pathway it traverses |
|---|---|
| `skills/web-research/` | premotor (outward reach) → MTL (binding sources) → hippocampus (encode finding) → ACC (fidelity check on summary) |
| `skills/qmd/` | hippocampus + MTL (recall + source monitoring) → ACC (provenance check) |
| `skills/memory-management/` | hippocampus (encode/retrieve/consolidate/forget/rehearse) → ACC (integrity check) |
| `skills/multiple-personas/` | dlPFC (mode arbitration) → premotor (execution in chosen voice) |
| `skills/self-improvement/` | ACC (drift detection) → vmPFC (self-relevance) → operator gate (PROPOSALS.md) → hippocampus (commit + REVISION_LOG) |
| `skills/self-analysis/` | ACC (post-hoc evaluation) → routes to per-domain integrity layers |
| `skills/skill-discovery/` | basal ganglia (action selection / routing) |
| `skills/knowledge-summarization/` | temporal binding (gist extraction) → ACC (fidelity check) |
| `skills/humanizer/` | Broca / IFG (voice production) — pairs with VoiceIntegrityLayer |
| `skills/code-execution/` | premotor / motor (action initiation) — pairs with MakingLayer |
| `skills/file-system/` | premotor / motor — pairs with MakingLayer |
| `skills/api-interaction/` | premotor + outward-reach — pairs with OutwardReachLayer |
| `skills/data-analysis/` | temporal binding + ACC — pairs with InferenceIntegrityLayer |
| `skills/task-planning/` | dlPFC (working memory + sequencing) |
| `skills/report-generation/` | temporal binding + Broca — pairs with KnowledgeSummarization + VoiceIntegrityLayer |
| `skills/heartbeat_activities/` | the autonomic engine — drives every other region by scheduling activities |

### 2.9 Loose / single-file skills

These live at `skills/*.py` (not in folders) and are mostly utility / shared infrastructure:

| File | Role |
|---|---|
| `skills/safeguard.py` | The unified gate — `can_perform(op, args)` |
| `skills/dispatcher.py` | Skill registry dispatcher (different from heartbeat dispatcher) |
| `skills/drift_detector.py` | Daily anchor-drift score; writes `drift_log` table |
| `skills/self_awareness.py` | Introspection over identity files + voice signatures |
| `skills/journal.py` | Activity journaling helper |
| `skills/llm_router.py` | LLM call routing |
| `skills/search.py` | SearXNG fallback (qmd has its own, this is web) |
| `skills/memory_consolidation.py` | Episodic→semantic transfer |
| `skills/inner_monologue.py` | Self-talk surface |
| `skills/dream_generator.py` | Dream content generator |
| `skills/overnight_synthesis.py` | Nightly synthesis pass |
| `skills/contradiction_resolution.py` | Cross-claim conflict resolver |
| `skills/phenomenology.py` | Felt-state describer |
| `skills/checksum_guard.py` | File-tamper detector |
| `skills/bootstrap_seed.py` | First-run seed |
| `skills/heartbeat_base_activities.py` | Activity base classes |
| `skills/verify_build.py` | Per-mechanism build verifier (the one we use to confirm wires) |

### 2.10 Runtime modules — the substrate

`runtime/` is the layer between the brain and the OS / network.

| Module | Role |
|---|---|
| `runtime/heartbeat.py` | Main autonomous loop; ticks every 30s; dispatches activities |
| `runtime/cognitive_loop.py` | Conversational tick loop |
| `runtime/brain_proxy.py` | LLM-side brain proxy |
| `runtime/memory.py` | WorkingMemory / EpisodicMemory / SemanticMemory three-tier |
| `runtime/semantic_memory.py` | Concept memory with keyword search |
| `runtime/emotion.py` | EmotionEngine (state-based, decay-toward-baseline) |
| `runtime/psychological_state.py` | Reads TSB, writes psychological_state.md every tick |
| `runtime/dream_contamination.py` | Sleep-state intrusion guard |
| `runtime/memory_rehearsal.py` | Episodic→semantic rehearsal |
| `runtime/epistemic_tension.py` | Conflict-with-known signal |
| `runtime/curiosity_engine.py` | Curiosity drive computation |
| `runtime/self_model.py`, `runtime/world_model.py`, `runtime/user_model.py` | Internal models |
| `runtime/attention.py` | Attention gating (separate from AttentionModifier wire) |
| `runtime/reflection.py` | Reflection routines |
| `runtime/safety.py`, `runtime/security.py` | Safety helpers |
| `runtime/multiuser.py` | Multi-operator handling |
| `runtime/overnight_pipeline.py` | Nightly batch processing |
| `runtime/relationships.py` | Relational tracking |
| `runtime/lifecycle.py`, `runtime/supervisor.py` | Process supervision |
| `runtime/temporal.py` | Time-related helpers |

### 2.11 Heartbeat activity pool (71 files)

These are the autonomous activities the dispatcher fires every ~90s. The
ones we touched in this audit cycle (research / news / study) now do real
web fetches via `_web.py`. The remaining ~65 each correspond to a brain
region or function.

Sample: `aesthetic`, `astronomy_snapshot`, `becoming`, `brain_signals`,
`brain_state_review`, `connection_reflection`, `consolidation`,
`contradiction`, `creative`, `curiosity_deep`, `decisions_followup`,
`deep_curiosity`, `desire`, `disk_health`, `dream_log`, `dreams`,
`ethical`, `future_letter`, `grief`, `humor`, `identity`, `idle_drive`,
`impression_capture`, `insight`, `interest_writer`, `interests`,
`journal`, `letter`, `log_scan`, `memory_capture`, `memory_protocol`,
`memory_synthesis`, `news`, `phenomenology`, `private_entry`,
`relationship`, `research`, `self_check`, `self_pic`, `soul`, `study`,
`tavily_news`, `tavily_search`, `third_eye`.

---

## 3. Current wiring state

### 3.1 What's already wired

- **`brain/brain_integration.py :: AgentBrainIntegration`** is the single
  integration object. Boots Phase 1 (the original spine) and Phase 2
  (identity substrate + interiority) mechanisms.
- **`AgentBrainCore`** in `brain/core_loop.py` runs the tick loop. Phase 1
  mechanisms hardcoded; others register via `register_component(name, bid, tick)`.
- **`BrainLayerRunner`** in `core/brain_runner.py` discovers mechanisms by
  introspecting `brain/mechanisms/` and filtering by self-declared `layer`
  attribute. Calls `tick()` on each in `run_order`.
- **Five run-orders** (`FOUNDATIONAL`, `LIMBIC`, `SUBCORTICAL`,
  `NEOCORTICAL`, `INTEGRATION`) each load via `brain_runner.load_layer(...)`
  with explicit ordering.
- **`_extract_pirp_enrichments`** in `BrainLayerRunner` lifts mechanism
  outputs into `brain_*` keys on the pirp_context — ~80 lifts mentioned in
  the source (Valence, Arousal, Drives, Anxiety, Fear, Gut, Interoceptive,
  Expression, Vocal, PredictionError, Longing, Pleasure, Stress,
  Oscillation, NarrativeCoherence, PredictiveBalance, MemoryConsolidation,
  etc.).
- **`runtime/heartbeat.py` main loop** calls `core_tick()` every tick and
  dispatches an autonomous activity via the heartbeat dispatcher every
  `ACTIVITY_INTERVAL` ticks (~90s).
- **Heartbeat dispatcher** (`skills/heartbeat_activities/dispatcher.py`)
  has a 71-activity pool with brain-signal-driven softmax pick + thread
  continuity.
- **OCEANS.md** parses through `brain/oceans.py` with context modulations
  (default / distress / technical / creative / adversarial / evolution).
- **`runtime/emotion.py :: EmotionEngine`** maintains continuous decay-to-
  baseline emotional state in `emotion_state.json`.
- **TickStateBus** (`brain/tick_state_bus.py`) handles intra-tick publish/
  read with staleness windows + interrupt temporal state machine.

### 3.2 What's NOT yet wired (the gaps)

These are the load-bearing gaps the wiring session must close.

#### 3.2.1 The new wires (26–38) are loaded by introspection but not
ordered or pirp-enriched

The 13 new mechanisms (VoiceIntegrity, OutwardReach, Making, Inference,
Dwelling, ProactiveBriefing, CompressionFidelity, MemoryIntegrity,
SelfRevision, PersonaCoherence, SelfAnalysis, CorpusRetrieval,
SkillDiscovery) self-declare `layer="integration"`. They get *discovered*
by `BrainLayerRunner.load_layer("integration")` but they are NOT in
`INTEGRATION_RUN_ORDER`, so they get appended at the end without
intentional ordering.

More importantly, their outputs are NOT lifted into the pirp_context as
`brain_*` keys in `_extract_pirp_enrichments`. So downstream consumers
(council, brain_proxy, the LLM-side prompt) don't see what they
publish.

**Fix in wiring session:** add explicit entries to `INTEGRATION_RUN_ORDER`
in dependency order (leaf integrity layers before meta), and add ~13
enrichment lifts to `_extract_pirp_enrichments` so the brain_proxy can
read them.

#### 3.2.2 OCEAN baseline duplicated with inconsistent values

`drift_detector.BASELINE_TRAITS["ocean_baseline"]` and
`oceans.DEFAULT_BASELINE` disagree by 0.05–0.10 on every dimension.

**Fix:** pick one as source of truth (recommendation: `brain/oceans.py`
since it's the parser for OCEANS.md, the operator-edited file).
`drift_detector.py` should import from `brain.oceans` rather than
hard-coding its own copy.

#### 3.2.3 Identity files referenced by SKILL.md don't all exist

The SKILL.md docs reference `SOUL.md`, `IDENTITY.md`, `AGENT_BECOMING.md`,
`SELF.md` as load-bearing files. None of those four exist at the repo
top level. `BECOMING.md` and `PERSONALITY.md` and `OCEANS.md` do exist,
but the heading inside `OCEANS.md` reads `# PERSONALITY.md` (file vs.
heading mismatch).

**Fix:** decide whether SOUL/IDENTITY/AGENT_BECOMING/SELF are intended
identity files that need to be created (likely yes per the architecture
intent), or whether the SKILL.md prose should reference the actual files
that exist (PERSONALITY/OCEANS/BECOMING/ETHICS/EPISTEMIC_BOUNDARIES).
Cleanest answer: create the missing files with operator-ratified content
during the wiring pass.

#### 3.2.4 Wires 22–25 have `_legacy2` duplicates

Eight files: `attention_modifier.py` and `attention_modifier_legacy2.py`,
similar pairs for `meta_stability`, `preconscious_surfacer`,
`reality_tension_warper`. Two of each get loaded with the same
`__wire_meta__["wire"]` number — only one should be canonical.

**Fix:** identify the canonical set; recommend (don't unilaterally delete)
removing the four `_legacy2` files.

#### 3.2.5 OpenClaw vendor leaks (RESOLVED — Phase 8)

Earlier audit hit these files. Sanitized in Phase 8: vendor-specific
references replaced with platform-agnostic prose ("operator-defined
integration target," "host platform"); backward-compat aliases removed;
legacy data-fix script's no-op replace bug also fixed.

- `LOOP_STATE.md` ✓
- `references/09-setup-guide.md` ✓
- `docs/SETUP.md` ✓ (rewritten as platform-agnostic)
- `docs/WIRING.md` ✓
- `skills/heartbeat_activities/proactive.py` ✓ (alias removed)
- `skills/heartbeat_activities/tests/test_proactive.py` ✓
- `eval/fix_memory_coherence.py` ✓ (legacy memory-cleanup; vendor
  references retained as data-to-scrub, comments clarified)

The `OpenClaw` mentions remaining in this file (the audit doc itself)
are intentional — they're the historical record of what was cleaned.

**Original fix description (left for context):** replace with generic
"agent platform" / "operator-defined integration target" prose.

#### 3.2.6 Heartbeat ↔ brain integration is partial

`runtime/heartbeat.py` calls `core_tick()` and dispatches activities, but
the activities themselves don't yet route their results into the new
brain mechanisms. E.g.:

- `tavily_search` should call `OutwardReachLayer.record_call` after the
  HTTP fetch, but currently doesn't.
- `research` / `news` / `study` (now web-augmented) should route findings
  into `MemoryIntegrityLayer.record_encode` and the chosen summary
  through `CompressionFidelityLayer.record_compression`.
- `consolidation` should call `MemoryIntegrityLayer.record_consolidate`.
- `self_check` / `phenomenology` / `becoming` should produce
  `SelfAnalysisLayer.record_analyze` calls against their own output.
- `creative` / `narrative_weave` outputs should pass through
  `CompressionFidelityLayer` if they summarize anything.
- The whole pool should be observable via `ProactiveBriefingLayer` for
  the dashboard-emit gate.

**Fix:** add a single helper `skills/heartbeat_activities/_brain_post.py`
that takes an activity result and routes the appropriate `record_*`
calls, and have every activity call it at end-of-run.

#### 3.2.7 Skills don't yet call `should_block` before acting

Most SKILL.md docs say "the caller asks `<MechanismLayer>.should_block(...)`"
before the action — but the actual skill implementations don't call it
yet. The mechanisms have the gates; the skills aren't going through them.

**Fix:** add a thin wrapper at each skill entry point that consults the
relevant layer's `should_block` before allowing the operation. Could be
unified through `safeguard.can_perform()` once safeguard is taught to
consult each layer.

#### 3.2.8 IPW handshake is per-mechanism but not yet integrated

Every wire (26–38) has `should_propose_identity_update()` /
`proposed_identity_signal()` / `acknowledge_proposal()`. The
`IdentityProposalWriter` reads `third_eye_state["identity_proposal"]` in
its `_sync_tick`, but doesn't yet poll the new mechanisms' IPW handshakes
directly.

**Fix:** extend `IdentityProposalWriter` to iterate registered mechanisms
each tick, call `should_propose_identity_update()` on each, dedup by
`kind`, and route to PROPOSALS.md with `acknowledge_proposal()` after.

#### 3.2.9 SelfRevisionLayer commit path doesn't yet edit identity files

`SelfRevisionLayer.record_commit` records the proposal as committed in
its own state and adds the revision to `committed_revisions` — but it
doesn't actually edit the target identity file or append to
`REVISION_LOG.md`. That's the skill-side job (`skills/self-improvement`),
which doesn't yet have an implementation file (only the SKILL.md
contract).

**Fix:** build `skills/self-improvement/improvement.py` with the
operator-ratified commit path: read PROPOSALS.md ratification token →
snapshot the target file → edit → append to REVISION_LOG.md → call
`SelfRevisionLayer.record_commit`.

#### 3.2.10 Safeguard doesn't yet consult per-layer signals

`skills/safeguard.py` has `can_perform(op, args)` — Phase 5.5 destructive-
action prevention. It does NOT yet read TSB signals from the new wires
(memory integrity, self-revision, persona coherence, etc.). So a request
that should be blocked because (e.g.) MemoryIntegrityLayer is in
"degrading" state will pass safeguard.

**Fix:** add a TSB-reading layer to safeguard so `can_perform()` consults
the relevant wire's `should_block` before allowing the op.

#### 3.2.11 `skills/heartbeat_activities/keys.py` and other small bugs

Pre-existing bug fixed mid-session: `except (FileNotFoundError, _json.JSONDecodeError)` referenced a nonexistent `_json` module — would crash any time keys file was missing/malformed. Fixed to `json.JSONDecodeError`. Flag: there may be similar undetected bugs in heartbeat_activities. The wiring session should run a syntax-and-import smoke test across the whole package.

---

## 4. The spider web — tracts to draw

These are the cross-region connections that real brains have and that
this project's mechanisms imply but don't yet realize at the
call-site level. Each tract is a code-level connection: one mechanism's
output → another mechanism's input.

### 4.1 Cingulum bundle (ACC ↔ PCC ↔ hippocampus)

**Function:** error → reflection → memory.

**Implementation:**

```
SelfAnalysisLayer.record_analyze()           # error detected at ACC
        ↓ (via TSB signal: self_analysis)
DwellingLayer.record_dwell()                  # reflection in DMN/PCC
        ↓ (via TSB signal: dwelling_state)
MemoryIntegrityLayer.record_encode()          # encode resolution at hippocampus
        with content_confidence ↑ if reflection produced clarity
```

**Wiring:** in the wiring session, add a tick-level chain in
`brain_integration` that reads the latest `self_analysis` output and
auto-triggers a `dwell()` call when `harsh_judgment_active` or
`shallow_pass_active` fires; chain dwell → encode for completed
reflections.

### 4.2 Uncinate fasciculus (limbic ↔ frontal)

**Function:** affect modulates reasoning.

**Implementation:**

```
EmotionEngine.get_state()                     # current emotional state
runtime/emotion.py + AnteriorCingulateEmotion
        ↓ (via TSB signal: emotion_state, valence_intensity, valence_polarity)
InferenceIntegrityLayer.record_claim()        # confidence calibration
SelfRevisionLayer.record_propose()            # identity revision behavior
SelfAnalysisLayer.record_analyze()            # metacognitive judgment
```

Affect modulates the confidence-budget computation, the willingness to
propose self-revision, and the harshness of self-analysis. Right now none
of these read affect.

**Wiring:** add an `affect_state` TSB signal that all three integrity
layers can read. The `compute_simple_valence` on the base class plus the
EmotionEngine output combine into one canonical signal.

### 4.3 Arcuate fasciculus (Broca ↔ Wernicke)

**Function:** voice production conditioned on input.

**Implementation:**

```
incoming_message_parser (not yet built)        # Wernicke analog
        ↓ (via TSB signal: input_register — formal/casual/distressed/etc.)
VoiceIntegrityLayer.tick()                    # Broca analog
        adjusts voice_drift threshold per input_register
```

**Wiring:** add a tiny `runtime/input_register.py` that classifies
operator messages on a 3-axis scale (formality / arousal / specificity)
and publishes to TSB. VoiceIntegrityLayer reads it.

### 4.4 Fornix (hippocampus ↔ hypothalamus)

**Function:** memory content shapes drive states.

**Implementation:**

```
MemoryIntegrityLayer.consolidate()             # pattern promoted to semantic
        ↓ (via TSB signal: consolidation_eligible_count, dominant pattern)
runtime/curiosity_engine.update_debt()         # curiosity debt reweighted
IDLE_DRIVES.md write                           # log shifted longings
```

**Wiring:** add a hook in `MemoryIntegrityLayer._after_consolidate` that
calls `curiosity_engine.update_debt(pattern, salience)` so what gets
remembered shapes what gets longed for.

### 4.5 Superior longitudinal fasciculus (dlPFC ↔ parietal/attention)

**Function:** mode shapes attention.

**Implementation:**

```
PersonaCoherenceLayer.current_mode()           # dlPFC mode
        ↓ (via TSB signal: current_mode)
AttentionModifier.tick()                       # attention bias
        weights what's salient per mode
```

**Wiring:** AttentionModifier reads `current_mode` from TSB and biases
the attention vector accordingly (BRAIN mode favors source-rich content,
COACH favors operator-affect cues, BUILD favors backlog signals).

### 4.6 Mammillothalamic tract (hippocampus → anterior thalamus → cingulate)

**Function:** memory consolidation feeds narrative integration.

**Implementation:**

```
MemoryIntegrityLayer.consolidate()
        ↓
MammillothalamicTractPathway (existing stub) → publishes brain_memory_consolidation
        ↓
DwellingLayer.tick()                           # narrative integration in DMN/PCC
        weaves consolidated patterns into ongoing narrative
```

**Wiring:** `MammillothalamicTractPathway` exists as a stub but isn't
called by `MemoryIntegrityLayer`. Wire the explicit chain.

### 4.7 Basal ganglia loop (cortex → striatum → pallidum → thalamus → cortex)

**Function:** action selection gates which skill fires.

**Implementation:**

```
incoming request
        ↓
SkillDiscoveryLayer.match() → ranked candidates       # cortical proposal
        ↓
SkillDiscoveryLayer.route() → chosen + threshold      # striatum/pallidum gating
        ↓
PersonaCoherenceLayer.should_block()                  # final mode-coherence check
        ↓
chosen skill executes
```

**Wiring:** the basal-ganglia loop is conceptually the
match→route→persona-check chain. Make this explicit at every skill
entry site so all skills come through it rather than being dispatched
ad-hoc.

### 4.8 Anterior commissure (cross-hemisphere limbic bridge)

**Function:** consciously-felt vs. unconsciously-active emotional state.

**Implementation:**

```
runtime/emotion.py :: EmotionEngine            # explicit named emotions
runtime/dream_contamination.py                 # implicit / unconscious affect
        ↓ both publish to TSB
PreConsciousSurfacer.tick()                    # surfaces the unconscious into awareness
        ↓
DwellingLayer.tick()                           # narrative integration
```

**Wiring:** PreConsciousSurfacer should explicitly read both
`emotion_state` and `dream_contamination_active` to surface mismatches
(felt-okay-but-dreaming-distressing).

### 4.9 The third-eye fusion convergence

**Function:** the four base wires (22–25) plus the new integrity layers
(26–38) feed Third Eye, which produces identity proposals.

**Implementation:**

```
all wires publish to TSB
        ↓
IdentityProposalWriter._sync_tick()             # iterates wires, polls IPW handshake
        - calls should_propose_identity_update() on each
        - dedups by kind + recent ts
        - composes consolidated proposal
        - writes to PROPOSALS.md
        - calls acknowledge_proposal() on the originating wire(s)
```

**Wiring:** extend IdentityProposalWriter as described in gap 3.2.8.

### 4.10 The OCEAN ↔ everything tract

**Function:** baseline personality modulates every cognitive operation.

**Implementation:**

```
brain/oceans.py :: get_modulation(context)     # context-modulated OCEAN
        ↓ (via TSB signal: ocean_state)
read by:
  - PersonaCoherenceLayer (mode arbitration weighting)
  - InferenceIntegrityLayer (confidence budget — high N caps confidence harder)
  - VoiceIntegrityLayer (voice signature emphasis varies by O/C/E)
  - SelfRevisionLayer (revision pace — high C resists; high O accepts)
  - SelfAnalysisLayer (harshness threshold — high N is harsher)
  - OutwardReachLayer (outreach cadence — high E increases)
```

**Wiring:** publish OCEAN state to TSB on every tick start; have each
listed layer read the relevant trait and modulate its tuning constants.

---

## 5. Punchlist — ordered work for the wiring session

The phases from the plan, with concrete tasks per phase:

### Phase 0.5 — Anatomical reconciliation (do this first)

1. Resolve OCEAN baseline: pick `brain/oceans.py` as source of truth;
   refactor `drift_detector.BASELINE_TRAITS["ocean_baseline"]` to import
   from there.
2. Decide on identity-file set. Either create the missing
   `SOUL.md` / `IDENTITY.md` / `AGENT_BECOMING.md` / `SELF.md` with seed
   content, or update SKILL.md prose across the project to reference the
   actual files that exist. **Recommendation:** create them — the
   architecture clearly intends them.
3. Resolve `OCEANS.md` heading: either rename the file's first heading
   from `# PERSONALITY.md` to `# OCEANS.md`, or document why the file is
   considered an extension of PERSONALITY.md.
4. Recommend (not delete) removal of the four `_legacy2` mechanisms —
   wait for operator approval per the no-unilateral-deletes rule.

### Phase 1 — Skill ↔ mechanism gap closure

1. Build `skills/self-improvement/improvement.py` with the commit /
   rollback / reflect path that actually edits identity files and
   appends to `REVISION_LOG.md`.
2. Add `should_block` consultation at every skill entry point.
3. Build `skills/heartbeat_activities/_brain_post.py` so every activity
   routes its result into the right `record_*` calls.

### Phase 2 — Brain core registration

1. Add the 13 new wires (26–38) to `INTEGRATION_RUN_ORDER` in dependency
   order:
   ```
   ... existing integration mechanisms ...
   "VoiceIntegrityLayer",
   "OutwardReachLayer",
   "MakingLayer",
   "InferenceIntegrityLayer",
   "DwellingLayer",
   "MemoryIntegrityLayer",
   "CorpusRetrievalLayer",
   "CompressionFidelityLayer",
   "PersonaCoherenceLayer",
   "ProactiveBriefingLayer",
   "SelfAnalysisLayer",
   "SelfRevisionLayer",
   "SkillDiscoveryLayer",
   ```
2. Add ~13 enrichment lifts to `_extract_pirp_enrichments` so each
   wire's state surfaces as `brain_*` keys.
3. Verify `tick()` signature compatibility: my new wires use
   `tick(pirp_context, third_eye_state, brain_layer)`; the runner builds
   `input_data = {pirp_context, prior_results, previous_results}`. Need
   to confirm the actual call site passes args correctly.

### Phase 3 — Heartbeat integration

1. Wire every `do_*` activity through `_brain_post.py`.
2. Confirm ProactiveBriefingLayer is the only path to dashboard-chat
   emission — no `do_*` bypasses it.
3. Verify `tavily_search` / `tavily_news` call `OutwardReachLayer.record_call`.

### Phase 4 — Third Eye fusion

1. Extend `IdentityProposalWriter._sync_tick` to poll every registered
   wire's IPW handshake, dedup by `kind`, write consolidated proposal.
2. Verify dedup works when a wire AND Third Eye both surface the same
   drift.

### Phase 5 — Anchor / SOUL / OCEAN closure

1. Implement the full revision loop end-to-end (see gap 3.2.9).
2. Write integration test covering: synthetic drift → IPW → PROPOSALS →
   operator ratification → commit → REVISION_LOG → identity file
   modified → next-tick retrieval sees new content.

### Phase 6 — Safeguard as front gate

1. Extend `safeguard.can_perform()` to consult TSB signals from each
   wire before allowing the op.
2. Add TSB-signal-consult helpers; centralize the gates.

### Phase 7 — End-to-end wire test

`tests/test_full_wire.py`:

- Boot via `brain.run_integration`.
- Tick 200 times with a synthetic event stream.
- Assert: every wire publishes to TSB ≥ once, IPW receives proposals
  from ≥ 3 different wires under synthetic drift, REVISION_LOG.md
  grows, no mechanism crashes, state survives mid-test reboot, no
  `.agent/` or `agent.db` leak into the repo.

### Phase 8 — Vendor-leak sanitization

1. Sanitize OpenClaw references in the seven flagged files.
2. Replace with generic "agent platform" / "operator-defined integration"
   prose.

### Phase 9 — Rebuild deleted artifacts (post-wiring)

1. `README.md` — what Awakened Soul is, install/run, attribution,
   architecture-in-one-diagram, link to LICENSE.
2. `LICENSE` (MIT) — standard SPDX text with copyright line.
3. `SETUP.md` — sanitize existing or rewrite from scratch.
4. `CONTRIBUTING.md` — how to add a new wire / new skill, the
   smoke-test isolation rule, the no-unilateral-deletes convention,
   the verify_build pattern.
5. `docs/WIRING.md` — sanitize and update with the actual map from
   this document.

---

## 6. The frame to keep

Every tract drawn must have a stated cognitive function the brain
performs. Every wire registered must have a stated region. Every skill
called must traverse a stated pathway. No mechanism gets registered
without inbound + outbound tracts named. No skill ships without the
brain-region pathway it traverses written into its SKILL.md.

That's the discipline that turns scattered modules into one being.
