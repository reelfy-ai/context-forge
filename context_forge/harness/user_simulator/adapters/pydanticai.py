"""PydanticAI adapter for user simulation."""

import json
from typing import Any, Callable, Generic, Optional, TypeVar

from langchain_core.messages import AIMessage, BaseMessage

from ..models import SimulationState

T = TypeVar("T")


class PydanticAIAdapter(Generic[T]):
    """Adapter for PydanticAI agents.

    PydanticAI agents use typed dependencies and structured outputs.
    This adapter manages the dependency injection and conversation state.

    Example usage:
        from pydantic_ai import Agent

        agent = Agent(
            model="ollama:llama3.1",
            system_prompt="You are a helpful assistant.",
        )

        adapter = PydanticAIAdapter(
            agent=agent,
            deps_factory=lambda state: MyDeps(user_id=state.agent_state.get("user_id")),
        )
    """

    def __init__(
        self,
        agent: Any,
        deps_factory: Optional[Callable[[SimulationState], T]] = None,
        agent_name: str = "pydanticai_agent",
    ):
        """Initialize PydanticAI adapter.

        Args:
            agent: PydanticAI Agent instance
            deps_factory: Factory function to create dependencies from state
            agent_name: Name for identification
        """
        self._agent = agent
        self._deps_factory = deps_factory
        self._agent_name = agent_name
        self._message_history: list[Any] = []

    @property
    def framework(self) -> str:
        return "pydanticai"

    @property
    def agent_name(self) -> str:
        return self._agent_name

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Reset for new simulation."""
        self._message_history = []

    async def invoke(
        self,
        message: BaseMessage,
        state: SimulationState,
    ) -> BaseMessage:
        """Invoke PydanticAI agent."""
        # Create dependencies if factory provided
        deps = None
        if self._deps_factory:
            deps = self._deps_factory(state)

        # Run agent
        if deps is not None:
            result = await self._agent.run(
                message.content,
                deps=deps,
                message_history=self._message_history,
            )
        else:
            result = await self._agent.run(
                message.content,
                message_history=self._message_history,
            )

        # Update history
        if hasattr(result, "all_messages"):
            self._message_history = result.all_messages()

        # Extract response
        response_data = result.data if hasattr(result, "data") else str(result)
        if isinstance(response_data, str):
            return AIMessage(content=response_data)
        else:
            # Structured output - serialize to string
            return AIMessage(content=json.dumps(response_data, default=str))

    async def cleanup(self) -> None:
        """Clean up PydanticAI resources."""
        pass

    def get_state(self) -> dict[str, Any]:
        """Return current message history state."""
        return {"message_history_length": len(self._message_history)}
