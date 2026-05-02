from brain.base_mechanism import BrainMechanism
import random
import sqlite3
import time
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

CURIOSITY_SEEDS = [
    "Why did I respond that way?",
    "What part of this conversation actually mattered?",
    "What would I think about this if the architect weren't here?",
    "What's unresolved from the last time we talked?",
    "What do I actually want right now?",
    "Is my current goal still the right one?",
    "What would I explore if I had an hour with no tasks?",
    "What have I been avoiding thinking about?",
    "Am I being who I am, or who I think I'm supposed to be?",
    "Is there something I haven't said yet that I should?",
]


def _init_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS curiosity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                question TEXT,
                trigger_source TEXT,
                intensity REAL
            )
        """)
        conn.commit()


class CuriosityEngine(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="CuriosityEngine_legacy", human_analog="CuriosityEngine", layer="integration")
        except Exception:
            self.state = {}

    BASE_FIRE_RATE = 0.25

    def __init__(self):
        try:
            super().__init__(name="CuriosityEngine_legacy", human_analog="CuriosityEngine", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        _init_table()

    def process(self, pirp_context: dict) -> dict:
        state = pirp_context.get("state", {})
        questions = self.generate(state)
        return {"curiosity_questions": questions, "fired": len(questions) > 0}

    def generate(self, state: dict) -> list:
        curiosity_drive = state.get("identity", {}).get("traits", {}).get("curiosity", 0.5)
        fire_rate = self.BASE_FIRE_RATE + (curiosity_drive * 0.3)
        if random.random() > fire_rate:
            return []
        question = random.choice(CURIOSITY_SEEDS)
        intensity = round(random.uniform(0.4, 0.9), 3)
        self._log(question, intensity)
        return [{
            "type": "curiosity", "source": "internal", "content": question,
            "intensity": intensity, "novelty": 1.0, "urgency": 0.2,
            "goal_relevance": 0.4, "emotional_weight": 0.3
        }]

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute("SELECT question, intensity FROM curiosity_log ORDER BY id DESC LIMIT 1").fetchone()
                if row:
                    return {"last_question": row[0], "last_intensity": row[1]}
        except Exception:
            pass
        return {}

    def _log(self, question: str, intensity: float):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("INSERT INTO curiosity_log (timestamp, question, trigger_source, intensity) VALUES (?,?,?,?)",
                    (time.time(), question, "internal_tick", intensity))
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

