"""Persona and behavior definitions for user simulation."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CommunicationStyle(str, Enum):
    """How the persona communicates."""

    CONCISE = "concise"
    VERBOSE = "verbose"
    CASUAL = "casual"
    FORMAL = "formal"
    CONFUSED = "confused"
    IMPATIENT = "impatient"


class TechnicalLevel(str, Enum):
    """Technical sophistication of the persona."""

    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class Behavior(BaseModel):
    """Behavioral traits that influence response generation."""

    communication_style: CommunicationStyle = CommunicationStyle.CASUAL
    technical_level: TechnicalLevel = TechnicalLevel.INTERMEDIATE
    patience_level: int = Field(default=5, ge=1, le=10)

    # Response patterns
    asks_followup_questions: bool = True
    provides_context_upfront: bool = True
    corrects_misunderstandings: bool = True

    # Conversation dynamics
    topic_drift_probability: float = Field(default=0.1, ge=0, le=1)
    clarification_threshold: int = Field(default=2)


class Goal(BaseModel):
    """A specific goal the persona wants to achieve."""

    description: str
    success_criteria: str
    priority: int = Field(default=1, ge=1, le=5)
    is_achieved: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class Persona(BaseModel):
    """Complete persona definition for user simulation.

    A persona represents a simulated user with specific characteristics,
    goals, and behavioral traits. The LLM uses this to generate contextually
    appropriate responses.
    """

    persona_id: str
    name: str
    description: str = ""

    # Context that shapes responses
    background: str = ""
    situation: str = ""

    # Behavioral configuration
    behavior: Behavior = Field(default_factory=Behavior)

    # Goals for this conversation
    goals: list[Goal] = Field(default_factory=list)

    # Domain-specific context
    context: dict[str, Any] = Field(default_factory=dict)

    # Example phrases this persona might use
    example_phrases: list[str] = Field(default_factory=list)

    def to_system_prompt(self) -> str:
        """Generate system prompt for LLM-based response generation."""
        style_desc = {
            CommunicationStyle.CONCISE: "Keep responses brief and to the point.",
            CommunicationStyle.VERBOSE: "Provide detailed responses with context.",
            CommunicationStyle.CASUAL: "Use informal, conversational language.",
            CommunicationStyle.FORMAL: "Use professional, polished language.",
            CommunicationStyle.CONFUSED: "Often ask for clarification or express uncertainty.",
            CommunicationStyle.IMPATIENT: "Express urgency, want quick answers.",
        }

        tech_desc = {
            TechnicalLevel.NOVICE: "Avoid technical jargon. Ask for simpler explanations.",
            TechnicalLevel.INTERMEDIATE: "Comfortable with basic domain terminology.",
            TechnicalLevel.EXPERT: "Use technical terms confidently. Challenge vague answers.",
        }

        goals_str = "\n".join(
            f"- {g.description}" for g in self.goals if not g.is_achieved
        )

        prompt_parts = [
            f"You are simulating a user named {self.name}.",
        ]

        if self.background:
            prompt_parts.append(f"\nBackground: {self.background}")

        if self.situation:
            prompt_parts.append(f"Current Situation: {self.situation}")

        prompt_parts.extend([
            f"\nCommunication Style: {style_desc[self.behavior.communication_style]}",
            f"Technical Level: {tech_desc[self.behavior.technical_level]}",
        ])

        if goals_str:
            prompt_parts.append(f"\nYour goals for this conversation:\n{goals_str}")
        else:
            prompt_parts.append("\nYour goal: Have a productive conversation")

        if self.context:
            context_str = ", ".join(f"{k}: {v}" for k, v in self.context.items())
            prompt_parts.append(f"\nAdditional context: {context_str}")

        if self.example_phrases:
            phrases_str = ", ".join(f'"{p}"' for p in self.example_phrases[:3])
            prompt_parts.append(f"\nExample phrases you might use: {phrases_str}")

        prompt_parts.append(
            "\n\nRespond as this user would, staying in character. "
            "Generate only the user's message, not the agent's response."
        )

        return "\n".join(prompt_parts)

    def mark_goal_achieved(self, goal_description: str) -> bool:
        """Mark a goal as achieved by its description."""
        for goal in self.goals:
            if goal.description == goal_description:
                goal.is_achieved = True
                return True
        return False

    def get_pending_goals(self) -> list[Goal]:
        """Get list of goals not yet achieved."""
        return [g for g in self.goals if not g.is_achieved]

    def reset_goals(self) -> None:
        """Reset all goals to not achieved."""
        for goal in self.goals:
            goal.is_achieved = False
