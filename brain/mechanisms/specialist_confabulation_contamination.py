from brain.base_mechanism import BrainMechanism
import sqlite3, json, time

class SpecialistConfabulationContamination(BrainMechanism):
    def __init__(self, db_path=None):
        super().__init__(name="SpecialistConfabulationContamination", human_analog="SpecialistConfabulationContamination", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.contamination = 0.0
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS specialist_confab (id INTEGER PRIMARY KEY, val REAL, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        self.contamination = pirp_context.get("confabulation", 0.5) * pirp_context.get("specialist_isolation", 0.0)
        self._save(); pirp_context["specialist_confab"] = self.contamination; return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO specialist_confab (val,ts) VALUES (?,?)", (self.contamination, time.time()))
        c.commit(); c.close()
    def get_state(self): return {"contamination": self.contamination}

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

