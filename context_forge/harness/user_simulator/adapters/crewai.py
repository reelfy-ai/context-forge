"""CrewAI adapter for user simulation."""

import asyncio
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from ..models import SimulationState


class CrewAIAdapter:
    """Adapter for CrewAI multi-agent crews.

    Wraps a CrewAI Crew and provides a conversational interface
    for the simulation harness.

    Note: CrewAI is task-oriented rather than conversational.
    This adapter treats each user message as a task input.

    Example usage:
        from crewai import Agent, Crew, Task

        agent = Agent(role="Assistant", goal="Help users", ...)
        crew = Crew(agents=[agent], tasks=[...])

        adapter = CrewAIAdapter(
            crew=crew,
            task_template="User request: {message}",
        )
    """

    def __init__(
        self,
        crew: Any,
        task_template: str = "{message}",
        agent_name: str = "crewai_crew",
        context_window: int = 5,
    ):
        """Initialize CrewAI adapter.

        Args:
            crew: CrewAI Crew instance
            task_template: Template for converting messages to tasks
            agent_name: Name for identification
            context_window: Number of recent turns to include as context
        """
        self._crew = crew
        self._task_template = task_template
        self._agent_name = agent_name
        self._context_window = context_window
        self._context: list[str] = []

    @property
    def framework(self) -> str:
        return "crewai"

    @property
    def agent_name(self) -> str:
        return self._agent_name

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Reset context for new simulation."""
        self._context = []

    async def invoke(
        self,
        message: BaseMessage,
        state: SimulationState,
    ) -> BaseMessage:
        """Invoke CrewAI with user message as task input."""
        # Format message as task input
        task_input = self._task_template.format(message=message.content)

        # Build context from recent turns
        context = "\n".join(self._context[-self._context_window:])

        # Run crew
        try:
            result = await asyncio.to_thread(
                self._crew.kickoff,
                inputs={"task": task_input, "context": context, "message": message.content}
            )
        except Exception as e:
            # Handle case where crew doesn't accept these inputs
            result = await asyncio.to_thread(self._crew.kickoff)

        # Store turn for context
        self._context.append(f"User: {message.content}")
        result_str = str(result) if result else ""
        self._context.append(f"Agent: {result_str}")

        return AIMessage(content=result_str)

    async def cleanup(self) -> None:
        """Clean up CrewAI resources."""
        pass

    def get_state(self) -> dict[str, Any]:
        """Return current context state."""
        return {"context_turns": len(self._context) // 2}
