import sqlite3,time,json
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova")))) / "nova.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS meta_consciousness_log(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,trait TEXT,direction TEXT,magnitude REAL,reflection TEXT,snapshot TEXT)""")
        c.commit()
class MetaConsciousness:
    DRIFT_THRESHOLD=0.05
    def __init__(self):
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
