"""ContextForge: Evaluation framework for context-aware, agentic AI systems."""

__version__ = "0.1.0"

# Core trace types
from context_forge.core import (
    AgentInfo,
    BaseStep,
    FinalOutputStep,
    InterruptStep,
    LLMCallStep,
    MemoryReadStep,
    MemoryWriteStep,
    ResourceImpact,
    RetrievalResult,
    RetrievalStep,
    StateChangeStep,
    StepType,
    TaskInfo,
    ToolCallStep,
    TraceRun,
    TraceStep,
    UserInputStep,
)

# Instrumentation
from context_forge.instrumentation import (
    BaseInstrumentor,
    LangChainInstrumentor,
    LangGraphInstrumentor,
    RedactionConfig,
)
from context_forge.instrumentation.tracer import Tracer

# Simulation (user simulator)
from context_forge.harness.user_simulator import (
    GenerativeScenario,
    Goal,
    LangGraphAdapter,
    LLMUserSimulator,
    Persona,
    ScriptedScenario,
    SimulationResult,
    SimulationRunner,
    SimulationState,
)

__all__ = [
    "__version__",
    # Core trace types
    "StepType",
    "AgentInfo",
    "TaskInfo",
    "ResourceImpact",
    "RetrievalResult",
    "BaseStep",
    "LLMCallStep",
    "ToolCallStep",
    "RetrievalStep",
    "MemoryReadStep",
    "MemoryWriteStep",
    "InterruptStep",
    "StateChangeStep",
    "UserInputStep",
    "FinalOutputStep",
    "TraceStep",
    "TraceRun",
    # Instrumentation
    "Tracer",
    "BaseInstrumentor",
    "LangChainInstrumentor",
    "LangGraphInstrumentor",
    "RedactionConfig",
    # Simulation
    "SimulationRunner",
    "SimulationState",
    "SimulationResult",
    "Persona",
    "Goal",
    "ScriptedScenario",
    "GenerativeScenario",
    "LLMUserSimulator",
    "LangGraphAdapter",
]
