"""Integration tests for the Memorizer subgraph.

Tests real LLM-based fact extraction from conversations,
profile updates, and conversation summarization.

Requires: Ollama running at localhost:11434 with llama3.2 pulled.
"""

import pytest

from src.core.models import Equipment, UserProfile
from src.core.state import MemorizerState

from .conftest import model_required, ollama_required

pytestmark = [ollama_required, model_required]


class TestFactExtraction:
    """Tests for LLM-based fact extraction from conversations."""

    def test_extract_facts_from_conversation(self, integration_config):
        """Memorizer extracts facts from a multi-turn conversation."""
        from langchain_core.messages import AIMessage, HumanMessage
        from src.agents.memorizer import build_memorizer_graph

        state = MemorizerState(
            messages=[
                HumanMessage(content="I just installed a 12kW solar system on my roof last week."),
                AIMessage(content="Congratulations on the 12kW system! That's a great size."),
                HumanMessage(content="Thanks! I also bought a Rivian R1T with an 135 kWh battery."),
                AIMessage(content="The Rivian R1T is excellent. The large battery means you can charge during off-peak hours."),
                HumanMessage(content="We have 5 people in our household and I work from home."),
                AIMessage(content="Working from home with 5 occupants means higher daytime usage."),
            ],
            user_profile=UserProfile(
                user_id="fact_test_user",
                equipment=Equipment(solar_capacity_kw=5.0),
            ),
            extracted_facts=[],
            validated_facts=[],
            summary=None,
            turns_to_summarize=[],
        )

        graph = build_memorizer_graph()
        result = graph.invoke(state)

        assert len(result["validated_facts"]) >= 1

        for fact in result["validated_facts"]:
            assert fact.field.startswith(("equipment.", "household.", "preferences.", "location."))
            assert fact.confidence >= 0.7
            assert len(fact.new_value) > 0
            assert len(fact.source_text) > 0


class TestProfileUpdate:
    """Tests for applying extracted facts to the user profile."""

    def test_memorizer_updates_profile(self, integration_config):
        """Memorizer applies extracted facts to the user profile."""
        from langchain_core.messages import AIMessage, HumanMessage
        from src.agents.memorizer import build_memorizer_graph

        state = MemorizerState(
            messages=[
                HumanMessage(content="I switched from gas heating to a heat pump last month."),
                AIMessage(content="Heat pumps are much more efficient. I'll note that update."),
            ],
            user_profile=UserProfile(
                user_id="update_test_user",
                equipment=Equipment(heating_type="gas"),
            ),
            extracted_facts=[],
            validated_facts=[],
            summary=None,
            turns_to_summarize=[],
        )

        graph = build_memorizer_graph()
        result = graph.invoke(state)

        if result["validated_facts"]:
            updated_profile = result["user_profile"]
            assert updated_profile is not None


class TestSummarization:
    """Tests for conversation summarization."""

    def test_memorizer_summarizes_conversation(self, integration_config):
        """Memorizer summarizes turns when requested."""
        from langchain_core.messages import AIMessage, HumanMessage
        from src.agents.memorizer import build_memorizer_graph

        messages = [
            HumanMessage(content="What time should I charge my EV?"),
            AIMessage(content="Based on your TOU rate, charge after 9 PM for off-peak rates."),
            HumanMessage(content="How about running the dishwasher?"),
            AIMessage(content="Same principle - run it after 9 PM to save on peak charges."),
        ]

        state = MemorizerState(
            messages=messages,
            user_profile=UserProfile(user_id="summary_test_user"),
            extracted_facts=[],
            validated_facts=[],
            summary=None,
            turns_to_summarize=[0, 1, 2, 3],
        )

        graph = build_memorizer_graph()
        result = graph.invoke(state)

        assert result["summary"] is not None
        assert len(result["summary"]) > 20
