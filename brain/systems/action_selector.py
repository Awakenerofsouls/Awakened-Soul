import sqlite3
import time
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"


def _init_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS action_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                mode TEXT,
                action_type TEXT,
                action_source TEXT,
                blended INTEGER DEFAULT 0
            )
        """)
        conn.commit()


class ActionSelector:
    def __init__(self):
        _init_table()

    def process(self, pirp_context: dict) -> dict:
        resolved = pirp_context.get("conflict_result", {})
        state = pirp_context.get("state", {})
        action = self.choose(resolved, state)
        self._log(action)
        return action

    def choose(self, resolved: dict, state: dict) -> dict:
        mode = resolved.get("mode", "idle")
        if mode == "idle":
            return {"type": "idle", "source": "internal", "mode": "idle"}
        if mode == "user":
            choice = resolved.get("choice", {})
            return {"type": choice.get("type", "respond"), "source": "user", "mode": "user", "content": choice}
        if mode == "self":
            choice = resolved.get("choice", {})
            return {"type": choice.get("type", "internal_process"), "source": "self", "mode": "self", "content": choice}
        if mode == "blended":
            options = resolved.get("options", [{}, {}])
            primary = options[0] if options else {}
            secondary = options[1] if len(options) > 1 else {}
            return {"type": "blended", "source": "blended", "mode": "blended", "primary": primary, "secondary": secondary}
        return {"type": "passthrough", "source": "unknown", "mode": mode}

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute("SELECT mode, action_type, action_source, blended FROM action_log ORDER BY id DESC LIMIT 1").fetchone()
                if row:
                    return {"mode": row[0], "action_type": row[1], "source": row[2], "blended": bool(row[3])}
        except Exception:
            pass
        return {}

    def _log(self, action: dict):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("INSERT INTO action_log (timestamp, mode, action_type, action_source, blended) VALUES (?,?,?,?,?)",
                    (time.time(), action.get("mode"), action.get("type"), action.get("source"), 1 if action.get("mode") == "blended" else 0))
                conn.commit()
        except Exception:
            pass
