"""Memorize Extract node: LLM analyzes conversation to extract facts."""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.models import ExtractedFact, FactExtractionResult
from src.core.prompts import MEMORIZE_EXTRACT_PROMPT
from src.core.state import MemorizerState
from src.llm import get_llm

logger = logging.getLogger(__name__)


def memorize_extract_node(state: MemorizerState) -> dict:
    """Extract facts from conversation using LLM with structured output.

    Uses Pydantic structured output to get validated FactExtractionResult
    directly from the LLM. Falls back to manual JSON parsing if structured
    output fails.

    Returns:
        Dict with 'extracted_facts' list of ExtractedFact objects.
    """
    llm = get_llm("memorizer")

    # Format messages for the prompt
    messages_text = "\n".join(
        f"Turn {i+1} [{msg.type}]: {msg.content}"
        for i, msg in enumerate(state["messages"])
    )

    prompt = MEMORIZE_EXTRACT_PROMPT.format(messages=messages_text)
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Extract the facts as structured output."),
    ]

    # Try structured output first
    try:
        structured_llm = llm.with_structured_output(FactExtractionResult)
        result = structured_llm.invoke(messages)
        if result and isinstance(result, FactExtractionResult):
            logger.info(f"memorize_extract: structured output returned {len(result.facts)} facts")
            return {"extracted_facts": result.facts}
    except Exception as e:
        logger.warning(f"memorize_extract: structured output failed ({e}), falling back to manual parsing")

    # Fallback: invoke without structured output and parse manually
    response = llm.invoke(messages)
    facts = _parse_facts(response.content)
    return {"extracted_facts": facts}


def _parse_facts(content: str) -> list[ExtractedFact]:
    """Parse LLM output into ExtractedFact objects.

    Fallback parser for when structured output is unavailable.
    Handles malformed JSON gracefully by returning an empty list.
    """
    try:
        text = content.strip()
        # Strip markdown code fences
        if "```" in text:
            lines = text.split("\n")
            inside = False
            code_lines = []
            for line in lines:
                if line.strip().startswith("```"):
                    inside = not inside
                    continue
                if inside:
                    code_lines.append(line)
            if code_lines:
                text = "\n".join(code_lines)

        # Try direct parse
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [ExtractedFact.model_validate(item) for item in data]
        except json.JSONDecodeError:
            pass

        # Try to find a JSON array in the text
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            data = json.loads(text[start:end + 1])
            if isinstance(data, list):
                return [ExtractedFact.model_validate(item) for item in data]

        return []
    except (json.JSONDecodeError, ValueError):
        return []
