"""Pydantic models for simulation state and results."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ConfigDict, Field


class ConversationRole(str, Enum):
    """Role in the conversation."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class SimulationTurn(BaseModel):
    """Single turn in the simulation conversation."""

    turn_number: int
    role: ConversationRole
    message: BaseMessage
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SimulationState(BaseModel):
    """Current state of a simulation run."""

    simulation_id: str
    scenario_id: str
    persona_id: str
    turns: list[SimulationTurn] = Field(default_factory=list)
    current_turn: int = 0
    max_turns: int = 20
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    status: Literal["running", "completed", "failed", "terminated"] = "running"
    termination_reason: Optional[str] = None
    agent_state: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_messages(self) -> list[BaseMessage]:
        """Get all messages in conversation order."""
        return [turn.message for turn in self.turns]

    def get_last_agent_message(self) -> Optional[BaseMessage]:
        """Get the most recent agent message."""
        for turn in reversed(self.turns):
            if turn.role == ConversationRole.AGENT:
                return turn.message
        return None

    def get_last_user_message(self) -> Optional[BaseMessage]:
        """Get the most recent user message."""
        for turn in reversed(self.turns):
            if turn.role == ConversationRole.USER:
                return turn.message
        return None


class SimulationResult(BaseModel):
    """Result of a completed simulation."""

    simulation_id: str
    state: SimulationState
    trace_path: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    success: bool = False
    error: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "simulation_id": self.simulation_id,
            "scenario_id": self.state.scenario_id,
            "persona_id": self.state.persona_id,
            "total_turns": len(self.state.turns),
            "status": self.state.status,
            "termination_reason": self.state.termination_reason,
            "started_at": self.state.started_at.isoformat(),
            "ended_at": self.state.ended_at.isoformat() if self.state.ended_at else None,
            "metrics": self.metrics,
            "success": self.success,
            "error": self.error,
            "trace_path": self.trace_path,
            "conversation": [
                {
                    "turn": t.turn_number,
                    "role": t.role.value,
                    "content": t.message.content,
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in self.state.turns
            ],
        }
