import random
import sqlite3
import time
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova")))) / "nova.db"

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


class CuriosityEngine:
    BASE_FIRE_RATE = 0.25

    def __init__(self):
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
