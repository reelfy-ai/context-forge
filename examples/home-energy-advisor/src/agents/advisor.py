"""Advisor agent: main orchestrator graph.

This module uses LangGraph's native memory primitives:
- Checkpointer: Automatically persists state between invocations (short-term memory)
- Store: Cross-session key-value storage for user profiles (long-term memory)

The graph is compiled with both checkpointer and store, enabling:
- Multi-turn conversations within a session (checkpointer handles messages)
- Profile persistence across sessions (store handles user profiles)
"""

from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.store.base import BaseStore

from src.agents.analyzer import invoke_analyzer
from src.core.state import AdvisorState
from src.nodes.intake import intake_node
from src.nodes.recall import recall_node
from src.nodes.recommend import recommend_node


def _should_analyze(state: AdvisorState) -> Literal["analyze", "recommend"]:
    """Decide whether to route to Analyzer or skip to Recommend.

    Routes to Analyzer when the query likely needs tool data (weather, rates, solar).
    Skips to Recommend for simple questions that can be answered from profile alone.
    """
    message = state.get("message", "").lower()

    # Keywords that suggest tool calls are needed
    tool_keywords = [
        "weather", "forecast", "temperature", "cloud",
        "rate", "cost", "price", "bill", "tariff", "tou",
        "solar", "production", "generate", "panel",
        "charge", "charging", "ev", "electric vehicle",
        "today", "tonight", "tomorrow", "this week",
        "how much", "when should", "best time",
        "optimize", "save", "reduce",
    ]

    if any(kw in message for kw in tool_keywords):
        return "analyze"
    return "recommend"


def _should_memorize(state: AdvisorState) -> Literal["memorize", "end"]:
    """Decide whether to invoke the Memorizer subgraph."""
    if state.get("should_memorize", False):
        return "memorize"
    return "end"


def _analyze_node(state: AdvisorState) -> dict:
    """Invoke the Analyzer agent and merge results back into state."""
    tools = _get_available_tools()

    # Build context from profile
    context = {}
    profile = state.get("user_profile")
    if profile:
        if profile.location:
            context["location"] = {
                "zip_code": profile.location.zip_code,
                "lat": profile.location.lat,
                "lon": profile.location.lon,
                "utility_provider": profile.location.utility_provider,
                "rate_schedule": profile.location.rate_schedule,
            }
        if profile.equipment:
            context["equipment"] = {
                "solar_capacity_kw": profile.equipment.solar_capacity_kw,
                "ev_model": profile.equipment.ev_model,
            }

    result = invoke_analyzer(
        query=state["message"],
        tools=tools,
        context=context,
    )

    return {
        "tool_observations": result["tool_observations"],
    }


def _get_available_tools() -> list:
    """Get the list of @tool-decorated functions available for the Analyzer."""
    try:
        from src.tools import get_tool_list
        return get_tool_list()
    except (ImportError, AttributeError):
        return []


def _memorize_node(state: AdvisorState, *, store: BaseStore) -> dict:
    """Invoke the Memorizer subgraph to extract facts and update profile.

    Bridges AdvisorState → MemorizerState, runs the subgraph,
    then persists the updated profile to the LangGraph Store.

    Args:
        state: Current advisor state
        store: LangGraph Store for profile persistence (injected by runtime)
    """
    from src.agents.memorizer import build_memorizer_graph
    from src.core.state import MemorizerState
    from src.memory.helpers import save_profile_to_store

    config_module = __import__("src.config", fromlist=["get_config"])
    config = config_module.get_config()

    # Determine which turns to summarize (if > max_turns_before_summary)
    max_turns = config.memorizer.max_turns_before_summary
    messages = state.get("messages", [])
    turns_to_summarize = list(range(len(messages))) if len(messages) > max_turns else []

    memorizer_state = MemorizerState(
        messages=messages,
        user_profile=state.get("user_profile"),
        extracted_facts=[],
        validated_facts=[],
        summary=None,
        turns_to_summarize=turns_to_summarize,
    )

    graph = build_memorizer_graph()
    result = graph.invoke(memorizer_state)

    # Persist the updated profile to LangGraph Store
    updated_profile = result.get("user_profile")
    if updated_profile:
        save_profile_to_store(store, updated_profile)

    return {
        "extracted_facts": result.get("validated_facts", []),
        "user_profile": updated_profile,
    }


def build_advisor_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
) -> StateGraph:
    """Build the Advisor orchestrator StateGraph.

    Flow: Intake → Recall → [Analyzer?] → Recommend → [Memorizer?] → END

    The checkpointer automatically persists state between invocations,
    eliminating the need for a manual _persist_session node.

    Args:
        checkpointer: LangGraph checkpointer for session state persistence.
                     If None, state is not persisted between invocations.
        store: LangGraph Store for cross-session profile storage.
               If None, profiles are created fresh each invocation.

    Returns:
        Compiled StateGraph ready for invocation
    """
    graph = StateGraph(AdvisorState)

    # Add nodes
    graph.add_node("intake", intake_node)
    graph.add_node("recall", recall_node)  # Uses store parameter
    graph.add_node("analyze", _analyze_node)
    graph.add_node("recommend", recommend_node)
    graph.add_node("memorize", _memorize_node)  # Uses store parameter

    # Set entry point
    graph.set_entry_point("intake")

    # Edges
    # Note: No _persist_session node - checkpointer handles state persistence
    graph.add_edge("intake", "recall")
    graph.add_conditional_edges(
        "recall",
        _should_analyze,
        {"analyze": "analyze", "recommend": "recommend"},
    )
    graph.add_edge("analyze", "recommend")
    graph.add_conditional_edges(
        "recommend",
        _should_memorize,
        {"memorize": "memorize", "end": END},
    )
    graph.add_edge("memorize", END)

    return graph.compile(checkpointer=checkpointer, store=store)


def create_advisor(data_dir: str = "./data") -> StateGraph:
    """Create an Advisor graph with SQLite persistence.

    Convenience factory that sets up:
    - SqliteSaver checkpointer for session state
    - InMemoryStore for profile storage (TODO: replace with persistent store)

    Args:
        data_dir: Directory for SQLite database

    Returns:
        Compiled Advisor graph with persistence enabled
    """
    import sqlite3
    from pathlib import Path

    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.store.memory import InMemoryStore

    # Ensure data directory exists
    Path(data_dir).mkdir(parents=True, exist_ok=True)

    # Create checkpointer for session state
    # Note: check_same_thread=False required for LangGraph's multi-threaded execution
    db_path = Path(data_dir) / "checkpoints.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    # Create store for profiles (in-memory for now, could use persistent store)
    store = InMemoryStore()

    return build_advisor_graph(checkpointer=checkpointer, store=store)
