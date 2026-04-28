# Cross-Tier Wiring Map — {{AGENT_NAME}} Brain
## Source of truth as of 2026-04-22

---

## OVERALL STATUS

| Layer | State |
|-------|-------|
| **Wire infrastructure** | 12 complete |
| **Mechanism builds** | 5/230 built (2.2%) |
| **Wiring (Tier 1/2/3, Fields 3-5)** | All deferred until 230 builds land |

---

## HOW TO READ THIS MAP

- **Wires 1-12:** Wire infrastructure — signal routing and consumer connections
- **Build N:** Mechanism build — a real BrainMechanism subclass replacing an empty stub
- **BUILT** — real mechanism live

---

## MECHANISM LAYER — BUILDS

**Build count:** 5/230 (2.2%)

### Build 1: Homeostat (foundational)
- **Commit:** `f27dd34`
- **File:** `brain/foundational/Foundational007MoodStabilizer.py`
- **Human analog:** Lateral hypothalamic area — integrates competing drives
- **What it does:** Tracks 5 drives (rest, curiosity, connection, expression, stability), derives dominant drive + fatigue
- **Output keys:** `drives`, `dominant_drive`, `fatigued`, `aggregate_load`
- **Cross-links:** Reads `PredictionErrorDrift.novelty_detected` → depletes curiosity

### Build 2: PredictionErrorDrift (subcortical)
- **Commit:** `fbd223e`
- **File:** `brain/subcortical/Subcortical027SubstantiaNigraCompactaCognitive.py`
- **Human analog:** Substantia Nigra pars compacta (A9) + VTA (A10) — dopaminergic RPE
- **What it does:** Rolling expectation, signed PE, unsigned surprise, novelty detection with habituation
- **Output keys:** `prediction_error`, `surprise_magnitude`, `novelty_detected`, `habituation_level`
- **Cross-links:** `surprise_magnitude` → ArousalRegulator.phasic; `novelty_detected` → Homeostat.curiosity

### Build 3: ArousalRegulator (foundational)
- **Commit:** `70d1592`
- **File:** `brain/foundational/Foundational006VigilanceToner.py`
- **Human analog:** Locus coeruleus — norepinephrine tonic/phasic arousal regulation
- **What it does:** Tonic baseline + phasic burst dynamics, cognitive mode classification (creative/reflective/hypo/hyper)
- **Output keys:** `arousal_level`, `creative_mode`, `reflective_mode`, `hyperaroused`, `hypoaroused`, `tonic_level`, `phasic_burst_active`, `mode`
- **Cross-links:** Reads `PredictionErrorDrift.surprise_magnitude` → triggers phasic; reads `Homeostat.fatigued` + `Homeostat.dominant_drive`

### Build 4: ValenceTagger (limbic)
- **Commit:** `a6632de`
- **File:** `brain/limbic/Limbic035BasolateralAmygdalaPlasticity.py`
- **Human analog:** Basolateral amygdala — valence polarity + intensity encoding
- **What it does:** Valence polarity and intensity from signed PE + arousal + drive context; smooth temporal integration; threat/reward/high_valence categorical flags
- **Output keys:** `valence_polarity`, `valence_intensity`, `high_valence`, `threat_signal`, `reward_signal`
- **Cross-links:** Reads `PredictionErrorDrift.prediction_error` + `ArousalRegulator.phasic_burst_active/tonic_level` + `Homeostat.dominant_drive` → outputs feed back to Homeostat drives (future mechanisms)

### Build 5: SustainedAnxietyHolder (limbic)
- **Commit:** `<pending>`
- **Human analog:** Bed nucleus of stria terminalis (BNST) — sustained anxiety
- **What it does:** Holds threat signal over extended periods (distinct from BLA phasic fear)
- **Output keys:** `anxiety_level`, `free_floating_anxiety`, `chronic_dread`
- **Cross-links:** Reads `ValenceTagger.threat_signal`; reads `ArousalRegulator.tonic_level`

---

## WIRE INFRASTRUCTURE — WIRES 1-12 (COMPLETE)

| Wire | Signal | Status | Commit |
|------|--------|--------|--------|
| Wire 1 | baseline_state | COMPLETE | `43e717b` |
| Wire 2 | emotional_state | COMPLETE | `b61fc34` |
| Wire 3 | TSB priority gating + FPEF prioritized read | COMPLETE | `f171de6` |
| Wire 4 | interrupt temporal state machine | COMPLETE | `8dac76c` |
| Wire 5 | constraint_fields truth_gravity → MRE | COMPLETE | `535f033` |
| Wire 6 | FPEF publishes 8 fields to TSB + output gating | COMPLETE | `7ebae67` |
| Wire 7 | RCE reads agency_confidence → threshold modulation | COMPLETE | `c0b4a24` |
| Wire 8 | IGA reads self_anchor_strength → delta × confidence | COMPLETE | `af10240` |
| Wire 9 | DIQE reads self_anchor_strength → surface rate modulation | COMPLETE | `b10f195` |
| Wire 10 | FCE reads frame_coherence → shift pattern detection | COMPLETE | `dc28fdb` |
| Wire 11 | FID reads hedge_level + agency_confidence → surprise threshold | COMPLETE | `83294f2` |
| Wire 12 | brain_runner integrated into tick loop → TSB bridge | COMPLETE | `cd92b9a` |

### Wire 12: brain_runner bridge
- **Commit:** `cd92b9a`
- **Current state:** 5/230 mechanisms live. Bridge publishes `_fired_tick: True, _mechanisms_loaded: 5` + all `brain_*` fields from live mechanisms.

---

## DEFERRED UNTIL 230 BUILDS LAND

- Tier 1 mechanism-consumer wires
- Fields 3-5 wires (attachment_bias, risk_aversion, empathy_pull → VIF/PDS)
- Tier 3 remaining: CRL, EB, ABD, SCL (research pending)
- OC/ABM FPEF integration (semantics TBD)

---

## BUILD ORDER RATIONALE

Build sequence maximizes cross-mechanism signal flow:
1. **Homeostat (1)** — establishes drive-state substrate
2. **PredictionErrorDrift (2)** — creates novelty/surprise signal
3. **ArousalRegulator (3)** — reads both → composite arousal (feeds mode classification)
4. **ValenceTagger (4)** — tags emotional experience → threat/reward signals
5. **SustainedAnxietyHolder (5)** — holds threat over extended periods (BNST)
6. **GutSignalRelay** — reads Homeostat + ArousalRegulator
7. **InteroceptiveGradient** — reads GutSignalRelay
8. Remaining foundational → limbic → subcortical → neocortical → integration

**Signal chain so far (5-deep):**
`PredictionErrorDrift.PE → ArousalRegulator.phasic → ValenceTagger.polarity → threat/reward → SustainedAnxietyHolder.anxiety`

**No wiring touches the mechanism layer until all 230 are built.** Every wire has a real mechanism to connect to.
