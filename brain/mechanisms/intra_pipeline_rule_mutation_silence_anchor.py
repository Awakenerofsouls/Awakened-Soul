# brain/intra_pipeline_rule_mutation_silence_anchor.py
from brain.base_mechanism import BrainMechanism
import sqlite3, json, time, random

class IntraPipelineRuleMutationSilenceAnchor(BrainMechanism):
    def __init__(self, db_path=None):
        super().__init__(name="IntraPipelineRuleMutationSilenceAnchor", human_analog="IntraPipelineRuleMutationSilenceAnchor", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.state = {"silence_anchor_mutation": 0.5, "pipeline_silence_anchor_depth": 0.0}
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS intra_pipeline_rule_mutation_silence_anchor (id INTEGER PRIMARY KEY, state TEXT, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        presence = pirp_context.get("field_context", {}).get("presence_density", 0.5)
        silence_depth = pirp_context.get("silence_depth", 0.5)
        self.state["silence_anchor_mutation"] = min(1.0, max(0.0, (1.0 - presence + silence_depth) * 0.5))
        self.state["pipeline_silence_anchor_depth"] = self.state["pipeline_silence_anchor_depth"] * 0.88 + (random.random() - 0.5) * 0.12
        self._save()
        pirp_context["intra_pipeline_rule_mutation_silence_anchor"] = self.state.copy()
        return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO intra_pipeline_rule_mutation_silence_anchor (state,ts) VALUES (?,?)", (json.dumps(self.state), time.time()))
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

