"""Scenario definitions for user simulation."""

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field

from .persona import Persona


class TerminationCondition(BaseModel):
    """Condition that can end a simulation."""

    condition_type: Literal["max_turns", "goal_achieved", "keyword", "custom"]
    value: Any
    description: str = ""


class ScriptedTurn(BaseModel):
    """A pre-defined turn in a scripted scenario."""

    turn_number: int
    user_message: str
    expected_keywords: list[str] = Field(default_factory=list)
    allow_variation: bool = False


class ScriptedScenario(BaseModel):
    """A scenario with pre-defined user messages.

    Useful for regression testing and specific edge case validation.
    """

    scenario_id: str
    name: str
    description: str = ""
    persona: Persona

    # Pre-defined conversation script
    turns: list[ScriptedTurn]

    # What to do after script exhausted
    fallback: Literal["loop", "generative", "terminate"] = "terminate"

    # Termination conditions
    max_turns: int = Field(default=50)
    termination_conditions: list[TerminationCondition] = Field(default_factory=list)

    def get_turn_message(self, turn_number: int) -> Optional[str]:
        """Get the scripted message for a turn, if available."""
        for turn in self.turns:
            if turn.turn_number == turn_number:
                return turn.user_message
        return None

    def get_initial_message(self) -> str:
        """Get the first user message."""
        if self.turns:
            return self.turns[0].user_message
        raise ValueError("Scripted scenario has no turns defined")


class GenerativeScenario(BaseModel):
    """A scenario where user responses are LLM-generated.

    The persona and goals guide response generation. More flexible
    than scripted scenarios for exploratory testing.
    """

    scenario_id: str
    name: str
    description: str = ""
    persona: Persona

    # Initial user message to start conversation
    initial_message: str

    # Constraints on response generation
    max_turns: int = Field(default=20)
    termination_conditions: list[TerminationCondition] = Field(default_factory=list)

    # Response generation parameters
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_response_tokens: int = Field(default=500)

    # Topic boundaries
    allowed_topics: list[str] = Field(default_factory=list)
    forbidden_topics: list[str] = Field(default_factory=list)

    def get_initial_message(self) -> str:
        """Get the initial user message."""
        return self.initial_message


# Union type for all scenarios
Scenario = Union[ScriptedScenario, GenerativeScenario]
