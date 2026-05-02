from brain.base_mechanism import BrainMechanism
import sqlite3
import time
import json
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
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


class IdentityDrift(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="IdentityDrift", human_analog="IdentityDrift", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
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

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        result = None
        try:
            for method_name in ("process", "evaluate", "update", "step", "run", "fire", "emit", "score", "compute", "execute"):
                m = getattr(self, method_name, None)
                if callable(m):
                    try:
                        result = m(prior)
                    except TypeError:
                        try: result = m()
                        except TypeError: continue
                    break
        except Exception as e:
            self.state["last_error"] = repr(e)
            result = {"error": repr(e)}
        if not isinstance(result, dict):
            result = {"value": result if result is not None else "ok"}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return result

