"""Tests for the Memorizer agent (learning subgraph)."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.core.models import Equipment, ExtractedFact, FactExtractionResult, Household, Preferences, UserProfile
from src.core.state import MemorizerState


@pytest.fixture
def memorizer_state():
    """A MemorizerState for testing the extract→apply→summarize flow."""
    return MemorizerState(
        messages=[
            HumanMessage(content="I just got a 10kW solar system installed."),
            AIMessage(content="That's great! A 10kW system will produce significant energy."),
            HumanMessage(content="I also switched to a heat pump for heating."),
            AIMessage(content="Heat pumps are very efficient. I'll update your profile."),
        ],
        user_profile=UserProfile(
            user_id="test_user",
            equipment=Equipment(
                solar_capacity_kw=5.0,
                heating_type="gas",
                updated_at=datetime(2024, 1, 1, 0, 0, 0),
            ),
            preferences=Preferences(updated_at=datetime(2024, 1, 1, 0, 0, 0)),
            household=Household(updated_at=datetime(2024, 1, 1, 0, 0, 0)),
        ),
        extracted_facts=[],
        validated_facts=[],
        summary=None,
        turns_to_summarize=[],
    )


class TestMemorizeExtractNode:
    """Tests for the fact extraction node."""

    @patch("src.nodes.memorize_extract.get_llm")
    def test_extracts_facts_from_conversation(self, mock_get_llm, memorizer_state):
        """Extract node identifies facts from conversation."""
        from src.nodes.memorize_extract import memorize_extract_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content=json.dumps([
            {
                "field": "equipment.solar_capacity_kw",
                "new_value": "10.0",
                "confidence": 0.95,
                "source_turn": 1,
                "source_text": "I just got a 10kW solar system installed."
            },
            {
                "field": "equipment.heating_type",
                "new_value": "heat_pump",
                "confidence": 0.9,
                "source_turn": 3,
                "source_text": "I also switched to a heat pump for heating."
            },
        ]))
        mock_get_llm.return_value = mock_llm

        result = memorize_extract_node(memorizer_state)
        assert len(result["extracted_facts"]) == 2
        assert result["extracted_facts"][0].field == "equipment.solar_capacity_kw"
        assert result["extracted_facts"][1].field == "equipment.heating_type"

    @patch("src.nodes.memorize_extract.get_llm")
    def test_handles_no_facts(self, mock_get_llm, memorizer_state):
        """Extract node returns empty list when no facts found."""
        from src.nodes.memorize_extract import memorize_extract_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="[]")
        mock_get_llm.return_value = mock_llm

        result = memorize_extract_node(memorizer_state)
        assert result["extracted_facts"] == []

    @patch("src.nodes.memorize_extract.get_llm")
    def test_handles_malformed_json(self, mock_get_llm, memorizer_state):
        """Extract node handles malformed LLM output gracefully."""
        from src.nodes.memorize_extract import memorize_extract_node

        mock_llm = MagicMock()
        # Structured output fails (returns non-FactExtractionResult)
        mock_llm.with_structured_output.return_value.invoke.return_value = None
        # Fallback returns invalid JSON
        mock_llm.invoke.return_value = AIMessage(content="not valid json")
        mock_get_llm.return_value = mock_llm

        result = memorize_extract_node(memorizer_state)
        assert result["extracted_facts"] == []

    @patch("src.nodes.memorize_extract.get_llm")
    def test_structured_output_path(self, mock_get_llm, memorizer_state):
        """Extract node uses structured output when available."""
        from src.nodes.memorize_extract import memorize_extract_node

        facts = [
            ExtractedFact(
                field="equipment.solar_capacity_kw",
                new_value="10.0",
                confidence=0.95,
                source_turn=1,
                source_text="I just got a 10kW solar system installed.",
            ),
        ]
        structured_result = FactExtractionResult(facts=facts)

        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = structured_result
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm

        result = memorize_extract_node(memorizer_state)
        assert len(result["extracted_facts"]) == 1
        assert result["extracted_facts"][0].field == "equipment.solar_capacity_kw"
        # Verify fallback invoke was NOT called
        mock_llm.invoke.assert_not_called()


class TestMemorizeApplyNode:
    """Tests for the fact application node."""

    def test_applies_high_confidence_facts(self, memorizer_state):
        """Apply node applies facts with confidence >= 0.7."""
        from src.nodes.memorize_apply import memorize_apply_node

        memorizer_state["extracted_facts"] = [
            ExtractedFact(
                field="equipment.solar_capacity_kw",
                new_value="10.0",
                confidence=0.95,
                source_turn=1,
                source_text="I just got a 10kW solar system installed.",
            ),
            ExtractedFact(
                field="equipment.heating_type",
                new_value="heat_pump",
                confidence=0.9,
                source_turn=3,
                source_text="I also switched to a heat pump for heating.",
            ),
        ]

        result = memorize_apply_node(memorizer_state)
        assert len(result["validated_facts"]) == 2
        assert result["user_profile"].equipment.solar_capacity_kw == 10.0
        assert result["user_profile"].equipment.heating_type == "heat_pump"

    def test_filters_low_confidence_facts(self, memorizer_state):
        """Apply node filters out facts with confidence < 0.7."""
        from src.nodes.memorize_apply import memorize_apply_node

        memorizer_state["extracted_facts"] = [
            ExtractedFact(
                field="equipment.solar_capacity_kw",
                new_value="10.0",
                confidence=0.95,
                source_turn=1,
                source_text="Got a 10kW system.",
            ),
            ExtractedFact(
                field="household.occupants",
                new_value="5",
                confidence=0.4,
                source_turn=2,
                source_text="Maybe around 5 people.",
            ),
        ]

        result = memorize_apply_node(memorizer_state)
        assert len(result["validated_facts"]) == 1
        assert result["validated_facts"][0].field == "equipment.solar_capacity_kw"

    def test_refreshes_section_timestamp(self, memorizer_state):
        """Apply node refreshes the section's updated_at timestamp."""
        from src.nodes.memorize_apply import memorize_apply_node

        old_ts = memorizer_state["user_profile"].equipment.updated_at
        memorizer_state["extracted_facts"] = [
            ExtractedFact(
                field="equipment.solar_capacity_kw",
                new_value="10.0",
                confidence=0.95,
                source_turn=1,
                source_text="Got a 10kW system.",
            ),
        ]

        result = memorize_apply_node(memorizer_state)
        assert result["user_profile"].equipment.updated_at > old_ts


class TestMemorizeSummarizeNode:
    """Tests for the summarization node."""

    @patch("src.nodes.memorize_summarize.get_llm")
    def test_summarizes_turns(self, mock_get_llm, memorizer_state):
        """Summarize node creates a summary of old turns."""
        from src.nodes.memorize_summarize import memorize_summarize_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="User upgraded solar to 10kW and switched to heat pump heating.")
        mock_get_llm.return_value = mock_llm

        memorizer_state["turns_to_summarize"] = [0, 1, 2, 3]

        result = memorize_summarize_node(memorizer_state)
        assert result["summary"] == "User upgraded solar to 10kW and switched to heat pump heating."

    @patch("src.nodes.memorize_summarize.get_llm")
    def test_no_turns_to_summarize(self, mock_get_llm, memorizer_state):
        """Summarize node skips when no turns to summarize."""
        from src.nodes.memorize_summarize import memorize_summarize_node

        memorizer_state["turns_to_summarize"] = []
        result = memorize_summarize_node(memorizer_state)
        assert result["summary"] is None
        mock_get_llm.assert_not_called()


class TestMemorizerGraph:
    """Integration tests for the full Memorizer subgraph."""

    @patch("src.nodes.memorize_summarize.get_llm")
    @patch("src.nodes.memorize_extract.get_llm")
    def test_full_memorizer_flow(self, mock_extract_llm, mock_summarize_llm, memorizer_state):
        """Test full Extract → Apply → Summarize flow."""
        from src.agents.memorizer import build_memorizer_graph

        # Mock extract LLM
        extract_llm = MagicMock()
        extract_llm.invoke.return_value = AIMessage(content=json.dumps([
            {
                "field": "equipment.solar_capacity_kw",
                "new_value": "10.0",
                "confidence": 0.95,
                "source_turn": 1,
                "source_text": "10kW solar system",
            },
        ]))
        mock_extract_llm.return_value = extract_llm

        # Mock summarize LLM
        summarize_llm = MagicMock()
        summarize_llm.invoke.return_value = AIMessage(content="User discussed solar upgrade.")
        mock_summarize_llm.return_value = summarize_llm

        graph = build_memorizer_graph()
        memorizer_state["turns_to_summarize"] = [0, 1]

        result = graph.invoke(memorizer_state)

        assert len(result["validated_facts"]) == 1
        assert result["user_profile"].equipment.solar_capacity_kw == 10.0
        assert result["summary"] == "User discussed solar upgrade."
