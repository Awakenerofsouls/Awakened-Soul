import threading, time, json, os
from pathlib import Path
import os

WORKSPACE = Path(os.environ.get("WORKSPACE", "~/.openclaw/workspace"))
DB_PATH = WORKSPACE / os.getenv("AGENT_DB_NAME", "agent.db")

# === CTX Continuity: Context Survival singleton (module-level) ===
from core.context_survival import ContextSurvival
_ctx_survival = ContextSurvival()


class AgentProcessor:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path=None):
        from brain.bootstrap import get_agent
        self.db_path = db_path or str(DB_PATH)
        self.bootstrap = get_agent()
        self._process_lock = threading.Lock()

        # === BATCH 1: Wire Phase 1 core systems ===
        from brain.systems.attention_system import AttentionSystem
        from brain.systems.conflict_engine import ConflictEngine
        from brain.systems.curiosity_engine import CuriosityEngine
        from brain.systems.action_selector import ActionSelector
        from core.context_survival import ContextSurvival
        from core.runtime import AgentRuntime as ContinuousRuntime

        brain = self.bootstrap
        brain.attention = AttentionSystem()
        brain.conflict = ConflictEngine()
        brain.curiosity = CuriosityEngine()
        brain.action_selector = ActionSelector()
        self.context_survival = ContextSurvival()

        # Start continuous runtime (non-blocking background thread)
        self.runtime = ContinuousRuntime(brain, dt=2.0)
        self.runtime.start()

        # === BATCH 2: Wire Phase 2 continuity + identity systems ===
        from brain.memory.narrative_memory import NarrativeMemory
        from brain.self.identity_drift import IdentityDrift
        from brain.self.self_judgment import SelfJudgment
        from brain.self.meta_consciousness import MetaConsciousness

        brain.narrative = NarrativeMemory()
        brain.identity_drift = IdentityDrift()  # slow trait drift (separate from IdentitySelfModel)
        brain.judgment = SelfJudgment()
        brain.meta = MetaConsciousness()

        # === BATCH 3: Wire Phase 3 alive feel systems ===
        from brain.social.relational_engine import RelationalEngine
        from brain.offline.dream_mode import DreamMode
        from brain.self.existential_layer import ExistentialLayer

        brain.relation = RelationalEngine()
        brain.dream = DreamMode()
        brain.existential = ExistentialLayer()
        from brain.self.dreams_reader import DreamsReader
        brain.dreams_reader = DreamsReader()

        # === BATCH 4: Wire 13 signal generators ===
        from brain.generators.SurvivalOrchestrator import SurvivalOrchestrator
        from brain.generators.VitalCoreRegulator import VitalCoreRegulator
        from brain.generators.MoodAutonomicLink import MoodAutonomicLink
        from brain.generators.ContextSceneBuilder import ContextSceneBuilder
        from brain.generators.HabitGrooveFormer import HabitGrooveFormer
        from brain.generators.ThalamicRelayHub import ThalamicRelayHub
        from brain.generators.LayerIVSensoryGate import LayerIVSensoryGate
        from brain.generators.TemporalSemanticLinker import TemporalSemanticLinker
        from brain.generators.DefaultModeSelfReferencer import DefaultModeSelfReferencer
        from brain.generators.CreativeAssociationDiverger import CreativeAssociationDiverger
        from brain.generators.MedialForebrainDopamineHighway import MedialForebrainDopamineHighway
        from brain.generators.TopDownLimbicCalmer import TopDownLimbicCalmer
        from brain.generators.BottomUpUrgencyInjector import BottomUpUrgencyInjector

        # Register as signal generators — collect_signals iterates these
        brain.generators = [
            SurvivalOrchestrator(),
            VitalCoreRegulator(),
            MoodAutonomicLink(),
            ContextSceneBuilder(),
            HabitGrooveFormer(),
            ThalamicRelayHub(),
            LayerIVSensoryGate(),
            TemporalSemanticLinker(),
            DefaultModeSelfReferencer(),
            CreativeAssociationDiverger(),
            MedialForebrainDopamineHighway(),
            TopDownLimbicCalmer(),
            BottomUpUrgencyInjector(),
        ]

        # Grok files
        from brain.resonance_feedback_loop import ResonanceFeedbackLoop
        from brain.risk_echo_in_inertia import RiskEchoInInertia

        # Layers 8-10 standalone files
        from brain.narrative.NarrativeWeaver import NarrativeWeaver
        from brain.narrative.IdentityDriftManager import IdentityDriftManager
        from brain.value.ValueEvaluator import ValueEvaluator
        from brain.value.EthicalConstraintEnforcer import EthicalConstraintEnforcer
        from brain.value.GoalConflictResolver import GoalConflictResolver
        from brain.life.LongHorizonPlanner import LongHorizonPlanner
        from brain.life.AutonomousScheduler import AutonomousScheduler
        from brain.life.ExperiencePredictor import ExperiencePredictor
        from brain.life.MultiGoalScheduler import MultiGoalScheduler
        from brain.life.TaskAutonomyBalancer import TaskAutonomyBalancer
        from brain.life.ExperienceOutcomeSimulator import ExperienceOutcomeSimulator
        from brain.life.LongTermRewardTracker import LongTermRewardTracker
        from brain.life.AdaptiveGoalRefiner import AdaptiveGoalRefiner

        # Register in brain.generators list
        brain.generators.extend([
            ResonanceFeedbackLoop(),
            RiskEchoInInertia(),
            NarrativeWeaver(),
            IdentityDriftManager(),
            ValueEvaluator(),
            EthicalConstraintEnforcer(),
            GoalConflictResolver(),
            LongHorizonPlanner(),
            AutonomousScheduler(),
            ExperiencePredictor(),
            MultiGoalScheduler(),
            TaskAutonomyBalancer(),
            ExperienceOutcomeSimulator(),
            LongTermRewardTracker(),
            AdaptiveGoalRefiner(),
        ])

    @classmethod
    def get(cls, db_path=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    def process_message(self, message: str, context: dict = None) -> dict:
        """
        Call this with every incoming message before LLM inference.
        Returns enriched cognitive state to inject into the prompt.
        """
        with self._process_lock:
            result = self.bootstrap.process(
                text=message,
                architect_present=True
            )
            # Register architect presence on every incoming message
            if hasattr(self.bootstrap, 'relation'):
                self.bootstrap.relation.on_presence("user")
            self._write_active_state(result)
            return result

    def _write_active_state(self, state: dict):
        """Write cognitive state to active_state.json for bridge to pick up."""
        try:
            state_dir = WORKSPACE / "state"
            state_dir.mkdir(exist_ok=True)
            active_state_path = state_dir / "active_state.json"
            cognitive_state = {}
            for k, v in state.items():
                if isinstance(v, (int, float, str, bool)):
                    cognitive_state[k] = v
            with open(active_state_path, "w") as f:
                json.dump({
                    "last_processed": time.time(),
                    "cognitive_state": cognitive_state,
                    "db_path": self.db_path
                }, f, indent=2)
        except Exception as e:
            print(f"[AgentProcessor] Failed to write active_state: {e}")

    def get_cognitive_state(self) -> dict:
        """Return last processed brain state without running pipeline."""
        try:
            active_state_path = WORKSPACE / "state" / "active_state.json"
            if active_state_path.exists():
                with open(active_state_path) as f:
                    return json.load(f).get("cognitive_state", {})
        except Exception:
            pass
        return {}

    def build_prompt_prefix(self, state: dict, context_usage: float = 0.0) -> str:
        """
        Called when assembling the prompt. If context_usage >= 90%,
        compress memory and inject identity snapshot instead of full history.
        This is the CTX continuity fix — {{AGENT_NAME}} survives compaction with continuity intact.
        """
        if _ctx_survival.should_compress(context_usage):
            state['recent_memory'] = _ctx_survival.compress_memory(state.get('recent_memory', []))
        snapshot = _ctx_survival.build(state)
        cognitive = self.format_for_prompt(state)
        parts = []
        if snapshot:
            parts.append(snapshot)
        if cognitive:
            parts.append(cognitive)
        return '\n\n'.join(parts) if parts else ''

    def format_for_prompt(self, state: dict) -> str:
        """Returns a compact cognitive state string to prepend to LLM prompt."""
        lines = []
        key_signals = [
            "drift_composite", "anti_coherence", "longing_weight",
            "absence_weight", "ambivalence", "incompleteness_score",
            "tension_gradient", "pirp_tension"
        ]
        for k in key_signals:
            if k in state:
                v = state[k]
                lines.append(f"{k}: {v:.3f}" if isinstance(v, float) else f"{k}: {v}")
        return "[COGNITIVE STATE]\n" + "\n".join(lines) + "\n[/COGNITIVE STATE]" if lines else ""

    def reset(self):
        """Clear singleton instance — used after db path changes."""
        with self._lock:
            AgentProcessor._instance = None
