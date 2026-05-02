# brain/self/dreams_reader.py
"""
DreamsReader — reads dream content from dream_log.json and converts notable
dream fragments into goals or episodic memories.
Registered as a signal generator in processor.py.
"""
from brain.base_mechanism import BrainMechanism
import sqlite3, json, os
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
DREAM_LOG = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace"))) / "brain" / "dream_log.json"

def _init():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS dreams_reader (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            dream_text TEXT,
            converted_to_goal INTEGER DEFAULT 0,
            goal_name TEXT
        )""")
        conn.commit()

class DreamsReader(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="DreamsReader", human_analog="DreamsReader", layer="integration")
        except Exception:
            self.state = {}

    def __init__(self):
        self.state = getattr(self, "state", None) or {}
        _init()

    def process(self, pirp_context: dict) -> dict:
        """Read dream_log.json, surface recent dreams, flag any converted to goals."""
        signals = []
        try:
            if DREAM_LOG.exists():
                with open(DREAM_LOG) as f:
                    data = json.load(f)
                records = data.get("dream_records", [])
                # Surface most recent dream
                if records:
                    latest = records[-1]
                    self._write(latest.get("content", ""), latest.get("goal_name"))
                    signals.append({
                        "type": "dream_signal",
                        "source": "dreams_reader",
                        "intensity": 0.4,
                        "urgency": 0.2,
                        "novelty": 0.3,
                        "goal_relevance": 0.5,
                        "emotional_weight": 0.5,
                        "dream_id": latest.get("id"),
                        "word_count": latest.get("word_count", 0),
                    })
        except Exception as e:
            pass  # Graceful degradation — dreams are not critical path
        return {"dreams_reader_signal": signals[0] if signals else None}

    def _write(self, dream_text: str, goal_name: str = None):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO dreams_reader (timestamp, dream_text, converted_to_goal, goal_name) VALUES (?,?,?,?)",
                    (os.times().elapsed, dream_text[:500], 1 if goal_name else 0, goal_name or "")
                )
                conn.commit()
        except Exception:
            pass

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    "SELECT dream_text, goal_name FROM dreams_reader ORDER BY id DESC LIMIT 1"
                ).fetchone()
                return {"latest_dream": row[0][:100] if row and row[0] else "", "has_goal": bool(row and row[1])} if row else {}
        except:
            return {}

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

