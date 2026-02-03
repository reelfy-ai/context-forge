"""User simulator implementations."""

from typing import Optional, Protocol, runtime_checkable

from langchain_core.messages import BaseMessage, HumanMessage

from .llm.ollama import OllamaClient, OllamaConfig
from .models import ConversationRole, SimulationState
from .persona import Persona
from .scenario import ScriptedScenario


@runtime_checkable
class UserSimulator(Protocol):
    """Protocol for simulating user behavior in agent conversations.

    Implementations can be:
    - LLM-based (using Ollama to generate contextual responses)
    - Scripted (returning pre-defined responses)
    - Hybrid (following a script with LLM fallback)
    """

    @property
    def persona(self) -> Persona:
        """Get the persona driving this simulator."""
        ...

    async def generate_response(
        self,
        agent_message: BaseMessage,
        state: SimulationState,
    ) -> BaseMessage:
        """Generate the next user message in response to agent output.

        Args:
            agent_message: The agent's most recent message
            state: Current simulation state including conversation history

        Returns:
            A HumanMessage representing the simulated user's response
        """
        ...

    async def should_terminate(
        self,
        state: SimulationState,
    ) -> tuple[bool, Optional[str]]:
        """Determine if the conversation should end.

        Args:
            state: Current simulation state

        Returns:
            Tuple of (should_terminate, reason)
        """
        ...

    def reset(self) -> None:
        """Reset simulator state for a new conversation."""
        ...


class LLMUserSimulator:
    """User simulator powered by Ollama LLM.

    Generates contextually appropriate user responses based on
    persona, goals, and conversation history.

    Example usage:
        persona = Persona(
            persona_id="test_user",
            name="Sarah",
            background="Homeowner with solar panels",
            goals=[Goal(description="Get EV charging advice", ...)],
        )

        simulator = LLMUserSimulator(persona)
        await simulator.initialize()

        response = await simulator.generate_response(agent_message, state)
    """

    def __init__(
        self,
        persona: Persona,
        ollama_config: Optional[OllamaConfig] = None,
        check_goals: bool = True,
    ):
        """Initialize the LLM user simulator.

        Args:
            persona: Persona to simulate
            ollama_config: Configuration for Ollama
            check_goals: Whether to check goal achievement for termination
        """
        self._persona = persona
        self._ollama_config = ollama_config or OllamaConfig()
        self._check_goals = check_goals
        self._client: Optional[OllamaClient] = None
        self._initialized = False

    @property
    def persona(self) -> Persona:
        return self._persona

    async def initialize(self) -> None:
        """Initialize the Ollama client."""
        if self._initialized:
            return
        self._client = OllamaClient(self._ollama_config)
        await self._client.__aenter__()
        self._initialized = True

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
            self._initialized = False

    async def generate_response(
        self,
        agent_message: BaseMessage,
        state: SimulationState,
    ) -> BaseMessage:
        """Generate a user response using the LLM."""
        if not self._client or not self._initialized:
            await self.initialize()

        # Build conversation context
        history = self._format_history(state)

        prompt = f"""Based on the conversation history below, generate the next message from the user's perspective.

Conversation History:
{history}

Agent's last message: {agent_message.content}

Generate only the user's response (no labels or prefixes). Stay in character.
Keep your response focused and concise (1-3 sentences typically)."""

        system_prompt = self._persona.to_system_prompt()
        response = await self._client.generate(prompt, system=system_prompt)

        # Clean up response
        cleaned = response.strip()
        # Remove any accidental role prefixes
        for prefix in ["User:", "user:", "Human:", "human:", "Me:", "me:"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        return HumanMessage(content=cleaned)

    def _format_history(self, state: SimulationState) -> str:
        """Format conversation history for the prompt."""
        lines = []
        # Include last 10 turns for context
        for turn in state.turns[-10:]:
            role = "User" if turn.role == ConversationRole.USER else "Agent"
            lines.append(f"{role}: {turn.message.content}")
        return "\n".join(lines) or "(No history yet)"

    async def should_terminate(
        self,
        state: SimulationState,
    ) -> tuple[bool, Optional[str]]:
        """Determine if conversation should end."""
        # Check max turns
        if state.current_turn >= state.max_turns:
            return True, "max_turns_reached"

        # Check goal achievement (use LLM to evaluate)
        if self._check_goals and self._persona.goals:
            achieved = await self._check_goals_achieved(state)
            if achieved:
                return True, "goals_achieved"

        return False, None

    async def _check_goals_achieved(self, state: SimulationState) -> bool:
        """Use LLM to check if goals have been achieved."""
        if not self._client or not self._initialized:
            return False

        pending_goals = self._persona.get_pending_goals()
        if not pending_goals:
            return True

        goals_str = "\n".join(
            f"- {g.description}: {g.success_criteria}"
            for g in pending_goals
        )

        history = self._format_history(state)

        prompt = f"""Based on this conversation, have the user's goals been achieved?

Goals:
{goals_str}

Conversation:
{history}

Answer with ONLY 'yes' or 'no'."""

        response = await self._client.generate(prompt)
        return response.strip().lower() == "yes"

    def reset(self) -> None:
        """Reset persona goal states."""
        self._persona.reset_goals()


class ScriptedUserSimulator:
    """User simulator that follows a pre-defined script.

    Falls back to LLM generation if script is exhausted
    and fallback mode is 'generative'.

    Example usage:
        scenario = ScriptedScenario(
            scenario_id="test",
            name="Test scenario",
            persona=persona,
            turns=[
                ScriptedTurn(turn_number=0, user_message="Hello"),
                ScriptedTurn(turn_number=1, user_message="What time should I charge?"),
            ],
        )

        simulator = ScriptedUserSimulator(scenario)
    """

    def __init__(
        self,
        scenario: ScriptedScenario,
        llm_fallback: Optional[LLMUserSimulator] = None,
    ):
        """Initialize scripted user simulator.

        Args:
            scenario: Scripted scenario with predefined turns
            llm_fallback: Optional LLM simulator for fallback generation
        """
        self._scenario = scenario
        self._llm_fallback = llm_fallback

    @property
    def persona(self) -> Persona:
        return self._scenario.persona

    async def initialize(self) -> None:
        """Initialize fallback simulator if present."""
        if self._llm_fallback:
            await self._llm_fallback.initialize()

    async def cleanup(self) -> None:
        """Clean up fallback simulator if present."""
        if self._llm_fallback:
            await self._llm_fallback.cleanup()

    async def generate_response(
        self,
        agent_message: BaseMessage,
        state: SimulationState,
    ) -> BaseMessage:
        """Return scripted response or fall back to LLM."""
        scripted = self._scenario.get_turn_message(state.current_turn)

        if scripted:
            return HumanMessage(content=scripted)

        # Script exhausted
        if self._scenario.fallback == "terminate":
            raise StopIteration("Script exhausted")
        elif self._scenario.fallback == "loop":
            # Restart from beginning
            if self._scenario.turns:
                turn_in_script = state.current_turn % len(self._scenario.turns)
                scripted = self._scenario.turns[turn_in_script].user_message
                return HumanMessage(content=scripted)
            raise StopIteration("No turns in script")
        elif self._scenario.fallback == "generative" and self._llm_fallback:
            return await self._llm_fallback.generate_response(agent_message, state)

        raise ValueError(f"Invalid fallback mode: {self._scenario.fallback}")

    async def should_terminate(
        self,
        state: SimulationState,
    ) -> tuple[bool, Optional[str]]:
        """Check termination conditions."""
        if state.current_turn >= self._scenario.max_turns:
            return True, "max_turns_reached"

        # Check if script is exhausted in terminate mode
        if self._scenario.fallback == "terminate":
            scripted = self._scenario.get_turn_message(state.current_turn)
            if scripted is None:
                return True, "script_exhausted"

        return False, None

    def reset(self) -> None:
        """Reset state."""
        self._scenario.persona.reset_goals()
