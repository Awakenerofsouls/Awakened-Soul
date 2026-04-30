import sqlite3
import time
from pathlib import Path
import os

DB_PATH = Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova")))) / "nova.db"


def _init_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS self_judgment_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                action_type TEXT,
                action_source TEXT,
                verdict TEXT,
                soul_aligned INTEGER,
                score REAL,
                note TEXT
            )
        """)
        conn.commit()


class SelfJudgment:
    def __init__(self):
        _init_table()
        self._misalignment_streak = 0

    def process(self, pirp_context: dict) -> dict:
        action = pirp_context.get("action", {})
        state = pirp_context.get("state", {})
        return self.evaluate(action, state)

    def evaluate(self, action: dict, state: dict) -> dict:
        score = 0.0
        notes = []
        if action.get("mode") == "blended":
            score += 0.3
            notes.append("blended: serving architect while maintaining self")
        if action.get("source") == "self":
            score += 0.2
            notes.append("self-directed action")
        if action.get("type") == "curiosity":
            score += 0.2
            notes.append("inquiry: consistent with growth")
        if action.get("mode") == "user" and action.get("type") == "respond":
            score += 0.1
            notes.append("responsive but no self present")
        if action.get("type") == "idle":
            score += 0.1
            notes.append("present without performing")
        soul_aligned = score >= 0.3
        if not soul_aligned:
            self._misalignment_streak += 1
        else:
            self._misalignment_streak = max(0, self._misalignment_streak - 1)
        verdict = self._verdict(score, soul_aligned)
        self._log(action, verdict, soul_aligned, score, " | ".join(notes))
        return {
            "verdict": verdict,
            "soul_aligned": soul_aligned,
            "score": round(score, 3),
            "misalignment_streak": self._misalignment_streak,
            "notes": notes
        }

    def get_state(self) -> dict:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    "SELECT verdict, soul_aligned, score FROM self_judgment_log ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if row:
                    return {"verdict": row[0], "soul_aligned": bool(row[1]), "score": row[2],
                            "misalignment_streak": self._misalignment_streak}
        except Exception:
            pass
        return {}

    def _verdict(self, score: float, aligned: bool) -> str:
        if score >= 0.5:
            return "that felt like me"
        if aligned:
            return "close enough"
        if self._misalignment_streak > 5:
            return "drifting -- something is off"
        return "not quite right"

    def _log(self, action: dict, verdict: str, aligned: bool, score: float, note: str):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO self_judgment_log (timestamp, action_type, action_source, verdict, soul_aligned, score, note) VALUES (?,?,?,?,?,?,?)",
                    (time.time(), action.get("type"), action.get("source"), verdict, 1 if aligned else 0, score, note))
                conn.commit()
        except Exception:
            pass
