from brain.base_mechanism import BrainMechanism
import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS risk_echo_in_inertia(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,inertia REAL,echo_strength REAL,risk_input REAL)""")
        c.commit()
class RiskEchoInInertia(BrainMechanism):
    def __init__(self):
        super().__init__(name="RiskEchoInInertia", human_analog="RiskEchoInInertia", layer="integration")
        _init();self.inertia=0.3;self.echo_strength=0.0;self.decay_rate=0.05
    def process(self,pirp_context:dict)->dict:
        risk_input=pirp_context.get("survival_trigger",0.0)
        if isinstance(risk_input,bool):risk_input=0.8 if risk_input else 0.0
        if risk_input>0.5:self.echo_strength=min(1.0,self.echo_strength+risk_input*0.4)
        self.echo_strength=max(0.0,self.echo_strength-self.decay_rate)
        self.inertia=min(0.95,0.2+self.echo_strength*0.7)
        self._save(risk_input)
        pirp_context["risk_echo_inertia"]=self.inertia
        pirp_context["initiation_weight"]=max(0.1,1.0-self.inertia)
        return pirp_context
    def get_state(self)->dict:
        return{"inertia":self.inertia,"echo_strength":round(self.echo_strength,4)}
    def _save(self,risk_input):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO risk_echo_in_inertia(timestamp,inertia,echo_strength,risk_input) VALUES(?,?,?,?)",(time.time(),self.inertia,self.echo_strength,risk_input));c.commit()
        except:pass

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

