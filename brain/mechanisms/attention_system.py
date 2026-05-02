# brain/systems/attention_system.py
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
            CREATE TABLE IF NOT EXISTS attention_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                top_signal_type TEXT,
                top_priority REAL,
                signal_count INTEGER
            )
        """)
        conn.commit()


class AttentionSystem(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="AttentionSystem", human_analog="AttentionSystem", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        _init_table()

    def process(self, pirp_context: dict) -> dict:
        signals = pirp_context.get("signals", [])
        weighted = self.weight(signals)
        top = weighted[0] if weighted else {}
        self._write_state(top, len(weighted))
        return {"weighted_signals": weighted, "top_signal": top}

    def weight(self, signals: list) -> list:
        scored = []
        for s in signals:
            priority = 0.0
            priority += float(s.get("intensity", 0)) * 1.0
            priority += float(s.get("novelty", 0)) * 0.5
            priority += float(s.get("urgency", 0)) * 1.5
            priority += float(s.get("goal_relevance", 0)) * 1.2
            priority += float(s.get("emotional_weight", 0)) * 0.8
            s = dict(s)
            s["priority"] = round(priority, 4)
            scored.append(s)
        return sorted(scored, key=lambda x: x.get("priority", 0), reverse=True)

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    "SELECT top_signal_type, top_priority, signal_count FROM attention_state ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if row:
                    return {"top_signal_type": row[0], "top_priority": row[1], "signal_count": row[2]}
        except Exception:
            pass
        return {}

    def _write_state(self, top: dict, count: int):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO attention_state (timestamp, top_signal_type, top_priority, signal_count) VALUES (?,?,?,?)",
                    (time.time(), top.get("type"), top.get("priority"), count)
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

