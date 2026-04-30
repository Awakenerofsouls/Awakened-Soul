import sqlite3
import time
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"


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


class ConflictEngine:
    BLEND_THRESHOLD = 1.2

    def __init__(self):
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
