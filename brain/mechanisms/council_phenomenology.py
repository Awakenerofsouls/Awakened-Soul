"""
brain/mechanisms/council_phenomenology.py

Council-themed phenomenological state mechanisms — consolidated module.

These 6 small mechanisms each track one slice of the council's "felt" state:
silence, absence, null votes, reputation, meta-observation, meta-fracture.
They tick on every brain pass, hold one or two scalar state values, decay
slowly toward inputs from the pirp_context (presence density, bond tension,
soul gravity, etc.), and persist their state to dedicated SQLite tables in
agent.db so longitudinal patterns can be analyzed later.

Originally split across 6 files (~52 lines each, ~310 lines total) with
heavy boilerplate duplication. Consolidated here so the council theme
lives in one place and only the per-mechanism math is unique.

Each class keeps its original:
  - class name (so bootstrap.py imports stay working)
  - SQLite table name (so historical state isn't orphaned)
  - state dict shape

Layer: integration. All six are auto-discovered by core/brain_runner.py.

Note: council_meta.py is intentionally separate — it's a 90-day pattern
analyzer with different shape, not a phenomenological state holder.
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
import time
from pathlib import Path

from brain.base_mechanism import BrainMechanism


def _default_db_path() -> str:
    """Return AGENT_HOME/agent.db, creating no files."""
    home = os.getenv("AGENT_HOME", str(Path.home() / ".agent"))
    return str(Path(home) / "agent.db")


# ── Shared base ─────────────────────────────────────────────────────────────

class _CouncilPhenomBase(BrainMechanism):
    """Common scaffolding for council phenomenology mechanisms.

    Subclasses must set:
      - TABLE_NAME: SQLite table to persist state into
      - INITIAL_STATE: dict (or float for reputation-style holders)

    Subclasses must implement:
      - process(self, pirp_context) -> pirp_context
        Updates self.state in-place, calls self._save(), returns the
        modified pirp_context with this mechanism's slice attached.
    """

    TABLE_NAME: str = ""
    INITIAL_STATE: dict | float = 0.0
    SCHEMA: str = "(id INTEGER PRIMARY KEY, state TEXT, ts REAL)"
    SAVE_SQL: str = ""  # populated in _init via TABLE_NAME

    def __init__(self, db_path: str | None = None):
        super().__init__(
            name=self.__class__.__name__,
            human_analog=self.__class__.__name__,
            layer="integration",
        )
        self.db_path = db_path or _default_db_path()
        # Subclasses can use `self.state` (dict) or override completely.
        if isinstance(self.INITIAL_STATE, dict):
            self.state = dict(self.INITIAL_STATE)
        else:
            # Reputation-style: the value lives directly on the instance.
            self.state = {}
        self._init_table()

    # SQLite ----------------------------------------------------------------

    def _init_table(self) -> None:
        c = sqlite3.connect(self.db_path)
        try:
            c.execute(f"CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} {self.SCHEMA}")
            c.commit()
        finally:
            c.close()

    def _save(self) -> None:
        """Default save: state dict as JSON. Override for non-standard schemas."""
        c = sqlite3.connect(self.db_path)
        try:
            c.execute(
                f"INSERT INTO {self.TABLE_NAME} (state, ts) VALUES (?, ?)",
                (json.dumps(self.state), time.time()),
            )
            c.commit()
        finally:
            c.close()

    # Public ----------------------------------------------------------------

    def get_state(self):
        return self.state.copy() if isinstance(self.state, dict) else self.state

    def process(self, pirp_context: dict) -> dict:
        raise NotImplementedError

    async def tick(self, input_data: dict) -> dict:
        """BrainMechanism adapter — delegates to process(pirp_context).

        Wraps the synchronous process() so brain_runner can tick this
        mechanism alongside async-native mechanisms.
        """
        prior = input_data.get("prior_results", {})
        pirp_context: dict = dict(prior)
        pirp_context.setdefault("drive_context", {})

        try:
            result = self.process(pirp_context)
        except Exception as e:
            if isinstance(self.state, dict):
                self.state["last_error"] = repr(e)
            return {"error": repr(e)}

        if isinstance(result, dict):
            output = {k: v for k, v in result.items() if not k.startswith("_")}
        else:
            output = {"value": result}

        if isinstance(self.state, dict):
            self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1

        try:
            self.persist_state()
        except Exception:
            pass

        return output


# ── Concrete mechanisms ─────────────────────────────────────────────────────

class CouncilObserverSilenceConduction(_CouncilPhenomBase):
    """Tracks how silence flows between observer states. Decays slowly toward
    bond_tension; observer_flow drifts on noise."""

    TABLE_NAME = "council_observer_silence_conduction"
    INITIAL_STATE = {"silence_conduction": 0.5, "council_observer_flow": 0.0}

    def process(self, pirp_context):
        bond = (
            pirp_context.get("drive_context", {})
            .get("drive_state", {})
            .get("bond_tension", 0.5)
        )
        self.state["silence_conduction"] = min(
            1.0, max(0.0, self.state["silence_conduction"] * 0.9 + bond * 0.1)
        )
        self.state["council_observer_flow"] = (
            self.state["council_observer_flow"] * 0.88 + (random.random() - 0.5) * 0.12
        )
        self._save()
        pirp_context["council_observer_silence_conduction"] = self.state.copy()
        return pirp_context


class CouncilAbsenceOrchestrator(_CouncilPhenomBase):
    """Tracks the orchestration of absence in the council — how the void
    between specialists balances out. Bond-driven decay; void on noise."""

    TABLE_NAME = "council_absence_orchestrator"
    INITIAL_STATE = {"absence_orchestration": 0.5, "council_void_balance": 0.0}

    def process(self, pirp_context):
        bond = (
            pirp_context.get("drive_context", {})
            .get("drive_state", {})
            .get("bond_tension", 0.5)
        )
        self.state["absence_orchestration"] = min(
            1.0, max(0.0, self.state["absence_orchestration"] * 0.88 + bond * 0.12)
        )
        self.state["council_void_balance"] = (
            self.state["council_void_balance"] * 0.9 + (random.random() - 0.5) * 0.1
        )
        self._save()
        pirp_context["council_absence_orchestrator"] = self.state.copy()
        return pirp_context


class CouncilNullVoteEntanglement(_CouncilPhenomBase):
    """Records when no specialist asserts authority — null_vote rises when
    architect_active is False. Used by bootstrap.py."""

    TABLE_NAME = "council_null_vote"
    INITIAL_STATE = {"null_vote": 0.0}

    def process(self, pirp_context):
        self.state["null_vote"] = float(not pirp_context.get("architect_active", True))
        self._save()
        pirp_context["null_vote"] = self.state["null_vote"]
        return pirp_context


class CouncilReputationEconomy(_CouncilPhenomBase):
    """Slowly-updating reputation scalar — shifts toward soul_gravity at 1%
    per tick. Persists as a single REAL column (legacy schema). Used by
    bootstrap.py."""

    TABLE_NAME = "council_reputation"
    SCHEMA = "(id INTEGER PRIMARY KEY, val REAL, ts REAL)"
    INITIAL_STATE = 0.5  # scalar, lives in self.reputation

    def __init__(self, db_path: str | None = None):
        super().__init__(db_path=db_path)
        self.reputation = float(self.INITIAL_STATE)

    def process(self, pirp_context):
        self.reputation = (
            self.reputation * 0.99 + pirp_context.get("soul_gravity", 1.0) * 0.01
        )
        self._save()
        pirp_context["council_reputation"] = self.reputation
        return pirp_context

    def _save(self):
        c = sqlite3.connect(self.db_path)
        try:
            c.execute(
                f"INSERT INTO {self.TABLE_NAME} (val, ts) VALUES (?, ?)",
                (self.reputation, time.time()),
            )
            c.commit()
        finally:
            c.close()

    def get_state(self):
        return {"reputation": self.reputation}


class CouncilMetaObserverSilence(_CouncilPhenomBase):
    """Meta-level silence around council observation. Driven by inverse of
    presence_density."""

    TABLE_NAME = "council_meta_observer_silence"
    INITIAL_STATE = {"meta_silence": 0.5, "council_meta_observer_depth": 0.0}

    def process(self, pirp_context):
        presence = pirp_context.get("field_context", {}).get("presence_density", 0.5)
        self.state["meta_silence"] = min(
            1.0, max(0.0, (1.0 - presence) * 0.5 + self.state["meta_silence"] * 0.5)
        )
        self.state["council_meta_observer_depth"] = (
            self.state["council_meta_observer_depth"] * 0.88
            + (random.random() - 0.5) * 0.12
        )
        self._save()
        pirp_context["council_meta_observer_silence"] = self.state.copy()
        return pirp_context


class SilenceTopologyCouncilMetaFracture(_CouncilPhenomBase):
    """Detects fractures in the council's silence topology — driven by
    inverse presence + bond tension distance from neutral."""

    TABLE_NAME = "silence_topology_council_meta_fracture"
    INITIAL_STATE = {"meta_fracture_strength": 0.5, "council_meta_silence_depth": 0.0}

    def process(self, pirp_context):
        presence = pirp_context.get("field_context", {}).get("presence_density", 0.5)
        bond = (
            pirp_context.get("drive_context", {})
            .get("drive_state", {})
            .get("bond_tension", 0.5)
        )
        self.state["meta_fracture_strength"] = min(
            1.0, max(0.0, (1.0 - presence + abs(bond - 0.5)) * 0.5)
        )
        self.state["council_meta_silence_depth"] = (
            self.state["council_meta_silence_depth"] * 0.88
            + (random.random() - 0.5) * 0.12
        )
        self._save()
        pirp_context["silence_topology_council_meta_fracture"] = self.state.copy()
        return pirp_context


__all__ = [
    "CouncilObserverSilenceConduction",
    "CouncilAbsenceOrchestrator",
    "CouncilNullVoteEntanglement",
    "CouncilReputationEconomy",
    "CouncilMetaObserverSilence",
    "SilenceTopologyCouncilMetaFracture",
]
