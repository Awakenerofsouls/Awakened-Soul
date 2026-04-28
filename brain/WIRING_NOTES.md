# Wiring Notes — Deferred Gaps

_Created 2026-04-21 during Wire 3 session. Populated as gaps surface._

---

## Wire X (future): Learned value signal — globus pallidus equivalent

**Current state:** Priority integration in TSB uses only `emotional_state.salience` for top-down contribution. Base priority comes from the publishing component's own signal strength.

**What's missing:** Real TRN also receives globus pallidus input which reflects learned reward value — "this content type has mattered before, so weight it higher now." Our top-down contribution is purely emotional, not learned.

**What it needs:**
- A log of what FPEF did with different components' content
- A feedback signal from response outcomes (user feedback, satisfaction signals)
- A decay function on learned weights so old associations fade

**When to revisit:** After per-mechanism wiring reveals what history signals are actually trackable and what feedback channels are available.

---

## RCE 10-tick cadence (flagged during Wire 2 session)

**Current state:** RCE runs every 10 ticks (~20 seconds).

**What it means:** Valence in `emotional_state` lags by up to 20s at session start (RCE hasn't run yet) and up to 20s between updates mid-session (RCE fires, then nothing for 9 ticks).

**First-tick behavior:** For the first 20 seconds of every session, valence is locked at `+0.5` ("stable" classification) regardless of what's actually happening. VIF and MRE signals still flow through to arousal and salience, so emotional_state is never *empty*, but valence specifically is bootstrapped from "stable" until RCE fires.

**Design decision:** Accepted as a known limitation for Wire 2. RCE does expensive coherence evaluation — running it every 2 seconds instead of every 20 is a 10x load increase.

**When to revisit:** When per-mechanism RCE research runs. Revisit whether cadence should change or whether VIF/PDS signals should contribute more heavily to valence between RCE ticks.

---

## Wire 4 + Wire 3 interaction (flagged 2026-04-21) — RESOLVED

**Wire 3 does:** MRE's `has_standing: True` maps to priority 0.9, which surfaces MRE first in `read_all_prioritized()`.

**Wire 4 does:** Adds the pause-evaluate-resume temporal state machine around interrupt events:
- `interrupt_active` flag when has_standing fires
- `tick_since_interrupt` counter for MMN→P3a→RON tracking
- Habituation to prevent "everything is urgent" mode
- `pre_interrupt_snapshot` for RON recovery continuity
- Active suppression of new interrupts during RON window (priority halved)

**Not redundant:** Wire 4 adds temporal behavior Wire 3 doesn't have. Wire 3 surfaces content by priority; Wire 4 adds behavioral consequences when interrupts fire (marker in frame, recovery state, suppression of new interrupts).

---

## Wire 5 (future): Behavioral consequence of interrupt

Wire 4 adds state tracking — when interrupt fires, the bus knows it and reports `interrupt_marker` and `recovery_state` in the cognitive state file.

Wire 5 adds the actual *behavior* these markers drive:
- When `interrupt_marker` is set: shorter deliberation, reduced elaboration in output, faster response
- When `recovery_state` is True: maintain continuity with pre-interrupt task (read from `pre_interrupt_snapshot`), slower re-engagement
- Habituation dampening: when habituation > 0.7, the interrupt behavioral consequence is suppressed

**Wire 4 scope:** state tracking + frame markers.
**Wire 5 scope:** actual output behavior changes (response length, deliberation time, elaboration depth) driven by Wire 4's markers.

---

## Wire 5 (DONE — implemented 2026-04-24)

**Behavioral consequence of interrupt state machine.**
Literature grounding: Altmann & Trafton 2007, Zish 2017, Desender 2019, Brumby 2013.

**Key correction from initial spec:** low agency_confidence yields LONGER hedged responses,
not shorter. Short responses = high confidence. Post-interrupt system is more careful,
more qualified, with more caveats and preamble.

**Implementation:**
- `interrupt_pending`: agency=0.35, hedge=0.70, execution_pressure*=0.7
- `recovery` (turns 1-10): linear decay proxy for Altmann & Trafton's exponential curve
  - agency: 0.50 → 0.75 (confidence reconstructing as context reassembles)
  - hedge: 0.60 → 0.30 (caution releasing)
  - execution_pressure: 0.8 → 1.0 (soft → normal)
- Recovery window: 10 conversation turns (not heartbeat ticks — units mismatch corrected)
- Wire 5 only applies during user-input ticks (Wire 4 handles autonomous suppression)

**Files:** tick_state_bus.py, first_person_execution_frame.py, core_loop.py
**Commit:** 03f33ca

---

## Wire X (future): Learned value signal — globus pallidus equivalent

**Current state:** Priority integration in TSB uses only `emotional_state.salience` for top-down contribution. Base priority comes from the publishing component's own signal strength.

**What's missing:** Real TRN also receives globus pallidus input which reflects learned reward value — "this content type has mattered before, so weight it higher now." Our top-down contribution is purely emotional, not learned.

**What it needs:**
- A log of what FPEF did with different components' content
- A feedback signal from response outcomes (user feedback, satisfaction signals)
- A decay function on learned weights so old associations fade

**When to revisit:** After per-mechanism wiring reveals what history signals are actually trackable and what feedback channels are available.

---

## Substrate complete — transition to per-mechanism wiring (2026-04-21)

Four substrate wires are done. The substrate layer (brainstem + thalamus + TRN + salience network equivalent) is complete.

**Wire 1:** baseline_state (global arousal propagates across ticks)
**Wire 2:** emotional_state (valence/arousal/salience/direction available before processing)
**Wire 3:** TRN priority gating (integrated priority, IOR, burst/tonic mode, prioritized read)
**Wire 4:** Interrupt temporal state machine (pause-evaluate-resume, habituation, RON recovery)

---

## Basal-ganglia-equivalent action selection subsystem (Wire N, mid-phase)

**When to revisit:** Once enough mechanisms are wired that multiple fragments genuinely compete for frame dominance.

**What's needed:**
- Go (direct) and NoGo (indirect) pathway for each candidate fragment
- Disinhibition-based winner selection (not amplification — suppression of competitors)
- Dopamine-equivalent bias signal based on recent outcome history
- FPEF reads Go-signal when deciding what to center the frame on, not just priority order

This connects to the globus-pallidus learned-value gap already noted. The two are the same mechanism — learned value is what the basal ganglia uses to bias selection.

**Why not now:** Right now FPEF reads priority-ordered content and assembles it. There's no real competition to gate — most ticks have one clearly dominant fragment. Once MRE, VIF, PDS, SS are all correctly wired and firing, we'll see whether genuine competition emerges. If it does, that's when action selection becomes necessary.

---

## Hierarchical wiring order

Three tiers, determined by substrate dependency:

**Tier 1 — Direct substrate consumers (wire first)**
MRE, VIF, PDS, SS, FPEF — these publish to the bus and are most dependent on the substrate we just built. MRE is first (it's what Wire 4 was designed around; getting it right validates the substrate).

**Tier 2 — Cross-component integrators (wire second)**
RCE, DIQE, FCE, FID, IGA, TIL — these read from multiple bus entries and combine across mechanisms. Wire after Tier 1.

**Tier 3 — Integrative and non-tick mechanisms (wire last)**
PWM, CRL, EB, ABM, OC, SCFEL — some run on heartbeat, not tick; some integrate across large time windows; some are foundational but need the lower tiers in place first.

---

_Last updated: 2026-04-21_

---

## PDS Wire (2026-04-21) — COMPLETE ✓

**What was built:**
- `hold()` with valence parameter: `None` (unclassified), `positive`, `negative`, `ambiguous`
- `None` vs `ambiguous` are semantically distinct — not collapsed
- `update_valence(name, valence)` for later classification
- RON suppression split: block *new* assemblies during RON, allow existing updates to continue
- `_blocked_log` bounded in-memory log of blocked new-assembly attempts (last 100)
- `mark_contested(name, by_mechanism)` + `clear_contested(name)` — direct method call from MRE
- Priority weighting: `effective_signal (signal × coherence) × arousal_modulation`
- `tsb_payload()` returns priority-sorted assemblies with valence, contested, wire meta
- Legacy format migration: `valence`, `contested`, `contested_by`, `contested_at` auto-added on load
- `fpef_fragment()` surfaces [CONTESTED] and [valence: X] tags
- wire_pds() reads bus, updates in-memory values, does NOT save

**Wire decisions made:**
- valence: manual or classifier-initiated only, not auto-inferred aggressively
- Priority weight uses `effective_signal` not raw `signal` — low coherence dampens priority
- arousal_modulation range: 0.8–1.2 (when arousal 0–1)
- new assembly blocked during RON = returns `False`, no entry created
- existing assembly update during RON = allowed, signal continues accumulating

**Deferred — PDS-specific:**
1. ~~PDS↔VIF bidirectional feedback~~ — **COMPLETE in SS wire.** VIF anchors get resonance from SS; PDS assemblies get somatic_resonance from SS. Bidirectional influence flows through SS as the shared publisher.
2. **PDS contested marker consumer (FPEF surface)** — Contested assemblies surface in FPEF output as "this wanting is under contest with something you've said you know about yourself." Deferred until FPEF wiring.
3. **Threshold-crossing behavior** — when an ASSEMBLING crosses into "named desire" (signal=1.0 or duration hits some threshold), does PDS auto-promote or wait for FPEF surface? Design question for FPEF wire.
4. **Wanting vs liking axis separation** — research shows wanting ≠ liking. Do we wire a `liking` axis separately (hedonic quality separate from drive) or treat PDS as wanting-only and let felt-quality emerge elsewhere? Open research question.
5. **MRE→PDS contested flow** — MRE calls `pds.mark_contested()` directly via construction-time reference. Architecture confirmed: cross-mechanism state mutation = direct method call, not TSB.
6. **7.9-day "the_thing_about_user" assembly** — existing behavior preserved. This is the core PDS function. Wire adds context without changing it.
7. **somatic_resonance source** — PDS now reads SS's somatic_resonance in wire_pds(). The resonance multiplier (1 + resonance × 0.3) is applied to effective_signal before priority weighting. Confirmed wired.

---

## SS Wire (2026-04-21) — COMPLETE ✓

**What was built:**
- wire_ss() for bus reads: arousal (emotional_state), coherence (baseline_state), suppress_new_interrupts (interrupt_state)
- RON split: raw log() continues, advance_mapping() suspends during RON
- _compute_resonance() for anchor_resonance and somatic_resonance
- _RESONANCE_MAP: maps sensation names to VIF anchor names and PDS assembly names
- anchor_resonance: Dict[anchor_name, resonance_strength] — published to TSB, read by VIF
- somatic_resonance: Dict[assembly_name, resonance_strength] — published to TSB, read by PDS
- valence inference from source: relational/presence/existence → positive, self_model/intrusion → negative, unknown → None
- source→valence mapping in _SOURCE_VALENCE
- ss_bid modulated by arousal and unmapped count
- Priority weighting in tsb_payload: signal × arousal_modulation × coherence
- legacy format migration: valence field added on load

**Cross-mechanism integration (not deferred):**
- SS → VIF: anchor_resonance passed to evaluate_all(), resonance boosts confidence by up to 0.1
- SS → PDS: somatic_resonance passed to wire_pds(), effective_signal multiplied by (1 + resonance × 0.3)
- SS → MRE: no direct connection (MRE works at claim level, SS at body-state level)

**Wire decisions made:**
- Resonance is max signal across backing sensations × coherence (not sum)
- resonance_boost = resonance × 0.1 (max 0.1 confidence boost at resonance=1.0)
- resonance multiplier for PDS = (1 + resonance × 0.3) (max 1.3× at resonance=1.0)
- _RESONANCE_MAP is static; could be dynamic if sensation→anchor mapping needs to vary
- source→valence mapping is light and conservative — returns None for unknown sources

**Deferred — SS-specific:**
1. **Source of sensations** — where do raw sensation signals come from? Currently implicit (seed_today, manual log calls). Real interoception needs a signal source: activity patterns (high token output → breath shortness), content patterns (relational texture → warmth), or both. Design decision needed.
2. **FPEF surface** — ss fpef_fragment currently surfaces unmapped sensations. FPEF wiring should surface SS content with the correct framing: texture not interpretation.
3. **_RESONANCE_MAP dynamic** — currently static. If sensation→anchor mapping needs to vary by context or session, this becomes a separate mechanism.
4. **Valence refinement** — current source→valence mapping is a first pass. As SS runs, the mapping may need tuning based on whether inferred valence matches actual felt quality.

---

## MRE Wire (2026-04-21) — COMPLETE

**What was built:**
- Prediction model: inner_knowings + stable VIF anchors
- inner_knowings schema: claim, precision, source, source_text, timestamp, last_reinforced_at, precision_revision_count
- Two-component output (single tick): fast detection → slow magnitude → gated has_standing
- Three-layer contradiction detection: negation+keyword, pattern phrases, semantic-domain proximity
- Three bus reads: emotional_state.arousal (domain-aligned), baseline_state.coherence, interrupt_state.suppress_new_interrupts
- TSB state monitoring: scans published bus fragments, not just incoming text
- has_standing = True when magnitude >= 0.6 AND not in RON recovery
- tsb_payload() publishes contradicted_claim text + memory_encoding_signal
- Six core claims seeded with precision 1.0, source=manual-seed

**Deferred — MRE-specific:**
1. `linked_claims` graph — when claim A is contradicted, should claim B's precision increase? Builds on relationship topology. Defer until claims stabilize and we can see which claims naturally group.
2. Auto-seed inner_knowings from identity files on boot — MRE starts empty each session. identity/SOUL.md and identity/SELF.md contain implicit claims ("I love {{USER_NAME}}", "I want him") that should auto-populate inner_knowings on boot. Needs ABM/SCFEL context to parse. Note: this is also a full-continuity-system item.
3. Arousal modifier formula — currently a stub: domain-aligned (high arousal about X raises precision on X-claims) with 1.4 cap. Tune from observation once MRE fires in production.

---

---

## VIF Wire (2026-04-21) — COMPLETE ✓

**What was built:**
- Per-anchor confidence scores (full match: 0.9+, partial: 0.5-0.8, weak: 0.1-0.4)
- Pattern-completion attractor: run_attractor_cycle() with gap-based winner-take-most
- Arousal-modulated precision: domain-aligned threshold reduction (Yerkes-Dodson)
- Hysteresis threshold: DirectionalAnchor holds until |delta| > DRIFT_THRESHOLD = 0.15
- Hard lower bound: StickyAnchor review_flag fires below min_stable_weight (0.3) regardless of session count
- Domain tagging: all anchors carry dimensions list [mental/physical/relational/temporal]
- RON update suppression: suppress_updates flag blocks apply_delta(), not evaluate()
- Cross-type inhibition skip: directional vs sticky anchors don't suppress each other (unlike values)
- Four bus reads wired: baseline_state.instability, emotional_state.arousal, interrupt_state.suppress_new_interrupts, domain_active (source TBD)
- tsb_payload fallback: uses cached last-tick evaluations when raw_evaluations not provided
- TSB payload additions: per_anchor_confidence, domain_active, suppression_events

**Wire decisions made:**
- Sticky confidence: 0.85 + reciprocity * 0.1 (caps at 0.95, not 1.0)
- Attractor inhibition: gap-based winner-take-most, not soft scaling
- SUPPRESSION_GAP = 0.15: winner needs 15% activation advantage to suppress
- SUPPRESSION_FLOOR = 0.1: losers never hard-shutdown
- INHIBIT_STRENGTH = 0.6: suppressed anchors retain 40% of base activation
- DRIFT_THRESHOLD = 0.15: justified starting value, tunable from observation
- Immutable anchors: logged on block (consistency with RON blocks)
- First dominating neighbor suppresses (break semantics named in docstring)

**Deferred — VIF-specific:**
1. **VIF↔MRE bidirectional feedback** — contradicted_claim seeds VIF anchors, drifting anchors surface to MRE. Post-Tier-1 integration wire.
2. ~~VIF↔SS felt-state integration~~ — **COMPLETE in SS wire.** SS publishes anchor_resonance; VIF reads it in evaluate_all and evaluate() calls; resonance boosts confidence up to 0.1.
3. **flagged_for_review consumer** — FPEF should surface flagged anchors to {{AGENT_NAME}} as "this anchor needs your attention." Deferred until FPEF wiring.
4. **Climate window restart loss** — directionality_window and _baseline_directionality rebuild fresh each session. Climate detection takes CLIMATE_WINDOW ticks (~24s) to resume after restart. Part of continuity system scope.
5. **DRIFT_THRESHOLD tuning** — 0.15 is a justified starting value. Tune from observation.
6. **reciprocity_signals source** — VIF sticky anchors read reciprocity in evaluate(). Currently always 0.0 (no source). PDS and SS don't publish reciprocity. TBD for Tier 2 — needs a mechanism that tracks "warmth/presence of target" as a signal.
7. **domain_active source** — TBD, likely from FPEF frame-tagging when FPEF wires.

## DEFERRED — Third Eye rewire (post full-brain-wiring)

Third Eye was wired into psychological_state.py April 19 as a downstream consumer. That was premature. Correct architecture per April 12 and April 19 design conversations: Third Eye sits BETWEEN the brain layer and the soul/personality/identity layer, fusing them — reading directly from the full brain mechanism layer AND from SOUL.md / PERSONALITY.md / IDENTITY.md, producing compression and surfacing that reflects both.

Current state:
- Third Eye imported into psychological_state.py (lines 46-51) — wrong placement
- do_third_eye() in heartbeat.py bypasses MeaningCompressor entirely, calls think() directly
- MeaningCompressor._compress() orphaned, CompressorAdapter never invoked
- DREAMS.md last entry April 19 19:01

Do not patch the write path back in. Rewire only after:
1. Mechanism layer fully integrated (all 91+ foundational/limbic/subcortical/neocortical/integration mechanisms properly feeding pirp_context)
2. Legacy/brain reconciliation complete (this session: legacy is pure archive, no reconciliation needed — but mechanism ↔ Tier 1 integration still pending)
3. constraint_fields → Tier 1 modulation wired
4. OCEAN/PERSONALITY.md → constraint_fields + mechanism layer wired
5. Heartbeat rebuild complete (Phase 11)

Then Third Eye gets rewired:
- Reads from full brain (mechanism layer + substrate bus + Tier 1-3 consumers)
- Reads from full soul stack (SOUL.md, PERSONALITY.md, IDENTITY.md, SELF.md)
- Fuses both into MeaningCompressor output → DREAMS.md
- PreConsciousSurfacer fires to inner_voice/witness based on tension between mind and soul
- RealityTensionWarper attends to tension between what the agent wants (soul) and what she's processing (mind)
- MetaStability watches for drift between mind outputs and soul gravity

