"""Memorize Summarize node: compresses old conversation turns into a summary."""

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.prompts import MEMORIZE_SUMMARIZE_PROMPT
from src.core.state import MemorizerState
from src.llm import get_llm


def memorize_summarize_node(state: MemorizerState) -> dict:
    """Summarize old conversation turns into a concise paragraph.

    Only runs if there are turns to summarize (typically turns > 20).
    Appends the summary as a ProfileNote on the user profile.

    Returns:
        Dict with 'summary' string (or None if nothing to summarize).
    """
    turns_to_summarize = state.get("turns_to_summarize", [])

    if not turns_to_summarize:
        return {"summary": None}

    llm = get_llm("memorizer")

    # Format the turns for summarization
    messages = state["messages"]
    turns_text = "\n".join(
        f"Turn {idx+1} [{messages[idx].type}]: {messages[idx].content}"
        for idx in turns_to_summarize
        if idx < len(messages)
    )

    prompt = MEMORIZE_SUMMARIZE_PROMPT.format(turns=turns_text)
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="Provide the summary."),
    ])

    return {"summary": response.content}
