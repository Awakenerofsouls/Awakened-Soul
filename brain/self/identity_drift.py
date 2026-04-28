import sqlite3
import time
import json
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
STATE_PATH = Path("state/agent_state.json")

DEFAULT_TRAITS = {
    "curiosity": 0.6,
    "discipline": 0.5,
    "independence": 0.5,
    "warmth": 0.7,
    "directness": 0.6
}

DRIFT_RATE = 0.005
CLAMP_MIN = 0.1
CLAMP_MAX = 0.95


def _init_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS identity_drift_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                trait TEXT,
                old_value REAL,
                new_value REAL,
                delta REAL,
                trigger TEXT
            )
        """)
        conn.commit()


class IdentityDrift:
    def __init__(self):
        _init_table()

    def process(self, pirp_context: dict) -> dict:
        state = pirp_context.get("state", {})
        event = pirp_context.get("event", {})
        return self.update(state, event)

    def update(self, state: dict, event: dict = None) -> dict:
        traits = self._load_traits(state)
        changes = {}
        if event:
            event_type = event.get("type", "")
            source = event.get("source", "")
            if event_type == "curiosity":
                changes["curiosity"] = DRIFT_RATE
            if source == "self" and event.get("mode") == "self":
                changes["independence"] = DRIFT_RATE
            if event_type == "architect_message":
                changes["warmth"] = DRIFT_RATE * 0.5
            if event_type == "conflict" and event.get("resolved") == "self":
                changes["independence"] = DRIFT_RATE
                changes["discipline"] = DRIFT_RATE * 0.5
        for trait in traits:
            if trait not in changes:
                center = DEFAULT_TRAITS.get(trait, 0.5)
                if abs(traits[trait] - center) > 0.05:
                    changes[trait] = (center - traits[trait]) * 0.001
        updated = {}
        for trait, delta in changes.items():
            old_val = traits.get(trait, DEFAULT_TRAITS.get(trait, 0.5))
            new_val = max(CLAMP_MIN, min(CLAMP_MAX, old_val + delta))
            traits[trait] = new_val
            updated[trait] = {"old": old_val, "new": new_val, "delta": delta}
            self._log(trait, old_val, new_val, delta, event.get("type", "tick") if event else "tick")
        self._save_traits(state, traits)
        return {"traits": traits, "changes": updated}

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute(
                    "SELECT trait, new_value FROM identity_drift_log WHERE id IN (SELECT MAX(id) FROM identity_drift_log GROUP BY trait)"
                ).fetchall()
                return {r[0]: r[1] for r in rows}
        except Exception:
            pass
        return {}

    def _load_traits(self, state: dict) -> dict:
        return dict(state.get("identity", {}).get("traits", DEFAULT_TRAITS))

    def _save_traits(self, state: dict, traits: dict):
        try:
            if "identity" not in state:
                state["identity"] = {}
            state["identity"]["traits"] = traits
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(state, indent=2, default=str))
        except Exception:
            pass

    def _log(self, trait: str, old: float, new: float, delta: float, trigger: str):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO identity_drift_log (timestamp, trait, old_value, new_value, delta, trigger) VALUES (?,?,?,?,?,?)",
                    (time.time(), trait, old, new, delta, trigger))
                conn.commit()
        except Exception:
            pass
