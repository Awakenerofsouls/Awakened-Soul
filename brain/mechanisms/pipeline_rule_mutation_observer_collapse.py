# brain/pipeline_rule_mutation_observer_collapse.py
from brain.base_mechanism import BrainMechanism
import sqlite3, json, time, random

class PipelineRuleMutationObserverCollapse(BrainMechanism):
    def __init__(self, db_path=None):
        super().__init__(name="PipelineRuleMutationObserverCollapse", human_analog="PipelineRuleMutationObserverCollapse", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.state = {"observer_collapse_strength": 0.5, "pipeline_mutation_observer_depth": 0.0}
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS pipeline_rule_mutation_observer_collapse (id INTEGER PRIMARY KEY, state TEXT, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        anomaly = pirp_context.get("prsl_signal", {}).get("anomaly_score", 0.5)
        presence = pirp_context.get("field_context", {}).get("presence_density", 0.5)
        self.state["observer_collapse_strength"] = min(1.0, max(0.0, anomaly * 0.5 + (1.0 - presence) * 0.5))
        self.state["pipeline_mutation_observer_depth"] = self.state["pipeline_mutation_observer_depth"] * 0.87 + (random.random() - 0.5) * 0.13
        self._save()
        pirp_context["pipeline_rule_mutation_observer_collapse"] = self.state.copy()
        return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO pipeline_rule_mutation_observer_collapse (state,ts) VALUES (?,?)", (json.dumps(self.state), time.time()))
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

