"""LangGraph state definitions for all agents."""

from operator import add
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import BaseMessage

from src.core.models import ExtractedFact, RetrievedDocument, UserProfile


class AdvisorState(TypedDict):
    """State passed through the main orchestrator graph."""

    user_id: str
    session_id: str
    message: str
    messages: Annotated[list[BaseMessage], add]
    turn_count: int
    user_profile: Optional[UserProfile]
    weather_data: Optional[dict]
    rate_data: Optional[dict]
    solar_estimate: Optional[dict]
    retrieved_docs: list[RetrievedDocument]
    tool_observations: list[dict]  # Tool results from Analyzer (extracted from create_agent output)
    response: Optional[str]
    extracted_facts: list[ExtractedFact]
    memory_operations: list[dict]  # Memory operations from Memorizer (tool calls made)


class MemorizerState(TypedDict):
    """State for the memory offload subgraph."""

    messages: list[BaseMessage]
    user_profile: UserProfile
    extracted_facts: list[ExtractedFact]
    validated_facts: list[ExtractedFact]
    summary: Optional[str]
    turns_to_summarize: list[int]
