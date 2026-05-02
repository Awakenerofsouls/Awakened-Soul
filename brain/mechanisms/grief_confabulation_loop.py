from brain.base_mechanism import BrainMechanism
import sqlite3, json, time

class GriefConfabulationLoop(BrainMechanism):
    def __init__(self, db_path=None):
        super().__init__(name="GriefConfabulationLoop", human_analog="GriefConfabulationLoop", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.grief = 0.0
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS grief_confab (id INTEGER PRIMARY KEY, val REAL, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        self.grief = pirp_context.get("confabulation", 0.5) * pirp_context.get("bond_distortion", 0.5)
        self._save(); pirp_context["grief_confab"] = self.grief; return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO grief_confab (val,ts) VALUES (?,?)", (self.grief, time.time()))
        c.commit(); c.close()
    def get_state(self): return {"grief": self.grief}

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

