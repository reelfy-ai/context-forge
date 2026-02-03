"""Core types and trace models for ContextForge.

This module contains the canonical trace specification including:
- StepType enum for step discrimination
- AgentInfo, TaskInfo metadata models
- All step type models (LLMCallStep, ToolCallStep, etc.)
- TraceStep discriminated union
- TraceRun complete trace model
"""

from context_forge.core.types import (
    AgentInfo,
    ResourceImpact,
    RetrievalResult,
    StepType,
    TaskInfo,
)
from context_forge.core.trace import (
    BaseStep,
    FinalOutputStep,
    InterruptStep,
    LLMCallStep,
    MemoryReadStep,
    MemoryWriteStep,
    RetrievalStep,
    StateChangeStep,
    ToolCallStep,
    TraceRun,
    TraceStep,
    UserInputStep,
)

__all__ = [
    # Enums
    "StepType",
    # Metadata models
    "AgentInfo",
    "TaskInfo",
    "ResourceImpact",
    "RetrievalResult",
    # Step models
    "BaseStep",
    "LLMCallStep",
    "ToolCallStep",
    "RetrievalStep",
    "MemoryReadStep",
    "MemoryWriteStep",
    "InterruptStep",
    "StateChangeStep",
    "UserInputStep",
    "FinalOutputStep",
    # Union and container
    "TraceStep",
    "TraceRun",
]
