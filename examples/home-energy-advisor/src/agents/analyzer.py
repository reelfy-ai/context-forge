"""Analyzer agent: ReAct tool-calling using create_react_agent."""

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from src.config import get_config
from src.core.prompts import ANALYZER_SYSTEM_PROMPT
from src.llm import get_llm


def build_analyzer(tools: list | None = None) -> Any:
    """Build the Analyzer agent using LangGraph's create_react_agent.

    Args:
        tools: List of @tool-decorated functions for the agent to use.

    Returns:
        A compiled LangGraph Runnable implementing the ReAct pattern.
    """
    if tools is None:
        tools = []

    llm = get_llm("analyzer")
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=ANALYZER_SYSTEM_PROMPT,
    )
    return agent


def invoke_analyzer(
    query: str,
    tools: list | None = None,
    context: dict | None = None,
) -> dict:
    """Invoke the Analyzer agent and extract tool observations.

    Args:
        query: The user's question to analyze.
        tools: List of @tool-decorated functions.
        context: Additional context (profile, retrieved docs) to include in the query.

    Returns:
        Dict with 'messages' (list[BaseMessage]) and 'tool_observations' (list[dict]).
    """
    config = get_config()

    agent = build_analyzer(tools=tools)

    # Build the input message with context
    input_text = query
    if context:
        context_str = "\n".join(f"{k}: {v}" for k, v in context.items() if v)
        if context_str:
            input_text = f"Context:\n{context_str}\n\nQuestion: {query}"

    result = agent.invoke(
        {"messages": [HumanMessage(content=input_text)]},
        config={"recursion_limit": config.analyzer.recursion_limit},
    )

    # Extract tool observations from the message history
    messages = result.get("messages", [])
    tool_observations = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_observations.append({
                "tool": msg.name,
                "result": msg.content,
                "tool_call_id": msg.tool_call_id,
            })

    return {
        "messages": messages,
        "tool_observations": tool_observations,
    }
