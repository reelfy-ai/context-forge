"""LangGraph adapter for user simulation."""

import asyncio
from typing import Any, Callable, Optional

from langchain_core.messages import AIMessage, BaseMessage

from ..models import SimulationState


class LangGraphAdapter:
    """Adapter for LangGraph StateGraph agents.

    Wraps a compiled LangGraph and translates between the simulation
    harness message format and LangGraph's state-based invocation.

    Example usage:
        from my_agent import build_my_graph, MyAgentState

        graph = build_my_graph()
        adapter = LangGraphAdapter(
            graph=graph,
            state_class=MyAgentState,
            input_key="message",
            output_key="response",
        )
    """

    def __init__(
        self,
        graph: Any,
        state_class: Optional[type] = None,
        input_key: str = "message",
        output_key: str = "response",
        messages_key: str = "messages",
        agent_name: str = "langgraph_agent",
        initial_state: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        state_builder: Optional[Callable[[BaseMessage, SimulationState], dict[str, Any]]] = None,
    ):
        """Initialize the LangGraph adapter.

        Args:
            graph: Compiled LangGraph StateGraph
            state_class: TypedDict or Pydantic class for agent state (optional)
            input_key: State key for user input message
            output_key: State key for agent response
            messages_key: State key for conversation history
            agent_name: Name for identification
            initial_state: Initial state values
            config: LangGraph config (thread_id, etc.)
            state_builder: Optional custom function to build input state
        """
        self._graph = graph
        self._state_class = state_class
        self._input_key = input_key
        self._output_key = output_key
        self._messages_key = messages_key
        self._agent_name = agent_name
        self._initial_state = initial_state or {}
        self._config = config or {}
        self._state_builder = state_builder
        self._current_state: dict[str, Any] = {}

    @property
    def framework(self) -> str:
        return "langgraph"

    @property
    def agent_name(self) -> str:
        return self._agent_name

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Reset state for a new simulation."""
        self._current_state = dict(self._initial_state)
        if config:
            self._config.update(config)

    async def invoke(
        self,
        message: BaseMessage,
        state: SimulationState,
    ) -> BaseMessage:
        """Invoke the LangGraph agent with a user message."""
        # Build input state
        if self._state_builder:
            input_state = self._state_builder(message, state)
        else:
            input_state = self._build_default_state(message, state)

        # Invoke graph
        result = await self._invoke_graph(input_state)

        # Update internal state tracking
        self._current_state = dict(result)

        # Extract response
        response_text = result.get(self._output_key, "")
        if isinstance(response_text, BaseMessage):
            return response_text
        return AIMessage(content=str(response_text) if response_text else "")

    def _build_default_state(
        self,
        message: BaseMessage,
        state: SimulationState,
    ) -> dict[str, Any]:
        """Build default input state from message and simulation state."""
        # Get messages from simulation state
        messages = [t.message for t in state.turns]

        input_state = {
            self._input_key: message.content,
            self._messages_key: messages,
            **self._current_state,
        }

        # Carry over any fields from initial state that aren't set
        for key, value in self._initial_state.items():
            if key not in input_state:
                input_state[key] = value

        return input_state

    async def _invoke_graph(self, input_state: dict) -> dict:
        """Invoke the graph, handling sync/async."""
        if hasattr(self._graph, "ainvoke"):
            return await self._graph.ainvoke(input_state, config=self._config)
        else:
            return await asyncio.to_thread(
                self._graph.invoke, input_state, config=self._config
            )

    async def cleanup(self) -> None:
        """No cleanup needed for LangGraph."""
        pass

    def get_state(self) -> dict[str, Any]:
        """Return current agent state."""
        return dict(self._current_state)
