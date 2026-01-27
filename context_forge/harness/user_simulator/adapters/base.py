"""Base protocol for agent adapters."""

from typing import Any, Protocol, runtime_checkable

from langchain_core.messages import BaseMessage

from ..models import SimulationState


@runtime_checkable
class AgentAdapter(Protocol):
    """Protocol for adapting different agent frameworks to the simulation harness.

    Each adapter wraps a framework-specific agent and provides a uniform
    interface for:
    - Invoking the agent with user messages
    - Extracting responses in BaseMessage format
    - Managing agent state between turns
    """

    @property
    def framework(self) -> str:
        """Return the framework name (e.g., 'langgraph', 'crewai', 'pydanticai')."""
        ...

    @property
    def agent_name(self) -> str:
        """Return the agent's name/identifier."""
        ...

    async def invoke(
        self,
        message: BaseMessage,
        state: SimulationState,
    ) -> BaseMessage:
        """Invoke the agent with a user message and return the response.

        Args:
            message: User's input message (HumanMessage)
            state: Current simulation state for context

        Returns:
            Agent's response as AIMessage
        """
        ...

    async def initialize(
        self,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the agent before simulation starts.

        Called once per simulation run. Use for setup that should
        happen before the first turn.
        """
        ...

    async def cleanup(self) -> None:
        """Clean up agent resources after simulation ends."""
        ...

    def get_state(self) -> dict[str, Any]:
        """Get the current internal state of the agent.

        Used for trace capture and debugging.
        """
        ...
