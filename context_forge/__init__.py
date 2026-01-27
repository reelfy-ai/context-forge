"""ContextForge: Evaluation framework for context-aware, agentic AI systems."""

__version__ = "0.1.0"

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
    # Simulation
    "SimulationRunner",
    "SimulationState",
    "SimulationResult",
    # Personas & Scenarios
    "Persona",
    "Goal",
    "ScriptedScenario",
    "GenerativeScenario",
    # Simulators
    "LLMUserSimulator",
    # Adapters
    "LangGraphAdapter",
]
