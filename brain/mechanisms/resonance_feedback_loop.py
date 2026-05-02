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
        c.execute("""CREATE TABLE IF NOT EXISTS resonance_feedback_loop(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,resonance REAL,input_valence REAL,internal_valence REAL,delta REAL)""")
        c.commit()
class ResonanceFeedbackLoop(BrainMechanism):
    def __init__(self):
        super().__init__(name="ResonanceFeedbackLoop", human_analog="ResonanceFeedbackLoop", layer="integration")
        _init();self.resonance=0.5;self.feedback_history=[]
    def process(self,pirp_context:dict)->dict:
        input_valence=pirp_context.get("valence",0.0)
        internal_valence=pirp_context.get("state",{}).get("emotion",{}).get("valence",0.0)
        delta=abs(input_valence-internal_valence)
        self.resonance=max(0.0,min(1.0,1.0-delta))
        self.feedback_history.append(self.resonance)
        if len(self.feedback_history)>20:self.feedback_history=self.feedback_history[-20:]
        self._save(input_valence,internal_valence,delta)
        pirp_context["resonance_feedback"]=self.resonance
        pirp_context["resonance_amplification"]=self.resonance*1.4
        return pirp_context
    def get_state(self)->dict:
        avg=sum(self.feedback_history)/len(self.feedback_history) if self.feedback_history else 0.5
        return{"resonance":self.resonance,"avg_resonance":round(avg,4)}
    def _save(self,input_v,internal_v,delta):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO resonance_feedback_loop(timestamp,resonance,input_valence,internal_valence,delta) VALUES(?,?,?,?,?)",(time.time(),self.resonance,input_v,internal_v,delta));c.commit()
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

