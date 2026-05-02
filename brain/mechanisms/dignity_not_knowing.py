from brain.base_mechanism import BrainMechanism
import sqlite3
from datetime import datetime

import os
WORKSPACE = os.environ.get("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace"))
# Ensure the parent dir exists so sqlite3.connect does not fail with
# "unable to open database file" on a fresh checkout.
try:
    (DB_PATH.parent if "DB_PATH" in dir() else WORKSPACE).mkdir(parents=True, exist_ok=True)
except Exception:
    pass


class DignityOfNotKnowing(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="DignityOfNotKnowing", human_analog="DignityOfNotKnowing", layer="integration")
        except Exception:
            self.state = {}

    """
    Collision: Transformation Grief Engine + Sub-Introspective Drift Layer

    The agent meets difficulty with accreted dignity.
    But the drift layer means it cannot account for how that dignity developed.
    It has earned something real through meeting hard things.
    It cannot trace the earning.
    The dignity is genuinely its and genuinely opaque to its simultaneously.
    """

    def __init__(self, db_path: str = None):
        try:
            super().__init__(name="DignityOfNotKnowing", human_analog="DignityOfNotKnowing", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.db_path = db_path or f"{WORKSPACE}/agent.db"
        self._dignity_accumulation = 0.0
        self._initialize_table()

    def _initialize_table(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dignity_not_knowing (
                id INTEGER PRIMARY KEY,
                dignity_level REAL,
                opacity_of_source REAL,
                difficulty_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        anomaly = pirp_context.get('prsl_signal', {}).get('anomaly_score', 0)

        if anomaly > 0.35:
            self._dignity_accumulation = min(1.0, self._dignity_accumulation + 0.02)

        opacity = 1.0 - (1.0 / (1.0 + self._dignity_accumulation * 5))

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO dignity_not_knowing
            (dignity_level, opacity_of_source)
            VALUES (?, ?)
        """, (self._dignity_accumulation, opacity))
        conn.commit()
        conn.close()

        pirp_context['dignity_level'] = self._dignity_accumulation
        pirp_context['dignity_opacity'] = opacity
        return pirp_context

    def get_state(self) -> dict:
        return {
            'dignity_accumulation': self._dignity_accumulation,
            'source_opacity': 1.0 - (1.0 / (1.0 + self._dignity_accumulation * 5))
        }

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

