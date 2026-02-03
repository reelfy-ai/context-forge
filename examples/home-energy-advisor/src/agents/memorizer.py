"""Memorizer agent: ReAct-style agent for learning and profile updates.

Uses the same pattern as the Analyzer - an LLM with tools that decides
what actions to take. The memorizer evaluates conversations and decides
if there's anything worth remembering.

Key design: The memorizer is cost-efficient. It evaluates importance internally
and may decide "nothing worth remembering" without calling any tools.
"""

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.store.base import BaseStore

from src.config import get_config
from src.core.prompts import MEMORIZER_SYSTEM_PROMPT
from src.llm import get_llm
from src.tools.memory import create_memory_tools


def build_memorizer(user_id: str, store: BaseStore) -> Any:
    """Build the Memorizer agent using LangGraph's create_react_agent.

    The memorizer has access to memory tools:
    - get_current_profile: Check what's already stored
    - update_profile_field: Update a profile field
    - add_observation: Add a note/observation

    Args:
        user_id: User identifier for profile storage
        store: LangGraph Store for profile persistence

    Returns:
        A compiled LangGraph Runnable implementing the ReAct pattern.
    """
    llm = get_llm("memorizer")

    # Create tools bound to this user_id and store
    tools = create_memory_tools(user_id=user_id, store=store)

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=MEMORIZER_SYSTEM_PROMPT,
    )
    return agent


def invoke_memorizer(
    messages: list[BaseMessage],
    user_id: str,
    store: BaseStore,
) -> dict:
    """Invoke the Memorizer agent to analyze conversation and update memory.

    The memorizer will:
    1. Analyze the conversation for new user information
    2. Check the current profile (if needed)
    3. Update profile fields or add observations (if warranted)
    4. Return summary of what was learned

    Args:
        messages: Conversation history to analyze
        user_id: User identifier for profile storage
        store: LangGraph Store for profile persistence

    Returns:
        Dict with:
        - 'memory_operations': List of memory operations performed
        - 'summary': Brief summary of what was learned (or "nothing new")
    """
    config = get_config()
    agent = build_memorizer(user_id=user_id, store=store)

    # Format conversation for analysis
    conversation_text = _format_conversation(messages)

    # Build the input message
    input_message = HumanMessage(
        content=f"Analyze this conversation and update the user profile if needed:\n\n{conversation_text}"
    )

    # Invoke the agent
    result = agent.invoke(
        {"messages": [input_message]},
        config={"recursion_limit": config.memorizer.recursion_limit},
    )

    # Extract memory operations from the message history
    result_messages = result.get("messages", [])
    memory_operations = []
    summary = "No new information to store."

    for msg in result_messages:
        if isinstance(msg, ToolMessage):
            memory_operations.append({
                "tool": msg.name,
                "result": msg.content,
                "tool_call_id": msg.tool_call_id,
            })

    # Get final agent response as summary
    for msg in reversed(result_messages):
        if hasattr(msg, "content") and msg.content and not isinstance(msg, ToolMessage):
            summary = msg.content
            break

    return {
        "memory_operations": memory_operations,
        "summary": summary,
    }


def _format_conversation(messages: list[BaseMessage]) -> str:
    """Format conversation messages for analysis."""
    parts = []
    for i, msg in enumerate(messages):
        role = getattr(msg, "type", "unknown")
        content = getattr(msg, "content", str(msg))
        parts.append(f"Turn {i + 1} [{role}]: {content}")
    return "\n".join(parts)