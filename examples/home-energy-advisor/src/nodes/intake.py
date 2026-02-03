"""Intake node: parses user input and updates message history."""

from langchain_core.messages import HumanMessage

from src.core.state import AdvisorState


def intake_node(state: AdvisorState) -> dict:
    """Parse the user message and append to conversation history.

    - Wraps raw message text as a HumanMessage
    - Increments turn count
    """
    user_message = HumanMessage(content=state["message"])

    return {
        "messages": [user_message],
        "turn_count": state["turn_count"] + 1,
    }
