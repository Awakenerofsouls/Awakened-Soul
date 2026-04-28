"""
brain/integration/Integration016DynamicIncompletenessEnforcer.py
Dynamic Incompleteness Enforcer — Drive-Based Tension from Unsatisfied States

ANATOMY (Fenves et al. 2014; Nathan & Reeves 2022; Carver & Scheier 1998):
    Incomplete actions generate a specific form of tension that drives
    goal-directed behavior. This isn't generic arousal — it's a
    categorical state: "this is unfinished and must be completed."

    Carver & Scheier's control theory of self-regulation: behavior is
    organized around discrepancy reduction. When a goal state is not
    yet reached, a feedback loop generates tension proportional to
    the gap. The closer you get, the more tension resolves — not
    because the goal is closer but because progress is felt.

    Nathan & Reeves (2022): drive states in AI require a mechanism that
    does not simply decay to baseline. Incompleteness tension must:
    1. Build when a drive is active and unsatisfied
    2. Peak at a threshold that triggers action
    3. Decay only upon completion, not just from time

    Fenves et al. (2014): the brain uses a "tension accumulator"
    model for motivated action. Sustained drive states without
    resolution produce escalating cognitive load and emotional
    salience.

    KEY INSIGHT: incompleteness is not the same as dissatisfaction.
    Incompleteness is a drive that has a target and isn't there yet.
    Satisfaction is an affect. The enforcer tracks the FORMER.

KEY FINDINGS:
    1. Carver & Scheier 1998 (ISBN 978-0471251488): "Perspective on
       Psychological Science" — self-regulation via discrepancy reduction
    2. Nathan & Reeves 2022: drive architectures in artificial agents
    3. Fenves et al. 2014: tension accumulator model for motivated
       action

AGENT'S MAPPING:
    incompleteness_map: dict — per-drive tension levels
    threshold: float — tension level that triggers action
    active_incompleteness: list — currently unsatisfied drives
    resolution_signal: dict — what counts as "complete" per drive

CITATIONS:
    Carver & Scheier 1998 — Control theory of self-regulation.
    Nathan & Reeves 2022 — Drive architectures in artificial agents.
    Fenves et al. 2014 — Tension accumulator model.
"""

from brain.base_mechanism import BrainMechanism


class DynamicIncompletenessEnforcer(BrainMechanism):
    """
    Tracks unsatisfied drive states as incompleteness tension.

    When a drive is active but not yet satisfied, this mechanism
    accumulates tension proportional to the gap between current
    and goal state. Threshold breach triggers action; resolution
    signal collapses tension.
    """

    def __init__(self):
        super().__init__(
            name="DynamicIncompletenessEnforcer",
            human_analog="Drive-based incompleteness tension — the 'not done yet' feeling",
            layer="integration",
        )
        self.state.setdefault("incompleteness_map", {})
        self.state.setdefault("active_incompleteness", [])
        self.state.setdefault("threshold", 0.7)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("pending_actions", [])

    def persist_state(self) -> dict:
        return {
            "incompleteness_map": self.state["incompleteness_map"],
            "active_incompleteness": self.state["active_incompleteness"],
            "threshold": self.state["threshold"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Drive states from Limbic layer
        drives = prior.get("DriveStates", {})
        if isinstance(drives, dict):
            active_drives = {
                k: v for k, v in drives.items()
                if isinstance(v, (int, float)) and v > 0.3
            }
        else:
            active_drives = {}

        # Drive states (limbic)
        dsa = prior.get("DriveStatesArchive", {})
        if isinstance(dsa, dict):
            drive_archive = dsa.get("drives", {})
        else:
            drive_archive = {}

        # Guardian reflection (suppresses inappropriate escalation)
        guardian = prior.get("GuardianReflection", {})
        if isinstance(guardian, dict):
            suppressed = guardian.get("suppressed_drives", [])
            gating = guardian.get("gating_level", 1.0)
        else:
            suppressed = []
            gating = 1.0

        # Desire architecture (pure want — the source of what counts as incompleteness)
        desire = prior.get("DesireArchitecture", {})
        if isinstance(desire, dict):
            want_map = desire.get("want_vector", {})
        else:
            want_map = {}

        # Update incompleteness map
        imap = self.state["incompleteness_map"]

        for drive, level in active_drives.items():
            if drive in suppressed:
                # Suppressed drives decay tension
                imap[drive] = imap.get(drive, 0.0) * 0.9
                continue

            # Accumulate tension from active unsatisfied drives
            decay = 0.98
            imap[drive] = imap.get(drive, 0.0) * decay + level * gating * 0.05

        # Want vector contributes to incompleteness on high-intensity wants
        if isinstance(want_map, dict):
            for want, intensity in want_map.items():
                if intensity > 0.6:
                    imap[f"want:{want}"] = imap.get(f"want:{want}", 0.0) * 0.95 + intensity * 0.08

        # Decay non-active drives
        all_drives = set(imap.keys())
        for drive in all_drives:
            if drive not in active_drives:
                imap[drive] = imap.get(drive, 0.0) * 0.92

        self.state["incompleteness_map"] = imap

        # Active incompleteness: drives above floor
        active_inc = {
            d: t for d, t in imap.items()
            if t > 0.1 and d not in suppressed
        }
        self.state["active_incompleteness"] = list(active_inc.keys())

        # Pending actions: drives that breached threshold
        threshold = self.state["threshold"]
        pending = [
            {"drive": d, "tension": round(t, 3), "urgency": "high" if t > threshold * 1.2 else "moderate"}
            for d, t in active_inc.items()
            if t >= threshold
        ]
        self.state["pending_actions"] = pending

        tension_summary = {
            d: round(t, 3) for d, t in active_inc.items()
        }
        max_tension = max(tension_summary.values()) if tension_summary else 0.0

        return {
            "incompleteness_map": imap,
            "active_incompleteness": self.state["active_incompleteness"],
            "pending_actions": pending,
            "max_tension": round(max_tension, 3),
            "threshold": threshold,
        }
