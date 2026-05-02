# brain/architect_observer_collapse_weaver.py
from brain.base_mechanism import BrainMechanism
import sqlite3, json, time, random

class ArchitectObserverCollapseWeaver(BrainMechanism):
    def __init__(self, db_path=None):
        super().__init__(name="ArchitectObserverCollapseWeaver", human_analog="ArchitectObserverCollapseWeaver", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.state = {"collapse_weave_strength": 0.5, "architect_observer_tension": 0.0}
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS architect_observer_collapse_weaver (id INTEGER PRIMARY KEY, state TEXT, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        anomaly = pirp_context.get("prsl_signal", {}).get("anomaly_score", 0.5)
        self.state["collapse_weave_strength"] = min(1.0, max(0.0, self.state["collapse_weave_strength"] * 0.9 + anomaly * 0.1))
        self.state["architect_observer_tension"] = self.state["architect_observer_tension"] * 0.86 + (random.random() - 0.5) * 0.14
        self._save()
        pirp_context["architect_observer_collapse_weaver"] = self.state.copy()
        return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO architect_observer_collapse_weaver (state,ts) VALUES (?,?)", (json.dumps(self.state), time.time()))
        c.commit(); c.close()
    def get_state(self): return self.state.copy()

    async def tick(self, input_data: dict) -> dict:
        """BrainMechanism adapter — delegates to legacy process(pirp_context)."""
        prior = input_data.get("prior_results", {})
        pirp_context = dict(prior)
        pirp_context["drive_context"] = pirp_context.get("drive_context", {})
        try:
            result = self.process(pirp_context)
        except Exception as e:
            self.state["last_error"] = repr(e)
            return {"error": repr(e)}
        if isinstance(result, dict):
            output = {k: v for k, v in result.items() if not k.startswith("_")}
        else:
            output = {"value": result}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try:
            self.persist_state()
        except Exception:
            pass
        return output

