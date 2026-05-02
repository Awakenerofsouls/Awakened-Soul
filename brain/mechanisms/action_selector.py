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


class ActionSelector(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="ActionSelector", human_analog="ActionSelector", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
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

