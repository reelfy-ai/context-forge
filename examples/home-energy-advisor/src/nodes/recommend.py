"""Recommend node: generates final response using all context."""

import json

from langchain_core.messages import AIMessage, SystemMessage

from src.core.prompts import ADVISOR_SYSTEM_PROMPT
from src.core.state import AdvisorState
from src.llm import get_llm


def _build_context_message(state: AdvisorState) -> str:
    """Build a context string from profile, tool observations, and retrieved docs."""
    parts = []

    profile = state.get("user_profile")
    if profile:
        parts.append("User Profile:")
        if profile.location:
            parts.append(f"  Location: {profile.location.zip_code}, Utility: {profile.location.utility_provider}, Rate: {profile.location.rate_schedule}")
        if profile.equipment:
            equip = profile.equipment
            if equip.solar_capacity_kw:
                parts.append(f"  Solar: {equip.solar_capacity_kw} kW")
            if equip.ev_model:
                parts.append(f"  EV: {equip.ev_model} ({equip.ev_battery_kwh} kWh)")
            if equip.has_battery_storage:
                parts.append(f"  Battery Storage: {equip.battery_capacity_kwh} kWh")
        if profile.preferences:
            prefs = profile.preferences
            parts.append(f"  Priorities: budget={prefs.budget_priority}, comfort={prefs.comfort_priority}, green={prefs.green_priority}")
        if profile.household:
            hh = profile.household
            parts.append(f"  Household: {hh.occupants} occupants, schedule={hh.work_schedule}, usage={hh.typical_usage_pattern}")

    tool_obs = state.get("tool_observations", [])
    if tool_obs:
        parts.append("\nTool Observations:")
        for obs in tool_obs:
            parts.append(f"  [{obs.get('tool', 'unknown')}]: {json.dumps(obs.get('result', {}))}")

    retrieved = state.get("retrieved_docs", [])
    if retrieved:
        parts.append("\nRelevant Knowledge:")
        for doc in retrieved:
            parts.append(f"  [{doc.source}] (score={doc.score:.2f}): {doc.text[:200]}")

    return "\n".join(parts)


def recommend_node(state: AdvisorState) -> dict:
    """Generate a recommendation using the LLM with all available context.

    Assembles system prompt + context + conversation history, then invokes LLM.
    """
    llm = get_llm("advisor")

    context = _build_context_message(state)
    system_content = ADVISOR_SYSTEM_PROMPT
    if context:
        system_content += f"\n\nCurrent Context:\n{context}"

    messages = [SystemMessage(content=system_content)] + list(state["messages"])
    response = llm.invoke(messages)

    return {
        "response": response.content,
        "messages": [AIMessage(content=response.content)],
    }
