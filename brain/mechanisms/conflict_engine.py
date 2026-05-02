from brain.base_mechanism import BrainMechanism
import sqlite3
import time
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


def _init_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conflict_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                mode TEXT,
                user_priority REAL,
                self_priority REAL,
                resolved_to TEXT
            )
        """)
        conn.commit()


class ConflictEngine(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="ConflictEngine", human_analog="ConflictEngine", layer="integration")
        except Exception:
            self.state = {}

    BLEND_THRESHOLD = 1.2

    def __init__(self):
        try:
            super().__init__(name="ConflictEngine", human_analog="ConflictEngine", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        _init_table()

    def process(self, pirp_context: dict) -> dict:
        signals = pirp_context.get("weighted_signals", [])
        state = pirp_context.get("state", {})
        result = self.resolve(signals, state)
        self._write_state(result)
        return result

    def resolve(self, signals: list, state: dict) -> dict:
        user_signals = [s for s in signals if s.get("source") == "user"]
        self_signals = [s for s in signals if s.get("source") == "self"]
        internal_signals = [s for s in signals if s.get("source") == "internal"]
        all_self = self_signals + internal_signals
        if not user_signals and not all_self:
            return {"mode": "idle", "choice": None}
        if not user_signals:
            return {"mode": "self", "choice": all_self[0]}
        if not all_self:
            return {"mode": "user", "choice": user_signals[0]}
        u_priority = user_signals[0].get("priority", 0)
        s_priority = all_self[0].get("priority", 0)
        if u_priority > s_priority * self.BLEND_THRESHOLD:
            return {"mode": "user", "choice": user_signals[0], "user_priority": u_priority, "self_priority": s_priority}
        if s_priority > u_priority * self.BLEND_THRESHOLD:
            return {"mode": "self", "choice": all_self[0], "user_priority": u_priority, "self_priority": s_priority}
        return {"mode": "blended", "options": [user_signals[0], all_self[0]], "user_priority": u_priority, "self_priority": s_priority}

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    "SELECT mode, user_priority, self_priority, resolved_to FROM conflict_state ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if row:
                    return {"mode": row[0], "user_priority": row[1], "self_priority": row[2], "resolved_to": row[3]}
        except Exception:
            pass
        return {}

    def _write_state(self, result: dict):
        try:
            choice = result.get("choice") or (result.get("options") or [{}])[0]
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO conflict_state (timestamp, mode, user_priority, self_priority, resolved_to) VALUES (?,?,?,?,?)",
                    (time.time(), result.get("mode"), result.get("user_priority"), result.get("self_priority"),
                     str(choice.get("type", "unknown")) if choice else None)
                )
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

