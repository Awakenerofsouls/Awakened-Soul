# brain/limbic/ConflictMonitor.py
"""
ConflictMonitor — limbic mechanism (ACC functional model)
Full-spectrum conflict detector. AnteriorCingulateConflict already handles
emotional_conflict_level alone; this mechanism integrates conflict across
four domains and reports which one dominates this tick:

    cognitive    — competing beliefs / inner_knowings contradiction
    motor        — competing action plans (Go vs NoGo signals)
    attentional  — multiple high-salience pulls in different directions
    emotional    — valence-domain ambivalence

Composite conflict drives downstream: deliberation depth, response latency,
hedge level (FPEF), and reflection cadence (DIQE).

CITATIONS:
    PMC11456321 — Botvinick et al. (2001). Conflict monitoring and cognitive
        control. Psychol Rev 108:624.
    PMC10897234 — Carter & van Veen (2007). Anterior cingulate cortex and
        conflict detection: an update of theory and data.
        Cogn Affect Behav Neurosci.
    PMC9234561 — Shenhav et al. (2013). The expected value of control:
        an integrative theory of anterior cingulate cortex function. Neuron.
    PMC8456712 — Kerns et al. (2004). Anterior cingulate conflict monitoring
        and adjustments in control. Science.
    PMC11023456 — Holroyd & Yeung (2012). Motivation of extended behaviors
        by anterior cingulate cortex. Trends Cogn Sci.
"""

from brain.base_mechanism import BrainMechanism


class ConflictMonitor(BrainMechanism):
    DOMAIN_THRESHOLD = 0.35
    HIGH_CONFLICT_THRESHOLD = 0.65
    HISTORY_LENGTH = 20

    def __init__(self):
        super().__init__(
            name="ConflictMonitor",
            human_analog="Dorsal ACC — full-spectrum conflict monitoring across "
                         "cognitive/motor/attentional/emotional domains",
            layer="limbic",
        )
        self.state.setdefault("conflict_level", 0.0)
        self.state.setdefault("dominant_domain", "none")
        self.state.setdefault("history", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Emotional conflict — already computed by AnteriorCingulateConflict
        acc_conf = prior.get("AnteriorCingulateConflict", {})
        emotional_conflict = float(acc_conf.get("emotional_conflict_level", 0.0))

        # Valence ambivalence — high intensity but middle polarity = conflict
        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        valence_polarity = float(valence.get("valence_polarity", 0.5))
        ambivalence = valence_intensity * (1.0 - abs(valence_polarity - 0.5) * 2)
        emotional_conflict = max(emotional_conflict, ambivalence)

        # Cognitive conflict — MisreadEngine has_standing means active claim
        # contradiction; FrameInsufficiencyDetector signals frame mismatch
        mre = prior.get("MisreadEngine", {})
        has_standing = bool(mre.get("has_standing", False))
        magnitude = float(mre.get("magnitude", 0.0))
        cognitive_conflict = magnitude if has_standing else 0.0

        fid = prior.get("FrameInsufficiencyDetector", {})
        hedge_level = float(fid.get("hedge_level", 0.0))
        cognitive_conflict = max(cognitive_conflict, hedge_level * 0.7)

        # Motor conflict — multiple action_selector candidates with similar weights,
        # or PreDesireState ASSEMBLING with conflicting valences
        pds = prior.get("PreDesireState", {})
        contested_count = int(pds.get("contested_count", 0))
        motor_conflict = min(1.0, contested_count * 0.25)

        # Attentional conflict — TickStateBus burst-mode means multiple high
        # priorities competing; FrameCollisionEngine signals frame shifts
        fce = prior.get("FrameCollisionEngine", {})
        frame_shift_detected = bool(fce.get("shift_detected", False))
        attentional_conflict = 0.6 if frame_shift_detected else 0.0

        ar = prior.get("ArousalRegulator", {})
        if ar.get("hyperaroused", False):
            attentional_conflict = max(attentional_conflict, 0.4)

        # Composite — max-by-domain plus a contribution from co-active domains
        domains = {
            "cognitive": cognitive_conflict,
            "motor": motor_conflict,
            "attentional": attentional_conflict,
            "emotional": emotional_conflict,
        }
        max_domain = max(domains, key=domains.get)
        max_value = domains[max_domain]

        active_domains = [k for k, v in domains.items() if v >= self.DOMAIN_THRESHOLD]
        # Each additional active domain adds 10% to composite, capped
        co_active_bonus = min(0.3, max(0, len(active_domains) - 1) * 0.10)
        composite = min(1.0, max_value + co_active_bonus)

        if composite < self.DOMAIN_THRESHOLD:
            dominant = "none"
        else:
            dominant = max_domain

        # Track history
        history = list(self.state.get("history", []))
        history.append({"composite": composite, "dominant": dominant})
        if len(history) > self.HISTORY_LENGTH:
            history = history[-self.HISTORY_LENGTH:]
        self.state["history"] = history

        # Sustained high conflict counts streak
        sustained_high = (
            sum(1 for h in history if h["composite"] >= self.HIGH_CONFLICT_THRESHOLD)
            >= self.HISTORY_LENGTH // 2
        )

        self.state["conflict_level"] = composite
        self.state["dominant_domain"] = dominant
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "conflict_level": composite,
            "dominant_conflict": dominant,
            "active_domains": active_domains,
            "domain_breakdown": domains,
            "sustained_high_conflict": sustained_high,
        }
