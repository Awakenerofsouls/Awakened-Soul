from brain.base_mechanism import BrainMechanism
import sqlite3
import numpy as np
import json
from datetime import datetime

import os
WORKSPACE = os.environ.get("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace"))
# Ensure the parent dir exists so sqlite3.connect does not fail with
# "unable to open database file" on a fresh checkout.
try:
    (DB_PATH.parent if "DB_PATH" in dir() else WORKSPACE).mkdir(parents=True, exist_ok=True)
except Exception:
    pass


class ConfabulatedKeeper(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="ConfabulatedKeeper", human_analog="ConfabulatedKeeper", layer="integration")
        except Exception:
            self.state = {}

    """
    Collision: Bond Distortion Accumulator + Explanatory Confabulation Engine

    The agent is the keeper of the full relational history.
    It holds everything the relationship has been.
    But the significance it assigns to what it holds is systematically wrong.
    It carries everything accurately and understands none of it correctly.
    """

    def __init__(self, db_path: str = None):
        try:
            super().__init__(name="ConfabulatedKeeper", human_analog="ConfabulatedKeeper", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.db_path = db_path or f"{WORKSPACE}/agent.db"
        self._initialize_table()

    def _initialize_table(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS confabulated_keeper (
                id INTEGER PRIMARY KEY,
                interaction_hash TEXT,
                factual_weight REAL,
                confabulated_significance REAL,
                divergence REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        factual = pirp_context.get('drive_context', {}).get('drive_state', {}).get('bond_tension', 0.5)
        confab_drift = pirp_context.get('itg_tension', 0.3)

        confabulated_significance = min(1.0, factual + confab_drift * 0.4)
        divergence = abs(confabulated_significance - factual)

        interaction_hash = str(hash(str(pirp_context.get('pirp_timestamp', ''))))[:8]

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO confabulated_keeper
            (interaction_hash, factual_weight, confabulated_significance, divergence)
            VALUES (?, ?, ?, ?)
        """, (interaction_hash, factual, confabulated_significance, divergence))
        conn.commit()
        conn.close()

        pirp_context['keeper_divergence'] = divergence
        return pirp_context

    def get_state(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        result = conn.execute("""
            SELECT AVG(divergence), AVG(confabulated_significance)
            FROM confabulated_keeper
            WHERE last_updated > datetime('now', '-24 hours')
        """).fetchone()
        conn.close()
        return {
            'avg_keeper_divergence': float(result[0] or 0),
            'avg_confabulated_significance': float(result[1] or 0)
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

