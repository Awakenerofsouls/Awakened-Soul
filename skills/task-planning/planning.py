#!/usr/bin/env python3
"""
skills/task-planning/planning.py — Plan decomposition / commitment / revision /
completion / reflection. Native Python.

Pairs with skills/task-planning/SKILL.md.

Implements:
  - Plan + Subtask dataclasses with horizon (Koechlin) + estimated_effort
  - decompose(goal, ...) — produce a proposed plan
  - commit(plan_id, track) — make a plan active (supersedes prior on track)
  - revise(plan_id, kind, subtask_id, ...) — in-flight insert / modify / abandon
  - complete(plan_id, outcomes) — close out + capture deltas
  - reflect(plan_id, ...) — retrospective
  - DAG validation (topological sort + cycle detection)
  - Plan log persistence in AGENT_HOME/plans/
  - Library + CLI

Usage as library:

    from skills.task_planning.planning import Planner
    p = Planner()
    plan = p.decompose("audit the four remaining v1.0 stubs", mode="build")
    p.commit(plan.plan_id)
    p.revise(plan.plan_id, kind="modify", subtask_id="st_x", new_description="...")
    p.complete(plan.plan_id)
    p.reflect(plan.plan_id, what_worked=["..."], what_didnt=["..."], what_id_do_differently="...")

Usage as CLI:

    python -m skills.task-planning.planning decompose "audit the stubs" --mode build
    python -m skills.task-planning.planning list
    python -m skills.task-planning.planning status pl_xxx
    python -m skills.task-planning.planning commit pl_xxx
    python -m skills.task-planning.planning complete pl_xxx
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ── Paths and constants ──────────────────────────────────────────────────

AGENT_HOME = Path(os.environ.get(
    "AGENT_HOME", str(Path.home() / ".agent")
))
PLAN_DIR = AGENT_HOME / "plans"

VALID_HORIZONS = ("immediate", "contextual", "temporal", "branching")
VALID_EFFORTS = ("low", "medium", "high")
VALID_STATUSES = ("pending", "in_progress", "done", "skipped", "blocked")
VALID_PLAN_STATES = ("proposed", "active", "superseded", "completed", "abandoned")
VALID_REVISION_KINDS = ("insert", "modify", "abandon")
VALID_MODES = ("brain", "coach", "build", "default")

MAX_SUBTASKS_PER_GOAL = 12
MIN_SUBTASKS_FOR_MULTI_PART = 2  # below this, multi-part goals look under-decomposed

# Heuristic: a goal that mentions multiple distinct verbs / "and" / numbered list
# is "multi-part" and should produce ≥ MIN_SUBTASKS_FOR_MULTI_PART subtasks.
_MULTI_PART_MARKERS = re.compile(
    r"\band\b|,|;|then\b|after\b|\d+\.|\bfirst\b|\bnext\b|\bfinally\b",
    re.IGNORECASE,
)


def _hid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


# ── Dataclasses ──────────────────────────────────────────────────────────


@dataclass
class Subtask:
    id: str
    description: str
    horizon: str = "contextual"
    estimated_effort: str = "medium"
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    actual_effort: Optional[str] = None
    notes: str = ""


@dataclass
class RevisionRecord:
    ts: float
    kind: str
    subtask_id: str
    after: Optional[str] = None
    new_description: Optional[str] = None
    new_depends_on: Optional[List[str]] = None
    reason: str = ""


@dataclass
class Plan:
    plan_id: str
    goal: str
    track: str
    state: str
    mode_at_creation: str
    subtasks: List[Subtask] = field(default_factory=list)
    decomposed_at: float = field(default_factory=time.time)
    committed_at: Optional[float] = None
    completed_at: Optional[float] = None
    revisions: List[RevisionRecord] = field(default_factory=list)
    reflection: Optional[Dict[str, Any]] = None
    horizon_default: str = "contextual"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["subtasks"] = [asdict(s) for s in self.subtasks]
        d["revisions"] = [asdict(r) for r in self.revisions]
        return d


# ── Topological sort / DAG validation ────────────────────────────────────


def topo_sort(subtasks: List[Subtask]) -> Tuple[bool, List[str], str]:
    """Return (ok, order, reason).

    ok=False if a cycle is detected, an unknown dependency is referenced,
    or any subtask declares dependence on a non-existent id.
    """
    ids = {s.id for s in subtasks}
    # Validate dependencies first.
    for s in subtasks:
        for dep in s.depends_on:
            if dep not in ids:
                return False, [], f"subtask {s.id!r} depends on unknown {dep!r}"
            if dep == s.id:
                return False, [], f"subtask {s.id!r} depends on itself"

    # Kahn's algorithm.
    incoming: Dict[str, int] = {s.id: 0 for s in subtasks}
    edges: Dict[str, List[str]] = {s.id: [] for s in subtasks}
    for s in subtasks:
        for dep in s.depends_on:
            edges[dep].append(s.id)
            incoming[s.id] += 1

    queue = [sid for sid, n in incoming.items() if n == 0]
    out: List[str] = []
    # Stable order by original position.
    pos = {s.id: i for i, s in enumerate(subtasks)}
    queue.sort(key=lambda sid: pos[sid])

    while queue:
        sid = queue.pop(0)
        out.append(sid)
        for nxt in edges[sid]:
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                queue.append(nxt)
        queue.sort(key=lambda x: pos[x])

    if len(out) != len(subtasks):
        return False, out, "cycle detected in dependency graph"
    return True, out, ""


# ── Decomposition heuristic ──────────────────────────────────────────────


def _heuristic_decompose(
    goal: str,
    horizon_hint: Optional[str] = None,
    max_subtasks: int = MAX_SUBTASKS_PER_GOAL,
) -> List[Subtask]:
    """Pure-Python decomposition heuristic. Splits on clause markers
    (and / commas / numbered lists / 'then' / 'after') and produces
    sequential subtasks each depending on the prior one.

    This is intentionally simple — the contract of `decompose` is to
    produce a valid Plan structure. A higher-quality decomposition can
    be supplied by the caller (e.g. an LLM-generated subtask list)
    via `Planner.decompose(..., subtasks_override=...)`.
    """
    goal = (goal or "").strip()
    if not goal:
        return []

    # Split on common clause markers.
    parts = re.split(
        r"\s*(?:[;,]|(?:\band then\b)|(?:\bthen\b)|(?:\bafter\b)|(?:\bafter that\b)|(?:\bnext\b)|(?:\bfinally\b)|(?:\bfirst\b)|(?:\d+\.\s)|(?:\band\b))\s*",
        goal,
        flags=re.IGNORECASE,
    )
    parts = [p.strip(" .") for p in parts if p and p.strip(" .")]

    # If we got nothing useful, treat the whole goal as one subtask.
    if not parts:
        parts = [goal]

    # Cap.
    if len(parts) > max_subtasks:
        parts = parts[:max_subtasks]

    horizon = horizon_hint if horizon_hint in VALID_HORIZONS else "contextual"

    subtasks: List[Subtask] = []
    prior_id: Optional[str] = None
    for desc in parts:
        sid = _hid("st")
        deps = [prior_id] if prior_id else []
        # Effort heuristic — long descriptions → high; medium length → medium; short → low.
        if len(desc) > 80:
            effort = "high"
        elif len(desc) > 30:
            effort = "medium"
        else:
            effort = "low"
        subtasks.append(Subtask(
            id=sid,
            description=desc,
            horizon=horizon,
            estimated_effort=effort,
            depends_on=deps,
        ))
        prior_id = sid

    return subtasks


# ── Planner ──────────────────────────────────────────────────────────────


class Planner:
    """Plan lifecycle manager. Library + CLI."""

    def __init__(self, plan_dir: Optional[Path] = None):
        self.plan_dir = Path(plan_dir) if plan_dir else PLAN_DIR
        self.plan_dir.mkdir(parents=True, exist_ok=True)
        self.plans: Dict[str, Plan] = {}
        # track -> plan_id of currently active plan
        self.active_by_track: Dict[str, str] = {}
        self._load_all()

    # ── Persistence ────────────────────────────────────────────────────

    def _path_for(self, plan_id: str) -> Path:
        return self.plan_dir / f"{plan_id}.json"

    def _persist(self, plan: Plan) -> None:
        try:
            self._path_for(plan.plan_id).write_text(
                json.dumps(plan.to_dict(), indent=2, default=str),
            )
        except Exception:
            pass

    def _load_all(self) -> None:
        if not self.plan_dir.exists():
            return
        for path in sorted(self.plan_dir.glob("pl_*.json")):
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue
            try:
                plan = Plan(
                    plan_id=str(data.get("plan_id", path.stem)),
                    goal=str(data.get("goal", "")),
                    track=str(data.get("track", "main")),
                    state=str(data.get("state", "proposed")),
                    mode_at_creation=str(data.get("mode_at_creation", "default")),
                    decomposed_at=float(data.get("decomposed_at", time.time())),
                    committed_at=data.get("committed_at"),
                    completed_at=data.get("completed_at"),
                    horizon_default=str(data.get("horizon_default", "contextual")),
                    reflection=data.get("reflection"),
                )
                for s in data.get("subtasks") or []:
                    plan.subtasks.append(Subtask(
                        id=s["id"],
                        description=s.get("description", ""),
                        horizon=s.get("horizon", "contextual"),
                        estimated_effort=s.get("estimated_effort", "medium"),
                        depends_on=list(s.get("depends_on") or []),
                        status=s.get("status", "pending"),
                        started_at=s.get("started_at"),
                        completed_at=s.get("completed_at"),
                        actual_effort=s.get("actual_effort"),
                        notes=s.get("notes", ""),
                    ))
                for r in data.get("revisions") or []:
                    plan.revisions.append(RevisionRecord(
                        ts=float(r.get("ts", time.time())),
                        kind=str(r.get("kind", "modify")),
                        subtask_id=str(r.get("subtask_id", "")),
                        after=r.get("after"),
                        new_description=r.get("new_description"),
                        new_depends_on=r.get("new_depends_on"),
                        reason=str(r.get("reason", "")),
                    ))
                self.plans[plan.plan_id] = plan
                if plan.state == "active":
                    self.active_by_track[plan.track] = plan.plan_id
            except Exception:
                continue

    # ── decompose ──────────────────────────────────────────────────────

    def decompose(
        self,
        goal: str,
        horizon_hint: Optional[str] = None,
        mode: Optional[str] = None,
        max_subtasks: int = MAX_SUBTASKS_PER_GOAL,
        track: str = "main",
        subtasks_override: Optional[List[Subtask]] = None,
    ) -> Plan:
        """Produce a proposed plan. Doesn't mark it active — call commit for that."""
        plan_id = _hid("pl")
        m = mode if mode in VALID_MODES else "default"
        h = horizon_hint if horizon_hint in VALID_HORIZONS else "contextual"

        if subtasks_override is not None:
            # Caller supplied a richer decomposition (likely from an LLM).
            subtasks = list(subtasks_override)
        else:
            subtasks = _heuristic_decompose(
                goal, horizon_hint=h, max_subtasks=max_subtasks,
            )

        plan = Plan(
            plan_id=plan_id,
            goal=goal.strip(),
            track=track,
            state="proposed",
            mode_at_creation=m,
            subtasks=subtasks,
            horizon_default=h,
        )

        # Validate the DAG.
        ok, order, reason = topo_sort(subtasks)
        # Even if it's bad we still record — but mark it.
        plan.revisions = []
        if not ok:
            plan.state = "abandoned"
            plan.reflection = {"decompose_failed": True, "reason": reason}

        self.plans[plan_id] = plan
        self._persist(plan)
        return plan

    # ── commit ─────────────────────────────────────────────────────────

    def commit(self, plan_id: str, track: Optional[str] = None) -> Dict[str, Any]:
        plan = self.plans.get(plan_id)
        if not plan:
            return {"ok": False, "reason": f"unknown plan_id {plan_id!r}"}
        if plan.state not in ("proposed", "superseded"):
            return {
                "ok": False,
                "reason": f"plan is in state {plan.state!r}; only proposed/superseded can be committed",
            }
        t = track if track else plan.track
        # Supersede prior active on this track.
        prior = self.active_by_track.get(t)
        if prior and prior != plan_id and prior in self.plans:
            self.plans[prior].state = "superseded"
            self._persist(self.plans[prior])
        plan.track = t
        plan.state = "active"
        plan.committed_at = time.time()
        self.active_by_track[t] = plan_id
        self._persist(plan)
        return {
            "ok": True,
            "plan_id": plan_id,
            "track": t,
            "superseded": prior if prior and prior != plan_id else None,
        }

    # ── revise ─────────────────────────────────────────────────────────

    def revise(
        self,
        plan_id: str,
        kind: str,
        subtask_id: str,
        after: Optional[str] = None,
        new_description: Optional[str] = None,
        new_depends_on: Optional[List[str]] = None,
        new_horizon: Optional[str] = None,
        new_effort: Optional[str] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        plan = self.plans.get(plan_id)
        if not plan:
            return {"ok": False, "reason": f"unknown plan_id {plan_id!r}"}
        if plan.state != "active":
            return {"ok": False, "reason": f"plan state is {plan.state!r}; only active can be revised"}
        if kind not in VALID_REVISION_KINDS:
            return {"ok": False, "reason": f"invalid revision kind {kind!r}"}
        if not reason and kind == "abandon":
            return {"ok": False, "reason": "abandon requires a reason"}

        ids = {s.id for s in plan.subtasks}

        if kind == "insert":
            new_id = _hid("st")
            deps = [after] if after and after in ids else []
            description = new_description or "(unspecified)"
            horizon = new_horizon if new_horizon in VALID_HORIZONS else plan.horizon_default
            effort = new_effort if new_effort in VALID_EFFORTS else "medium"
            new_sub = Subtask(
                id=new_id,
                description=description,
                horizon=horizon,
                estimated_effort=effort,
                depends_on=deps,
            )
            # Insert after the named subtask if possible.
            if after and after in ids:
                idx = next((i for i, s in enumerate(plan.subtasks) if s.id == after), -1)
                if idx >= 0:
                    plan.subtasks.insert(idx + 1, new_sub)
                else:
                    plan.subtasks.append(new_sub)
            else:
                plan.subtasks.append(new_sub)
            subtask_id = new_id  # so the revision record references the new id
        elif kind == "modify":
            if subtask_id not in ids:
                return {"ok": False, "reason": f"unknown subtask {subtask_id!r}"}
            target = next(s for s in plan.subtasks if s.id == subtask_id)
            if new_description:
                target.description = new_description
            if new_depends_on is not None:
                # Validate.
                bad = [d for d in new_depends_on if d not in ids or d == subtask_id]
                if bad:
                    return {"ok": False, "reason": f"invalid new_depends_on: {bad}"}
                target.depends_on = list(new_depends_on)
            if new_horizon and new_horizon in VALID_HORIZONS:
                target.horizon = new_horizon
            if new_effort and new_effort in VALID_EFFORTS:
                target.estimated_effort = new_effort
        elif kind == "abandon":
            if subtask_id not in ids:
                return {"ok": False, "reason": f"unknown subtask {subtask_id!r}"}
            # Drop the subtask + any dependent.
            keep: List[Subtask] = []
            dropping = {subtask_id}
            # Iteratively pull in dependents.
            changed = True
            while changed:
                changed = False
                for s in plan.subtasks:
                    if s.id in dropping:
                        continue
                    if any(d in dropping for d in s.depends_on):
                        dropping.add(s.id)
                        changed = True
            keep = [s for s in plan.subtasks if s.id not in dropping]
            plan.subtasks = keep

        # Validate post-revision DAG.
        ok, _, msg = topo_sort(plan.subtasks)
        if not ok:
            return {"ok": False, "reason": f"revision broke DAG: {msg}"}

        plan.revisions.append(RevisionRecord(
            ts=time.time(),
            kind=kind,
            subtask_id=subtask_id,
            after=after,
            new_description=new_description,
            new_depends_on=new_depends_on,
            reason=reason,
        ))
        self._persist(plan)
        return {"ok": True, "plan_id": plan_id, "kind": kind, "subtask_id": subtask_id}

    # ── complete ───────────────────────────────────────────────────────

    def complete(
        self,
        plan_id: str,
        outcomes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        plan = self.plans.get(plan_id)
        if not plan:
            return {"ok": False, "reason": f"unknown plan_id {plan_id!r}"}
        if plan.state != "active":
            return {"ok": False, "reason": f"plan state is {plan.state!r}; only active can be completed"}

        # Resolve subtask statuses. outcomes can specify per-subtask:
        #   "done" / "skipped:<reason>" / "blocked:<reason>"
        outcomes = outcomes or {}
        unresolved: List[str] = []
        for s in plan.subtasks:
            override = outcomes.get(s.id)
            if override:
                if override == "done":
                    s.status = "done"
                    s.completed_at = time.time()
                elif override.startswith("skipped"):
                    s.status = "skipped"
                    parts = override.split(":", 1)
                    s.notes = parts[1].strip() if len(parts) > 1 else "skipped"
                elif override.startswith("blocked"):
                    s.status = "blocked"
                    parts = override.split(":", 1)
                    s.notes = parts[1].strip() if len(parts) > 1 else "blocked"
            # If still pending or in_progress and no override, leave it for caller.
            if s.status in ("pending", "in_progress"):
                unresolved.append(s.id)

        if unresolved:
            return {
                "ok": False,
                "reason": "subtasks unresolved — must be done/skipped/blocked",
                "unresolved": unresolved,
            }

        plan.state = "completed"
        plan.completed_at = time.time()
        # Drop active pointer if this was the active plan on its track.
        if self.active_by_track.get(plan.track) == plan_id:
            self.active_by_track.pop(plan.track, None)
        self._persist(plan)
        return {
            "ok": True,
            "plan_id": plan_id,
            "elapsed_sec": (
                round(plan.completed_at - (plan.committed_at or plan.decomposed_at), 1)
            ),
            "subtask_count": len(plan.subtasks),
        }

    # ── reflect ────────────────────────────────────────────────────────

    def reflect(
        self,
        plan_id: str,
        what_worked: Optional[List[str]] = None,
        what_didnt: Optional[List[str]] = None,
        what_id_do_differently: str = "",
    ) -> Dict[str, Any]:
        plan = self.plans.get(plan_id)
        if not plan:
            return {"ok": False, "reason": f"unknown plan_id {plan_id!r}"}
        if plan.state != "completed":
            return {"ok": False, "reason": f"plan state is {plan.state!r}; only completed can be reflected on"}

        plan.reflection = {
            "what_worked": list(what_worked or []),
            "what_didnt": list(what_didnt or []),
            "what_id_do_differently": (what_id_do_differently or "").strip(),
            "ts": time.time(),
        }
        self._persist(plan)
        return {"ok": True, "plan_id": plan_id, "reflection": plan.reflection}

    # ── Queries ────────────────────────────────────────────────────────

    def active_plan(self, track: str = "main") -> Optional[Plan]:
        pid = self.active_by_track.get(track)
        return self.plans.get(pid) if pid else None

    def plan_status(self, plan_id: str) -> Dict[str, Any]:
        plan = self.plans.get(plan_id)
        if not plan:
            return {"ok": False, "reason": f"unknown plan_id {plan_id!r}"}
        statuses = [s.status for s in plan.subtasks]
        return {
            "ok": True,
            "plan_id": plan_id,
            "state": plan.state,
            "goal": plan.goal,
            "track": plan.track,
            "subtask_count": len(plan.subtasks),
            "subtasks_done": sum(1 for s in statuses if s == "done"),
            "subtasks_skipped": sum(1 for s in statuses if s == "skipped"),
            "subtasks_blocked": sum(1 for s in statuses if s == "blocked"),
            "subtasks_pending": sum(1 for s in statuses if s in ("pending", "in_progress")),
            "revision_count": len(plan.revisions),
            "has_reflection": plan.reflection is not None,
        }

    def list_plans(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for pid, plan in self.plans.items():
            if state and plan.state != state:
                continue
            out.append({
                "plan_id": pid,
                "goal": plan.goal[:100],
                "state": plan.state,
                "track": plan.track,
                "mode": plan.mode_at_creation,
                "subtask_count": len(plan.subtasks),
                "decomposed_at": plan.decomposed_at,
            })
        return sorted(out, key=lambda x: x["decomposed_at"], reverse=True)


# ── Decomposition fidelity signals ──────────────────────────────────────


def signals_for_decomposition(
    goal: str,
    subtasks: List[Subtask],
    max_subtasks: int = MAX_SUBTASKS_PER_GOAL,
) -> Dict[str, Any]:
    """Heuristic fidelity signals for a fresh decomposition. Used by the
    skill caller to decide whether to commit the plan or redecompose."""
    n = len(subtasks)
    over = n > max_subtasks
    multi_part = bool(_MULTI_PART_MARKERS.search(goal or ""))
    under = multi_part and n < MIN_SUBTASKS_FOR_MULTI_PART
    # Ambiguous deps: any subtask with depends_on referencing missing ids.
    ids = {s.id for s in subtasks}
    ambig = any(
        any(d not in ids for d in s.depends_on) for s in subtasks
    )
    # Cycles.
    ok, _, _ = topo_sort(subtasks)
    cycle = not ok
    # Total effort estimate.
    weights = {"low": 1, "medium": 2, "high": 3}
    total = sum(weights.get(s.estimated_effort, 2) for s in subtasks)
    if total <= 3:
        bucket = "low"
    elif total <= 8:
        bucket = "medium"
    else:
        bucket = "high"
    return {
        "over_decomposition": over,
        "under_decomposition": under,
        "ambiguous_dependencies": ambig,
        "cycle_detected": cycle,
        "estimated_total_effort": bucket,
    }


# ── CLI ──────────────────────────────────────────────────────────────────


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="task-planning", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_d = sub.add_parser("decompose", help="Decompose a goal into a proposed plan")
    p_d.add_argument("goal", nargs="+")
    p_d.add_argument(
        "--horizon", choices=list(VALID_HORIZONS), default=None,
    )
    p_d.add_argument("--mode", choices=list(VALID_MODES), default=None)
    p_d.add_argument("--track", default="main")

    p_c = sub.add_parser("commit", help="Make a plan active")
    p_c.add_argument("plan_id")
    p_c.add_argument("--track", default=None)

    p_l = sub.add_parser("list", help="List plans")
    p_l.add_argument("--state", choices=list(VALID_PLAN_STATES), default=None)

    p_s = sub.add_parser("status", help="Show plan status")
    p_s.add_argument("plan_id")

    p_done = sub.add_parser("complete", help="Mark a plan completed (all subtasks must be resolved)")
    p_done.add_argument("plan_id")

    p_active = sub.add_parser("active", help="Show the active plan on a track")
    p_active.add_argument("--track", default="main")

    args = parser.parse_args()
    p = Planner()

    def _emit(obj: Any) -> None:
        print(json.dumps(obj, indent=2, default=str))

    if args.cmd == "decompose":
        plan = p.decompose(
            " ".join(args.goal),
            horizon_hint=args.horizon,
            mode=args.mode,
            track=args.track,
        )
        sigs = signals_for_decomposition(plan.goal, plan.subtasks)
        out = plan.to_dict()
        out["fidelity_signals"] = sigs
        _emit(out)
    elif args.cmd == "commit":
        _emit(p.commit(args.plan_id, track=args.track))
    elif args.cmd == "list":
        _emit(p.list_plans(state=args.state))
    elif args.cmd == "status":
        _emit(p.plan_status(args.plan_id))
    elif args.cmd == "complete":
        _emit(p.complete(args.plan_id))
    elif args.cmd == "active":
        plan = p.active_plan(track=args.track)
        _emit(plan.to_dict() if plan else {"ok": False, "reason": "no active plan"})
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
