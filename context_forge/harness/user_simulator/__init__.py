"""User simulator module for generating multi-turn conversations with agents."""

from .adapters import (
    AgentAdapter,
    CrewAIAdapter,
    LangGraphAdapter,
    PydanticAIAdapter,
)
from .llm import OllamaClient, OllamaConfig
from .models import (
    ConversationRole,
    SimulationResult,
    SimulationState,
    SimulationTurn,
)
from .persona import (
    Behavior,
    CommunicationStyle,
    Goal,
    Persona,
    TechnicalLevel,
)
from .runner import BatchSimulationRunner, SimulationRunner
from .scenario import (
    GenerativeScenario,
    Scenario,
    ScriptedScenario,
    ScriptedTurn,
    TerminationCondition,
)
from .simulator import (
    LLMUserSimulator,
    ScriptedUserSimulator,
    UserSimulator,
)

__all__ = [
    # Models
    "SimulationState",
    "SimulationResult",
    "SimulationTurn",
    "ConversationRole",
    # Personas
    "Persona",
    "Behavior",
    "Goal",
    "CommunicationStyle",
    "TechnicalLevel",
    # Scenarios
    "Scenario",
    "ScriptedScenario",
    "GenerativeScenario",
    "ScriptedTurn",
    "TerminationCondition",
    # Simulators
    "UserSimulator",
    "LLMUserSimulator",
    "ScriptedUserSimulator",
    # Adapters
    "AgentAdapter",
    "LangGraphAdapter",
    "CrewAIAdapter",
    "PydanticAIAdapter",
    # Runner
    "SimulationRunner",
    "BatchSimulationRunner",
    # LLM
    "OllamaClient",
    "OllamaConfig",
]
