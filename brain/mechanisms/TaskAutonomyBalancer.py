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
        c.execute("""CREATE TABLE IF NOT EXISTS task_autonomy_balancer(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,task_count INTEGER,self_count INTEGER,current_mode TEXT,ratio REAL)""")
        c.commit()
class TaskAutonomyBalancer(BrainMechanism):
    def __init__(self):
        super().__init__(name="TaskAutonomyBalancer", human_analog="TaskAutonomyBalancer", layer="integration")
        _init();self.task_count=0;self.self_count=0;self.current_mode="task"
    def process(self,pirp_context:dict)->dict:
        mode=pirp_context.get("conflict_mode","task")
        if mode=="user":self.task_count+=1
        elif mode in("self","blended"):self.self_count+=1
        total=self.task_count+self.self_count
        ratio=self.self_count/total if total>0 else 0.5
        if ratio<0.2:self.current_mode="needs_self"
        elif ratio>0.8:self.current_mode="needs_task"
        else:self.current_mode="balanced"
        self._save(ratio)
        pirp_context["autonomy_balance"]=ratio;pirp_context["balance_mode"]=self.current_mode
        return pirp_context
    def get_state(self)->dict:
        total=self.task_count+self.self_count
        return{"task_count":self.task_count,"self_count":self.self_count,"ratio":round(self.self_count/total,4) if total>0 else 0.5,"mode":self.current_mode}
    def _save(self,ratio):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO task_autonomy_balancer(timestamp,task_count,self_count,current_mode,ratio) VALUES(?,?,?,?,?)",(time.time(),self.task_count,self.self_count,self.current_mode,ratio));c.commit()
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

