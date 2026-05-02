from brain.base_mechanism import BrainMechanism
import sqlite3, json, time, random

class RecursiveSelfModelWithPipelineRuleEcho(BrainMechanism):
    """
    Cross-layer mechanism combining recursive self-model with pipeline rule echo.
    Tracks recursive_rule_echo_events.
    process() combines self-model recursion with pipeline rule patterns.
    """
    def __init__(self, db_path=None):
        super().__init__(name="RecursiveSelfModelWithPipelineRuleEcho", human_analog="RecursiveSelfModelWithPipelineRuleEcho", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.self_model = 0.5
        self.rule_echo = 0.0
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS recursive_rule_echo_events (id INTEGER PRIMARY KEY, self_model REAL, rule_echo REAL, combined REAL, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        anomaly = pirp_context.get("prsl_signal", {}).get("anomaly_score", 0.5)
        pressure = pirp_context.get("self_model_pressure", 0.5)
        rule_mut = pirp_context.get("rule_mutation", 0.5)
        self.self_model = self.self_model * 0.85 + anomaly * 0.15
        self.rule_echo = pressure * rule_mut
        combined = self.self_model * self.rule_echo
        self._save()
        pirp_context["recursive_rule_echo"] = combined
        pirp_context["self_model_recursive"] = self.self_model
        return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO recursive_rule_echo_events (self_model,rule_echo,combined,ts) VALUES (?,?,?,?)",
                  (self.self_model, self.rule_echo, self.self_model * self.rule_echo, time.time()))
        c.commit(); c.close()
    def get_state(self): return {"self_model": self.self_model, "rule_echo": self.rule_echo}

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

