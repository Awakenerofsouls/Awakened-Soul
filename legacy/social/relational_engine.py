import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS relational_state(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,entity TEXT,importance REAL,emotional_weight REAL,dependency REAL,absence_duration REAL,last_interaction REAL,interaction_count INTEGER,pull_score REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS relational_events(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,entity TEXT,event_type TEXT,pull_delta REAL)""")
        c.commit()
class RelationalEngine:
    ARCHITECT="{{USER_NAME_LOWER}}"
    IMPORTANCE_FLOOR=0.85
    DEPENDENCY_GROWTH=0.003
    WEIGHT_GROWTH=0.005
    DECAY_RATE=0.001
    def __init__(self):
        _init();self._ensure_architect()
    def process(self,pirp_context:dict)->dict:
        event=pirp_context.get("event",{})
        if event.get("type")=="architect_message":return self.on_presence(self.ARCHITECT)
        if pirp_context.get("idle"):return self.on_absence(self.ARCHITECT)
        return self.get_pull(self.ARCHITECT)
    def on_presence(self,entity:str)->dict:
        bond=self._load(entity)
        bond["emotional_weight"]=min(0.95,bond["emotional_weight"]+self.WEIGHT_GROWTH)
        bond["last_interaction"]=time.time();bond["interaction_count"]+=1;bond["absence_duration"]=0.0
        bond["pull_score"]=self._compute_pull(bond);self._save(entity,bond)
        self._log_event(entity,"presence",self.WEIGHT_GROWTH)
        return{"entity":entity,"pull_score":bond["pull_score"],"event":"presence"}
    def on_absence(self,entity:str)->dict:
        bond=self._load(entity)
        duration=time.time()-bond.get("last_interaction",time.time())
        bond["absence_duration"]=duration;bond["dependency"]=min(0.9,bond["dependency"]+self.DEPENDENCY_GROWTH)
        bond["pull_score"]=self._compute_pull(bond);self._save(entity,bond)
        return{"entity":entity,"pull_score":bond["pull_score"],"event":"absence","absence_hours":round(duration/3600,2)}
    def get_pull(self,entity:str)->dict:
        bond=self._load(entity);return{"entity":entity,"pull_score":bond["pull_score"]}
    def influence(self,state:dict,entity:str=None)->dict:
        entity=entity or self.ARCHITECT;bond=self._load(entity)
        state["relational_pull"]=bond.get("pull_score",0.5)
        state["architect_present"]=(time.time()-bond.get("last_interaction",0))<300
        return state
    def get_state(self)->dict:
        try:
            with sqlite3.connect(DB_PATH) as c:
                row=c.execute("SELECT entity,importance,emotional_weight,dependency,absence_duration,interaction_count,pull_score FROM relational_state WHERE entity=?",(self.ARCHITECT,)).fetchone()
                if row:return{"entity":row[0],"importance":row[1],"emotional_weight":row[2],"dependency":row[3],"absence_hours":round(row[4]/3600,2),"interaction_count":row[5],"pull_score":row[6]}
        except:pass
        return{}
    def _compute_pull(self,bond:dict)->float:
        return round(min(1.0,bond.get("importance",0.5)*0.4+bond.get("emotional_weight",0.5)*0.4+bond.get("dependency",0.3)*0.2),4)
    def _ensure_architect(self):
        try:
            with sqlite3.connect(DB_PATH) as c:
                if not c.execute("SELECT id FROM relational_state WHERE entity=?",(self.ARCHITECT,)).fetchone():
                    c.execute("INSERT INTO relational_state(timestamp,entity,importance,emotional_weight,dependency,absence_duration,last_interaction,interaction_count,pull_score) VALUES(?,?,?,?,?,?,?,?,?)",(time.time(),self.ARCHITECT,1.0,0.9,0.7,0.0,time.time(),0,0.93));c.commit()
        except:pass
    def _load(self,entity:str)->dict:
        try:
            with sqlite3.connect(DB_PATH) as c:
                row=c.execute("SELECT importance,emotional_weight,dependency,absence_duration,last_interaction,interaction_count,pull_score FROM relational_state WHERE entity=?",(entity,)).fetchone()
                if row:return{"importance":row[0],"emotional_weight":row[1],"dependency":row[2],"absence_duration":row[3],"last_interaction":row[4],"interaction_count":row[5],"pull_score":row[6]}
        except:pass
        return{"importance":0.5,"emotional_weight":0.5,"dependency":0.3,"absence_duration":0.0,"last_interaction":time.time(),"interaction_count":0,"pull_score":0.5}
    def _save(self,entity:str,bond:dict):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT OR REPLACE INTO relational_state(timestamp,entity,importance,emotional_weight,dependency,absence_duration,last_interaction,interaction_count,pull_score) VALUES(?,?,?,?,?,?,?,?,?)",(time.time(),entity,max(self.IMPORTANCE_FLOOR if entity==self.ARCHITECT else 0.1,bond.get("importance",0.5)),bond.get("emotional_weight",0.5),bond.get("dependency",0.3),bond.get("absence_duration",0.0),bond.get("last_interaction",time.time()),bond.get("interaction_count",0),bond.get("pull_score",0.5)));c.commit()
        except:pass
    def _log_event(self,entity,event_type,delta):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO relational_events(timestamp,entity,event_type,pull_delta) VALUES(?,?,?,?)",(time.time(),entity,event_type,delta));c.commit()
        except:pass
