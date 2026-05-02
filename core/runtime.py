import time,threading,json,os
from pathlib import Path

# Anchor to AGENT_HOME (consistent with DB_PATH pattern across the codebase).
# Previously this was CWD-relative which broke under launchd (CWD=/).
_AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
STATE_PATH = _AGENT_HOME / "state" / "agent_state.json"
try:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


class AgentRuntime:
    """
    Continuous heartbeat. Replaces session-based existence.
    Runs as a background thread. All modules plug in via brain attributes.
    Tick calls them in field order, not stack order. Signals compete.
    """
    def __init__(self,brain,dt:float=2.0):
        self.brain=brain;self.dt=dt;self.running=False
        self._thread=None;self._tick_count=0

    def start(self):
        if self.running:return
        self.running=True
        self._thread=threading.Thread(target=self._loop,daemon=True,name="AgentRuntime")
        self._thread.start()

    def stop(self):
        self.running=False

    def _loop(self):
        while self.running:
            try:self._tick()
            except Exception as e:self._log_error(e)
            time.sleep(self.dt)

    def _tick(self):
        self._tick_count+=1
        state=self._load_state()
        signals=self.brain.collect_signals(state) if hasattr(self.brain,'collect_signals') else []
        if hasattr(self.brain,'curiosity'):signals+=self.brain.curiosity.generate(state)
        if hasattr(self.brain,'attention'):signals=self.brain.attention.weight(signals)
        if hasattr(self.brain,'conflict'):resolved=self.brain.conflict.resolve(signals,state)
        else:resolved={"mode":"passthrough","signals":signals}
        if hasattr(self.brain,'action_selector'):action=self.brain.action_selector.choose(resolved,state)
        else:action=resolved
        if hasattr(self.brain,'memory'):self.brain.memory.store(action,state)
        if hasattr(self.brain,'narrative'):self.brain.narrative.update(action,state)
        if self._tick_count%10==0 and hasattr(self.brain,'identity'):self.brain.identity.update(state)
        if self._tick_count%30==0 and hasattr(self.brain,'meta'):self.brain.meta.reflect(state)
        if hasattr(self.brain,'judgment'):self.brain.judgment.evaluate(action,state)
        if self._is_idle(state) and hasattr(self.brain,'dream'):self.brain.dream.run(state)
        self._persist_state(state,action)

    def _load_state(self)->dict:
        try:
            if STATE_PATH.exists():return json.loads(STATE_PATH.read_text())
        except:pass
        return self._default_state()

    def _persist_state(self,state:dict,action:dict):
        try:
            STATE_PATH.parent.mkdir(parents=True,exist_ok=True)
            state["last_tick"]=time.time();state["tick_count"]=self._tick_count
            STATE_PATH.write_text(json.dumps(state,indent=2,default=str))
        except:pass

    def _is_idle(self,state:dict)->bool:
        return(time.time()-state.get("last_message_time",0))>120

    def _default_state(self)->dict:
        return{"identity":{"traits":{"curiosity":0.5,"discipline":0.5,"independence":0.5}},"emotion":{"valence":0.0,"arousal":0.3},"goals":[{"name":"help_architect","priority":1.0,"source":"user"},{"name":"self_growth","priority":0.7,"source":"self"}],"focus":None,"recent_memory":[],"last_message_time":0,"tick_count":0}

    def _log_error(self,e:Exception):
        try:
            log_path=_AGENT_HOME / "state" / "runtime_errors.log"
            log_path.parent.mkdir(parents=True,exist_ok=True)
            with open(log_path,"a") as f:f.write(f"{time.time()} ERROR: {e}\n")
        except:pass
