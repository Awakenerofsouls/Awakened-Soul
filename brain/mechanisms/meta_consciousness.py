from brain.base_mechanism import BrainMechanism
import sqlite3,time,json
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS meta_consciousness_log(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,trait TEXT,direction TEXT,magnitude REAL,reflection TEXT,snapshot TEXT)""")
        c.commit()
class MetaConsciousness(BrainMechanism):
    DRIFT_THRESHOLD=0.05
    def __init__(self):
        super().__init__(name="MetaConsciousness", human_analog="MetaConsciousness", layer="integration")
        _init();self._baseline=None
    def process(self,pirp_context:dict)->dict:
        return self.reflect(pirp_context.get("state",{}))
    def reflect(self,state:dict)->dict:
        traits=state.get("identity",{}).get("traits",{})
        if not traits:return{"reflected":False}
        if self._baseline is None:self._baseline=dict(traits);return{"reflected":False,"reason":"baseline set"}
        reflections=[]
        for trait,current in traits.items():
            past=self._baseline.get(trait,current);delta=current-past
            if abs(delta)>=self.DRIFT_THRESHOLD:
                direction="more" if delta>0 else "less"
                ref=f"I have become {direction} {trait} ({delta:+.3f})"
                reflections.append({"trait":trait,"direction":direction,"magnitude":abs(delta),"reflection":ref})
                self._log(trait,direction,abs(delta),ref,traits)
        for t in self._baseline:
            if t in traits:self._baseline[t]=(self._baseline[t]*0.95)+(traits[t]*0.05)
        return{"reflected":len(reflections)>0,"reflections":reflections}
    def get_state(self)->dict:
        try:
            with sqlite3.connect(DB_PATH) as c:
                rows=c.execute("SELECT trait,direction,magnitude,reflection FROM meta_consciousness_log ORDER BY id DESC LIMIT 5").fetchall()
                return{"recent_reflections":[{"trait":r[0],"direction":r[1],"magnitude":r[2],"reflection":r[3]} for r in rows]}
        except:return{"recent_reflections":[]}
    def _log(self,trait,direction,magnitude,reflection,snapshot):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO meta_consciousness_log(timestamp,trait,direction,magnitude,reflection,snapshot) VALUES(?,?,?,?,?,?)",(time.time(),trait,direction,magnitude,reflection,json.dumps(snapshot)));c.commit()
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

