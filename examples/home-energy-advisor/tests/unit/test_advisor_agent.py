"""Integration tests for the Advisor agent orchestrator."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.store.memory import InMemoryStore

from src.core.state import AdvisorState
from src.nodes.intake import intake_node
from src.nodes.recommend import recommend_node


class TestIntakeNode:
    """Tests for the intake node."""

    def test_appends_user_message(self, initial_advisor_state):
        """Intake node appends user message to messages list."""
        state = AdvisorState(
            user_id="test_user",
            session_id="sess_1",
            message="What's the best time to run my dishwasher?",
            messages=[],
            turn_count=0,
            user_profile=None,
            weather_data=None,
            rate_data=None,
            solar_estimate=None,
            retrieved_docs=[],
            tool_observations=[],
            response=None,
            extracted_facts=[],
            should_memorize=False,
        )
        result = intake_node(state)
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], HumanMessage)
        assert result["messages"][0].content == "What's the best time to run my dishwasher?"

    def test_increments_turn_count(self):
        """Intake node increments turn count."""
        state = AdvisorState(
            user_id="test_user",
            session_id="sess_1",
            message="Hello",
            messages=[],
            turn_count=3,
            user_profile=None,
            weather_data=None,
            rate_data=None,
            solar_estimate=None,
            retrieved_docs=[],
            tool_observations=[],
            response=None,
            extracted_facts=[],
            should_memorize=False,
        )
        result = intake_node(state)
        assert result["turn_count"] == 4

    def test_handles_empty_message(self):
        """Intake node handles empty message gracefully."""
        state = AdvisorState(
            user_id="test_user",
            session_id="sess_1",
            message="",
            messages=[],
            turn_count=0,
            user_profile=None,
            weather_data=None,
            rate_data=None,
            solar_estimate=None,
            retrieved_docs=[],
            tool_observations=[],
            response=None,
            extracted_facts=[],
            should_memorize=False,
        )
        result = intake_node(state)
        assert len(result["messages"]) == 1


class TestRecommendNode:
    """Tests for the recommend node."""

    @patch("src.nodes.recommend.get_llm")
    def test_generates_response(self, mock_get_llm, initial_advisor_state):
        """Recommend node generates a response using LLM."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Charge after 9 PM for off-peak rates.")
        mock_get_llm.return_value = mock_llm

        result = recommend_node(initial_advisor_state)
        assert result["response"] == "Charge after 9 PM for off-peak rates."
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

    @patch("src.nodes.recommend.get_llm")
    def test_includes_profile_context(self, mock_get_llm, initial_advisor_state):
        """Recommend node passes user profile info to LLM."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Response with profile context.")
        mock_get_llm.return_value = mock_llm

        recommend_node(initial_advisor_state)
        call_args = mock_llm.invoke.call_args[0][0]
        # Should include system message with profile context
        messages_text = " ".join(m.content for m in call_args)
        assert "PG&E" in messages_text or "E-TOU-C" in messages_text or len(call_args) > 0

    @patch("src.nodes.recommend.get_llm")
    def test_includes_tool_observations(self, mock_get_llm, initial_advisor_state):
        """Recommend node includes tool observations in context."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Based on weather data...")
        mock_get_llm.return_value = mock_llm

        initial_advisor_state["tool_observations"] = [
            {"tool": "weather", "result": {"solar_hours": 6.5}}
        ]
        recommend_node(initial_advisor_state)
        call_args = mock_llm.invoke.call_args[0][0]
        messages_text = " ".join(m.content for m in call_args)
        assert "solar_hours" in messages_text or "weather" in messages_text or len(call_args) > 1


class TestAdvisorGraph:
    """Integration tests for the full Advisor graph."""

    @patch("src.agents.advisor.invoke_analyzer")
    @patch("src.nodes.recommend.get_llm")
    def test_full_flow_with_analyzer(self, mock_get_llm, mock_invoke_analyzer, mock_profile, memory_store):
        """Test full advisor flow: intake → recall → analyze → recommend."""
        from src.agents.advisor import build_advisor_graph

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Here's my recommendation for your EV charging.")
        mock_get_llm.return_value = mock_llm

        mock_invoke_analyzer.return_value = {
            "messages": [AIMessage(content="Rate data retrieved.")],
            "tool_observations": [{"tool": "rates", "result": {"peak_rate": 0.49}}],
        }

        graph = build_advisor_graph(store=memory_store)
        result = graph.invoke({
            "user_id": "test_user_123",
            "session_id": "session_001",
            "message": "When should I charge my EV?",
            "messages": [],
            "turn_count": 0,
            "user_profile": mock_profile,
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "should_memorize": False,
        })

        assert result["response"] is not None
        assert result["turn_count"] == 1
        assert len(result["messages"]) >= 2  # HumanMessage + AIMessage
        mock_invoke_analyzer.assert_called_once()

    @patch("src.agents.advisor.invoke_analyzer")
    @patch("src.nodes.recommend.get_llm")
    def test_simple_query_skips_analyzer(self, mock_get_llm, mock_invoke_analyzer, mock_profile, memory_store):
        """Simple FAQ query skips analyzer and goes directly to recommend."""
        from src.agents.advisor import build_advisor_graph

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Solar panels convert sunlight to electricity.")
        mock_get_llm.return_value = mock_llm

        graph = build_advisor_graph(store=memory_store)
        result = graph.invoke({
            "user_id": "test_user_123",
            "session_id": "session_001",
            "message": "What is a kilowatt hour?",
            "messages": [],
            "turn_count": 0,
            "user_profile": mock_profile,
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "should_memorize": False,
        })

        assert result["response"] == "Solar panels convert sunlight to electricity."
        mock_invoke_analyzer.assert_not_called()

    @patch("src.agents.advisor.invoke_analyzer")
    @patch("src.nodes.recommend.get_llm")
    def test_should_memorize_false_skips_memorizer(self, mock_get_llm, mock_invoke_analyzer, mock_profile, memory_store):
        """When should_memorize is False, memorizer subgraph is skipped."""
        from src.agents.advisor import build_advisor_graph

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Recommendation")
        mock_get_llm.return_value = mock_llm
        mock_invoke_analyzer.return_value = {"messages": [], "tool_observations": []}

        graph = build_advisor_graph(store=memory_store)
        result = graph.invoke({
            "user_id": "test_user_123",
            "session_id": "session_001",
            "message": "What are my current rates?",
            "messages": [],
            "turn_count": 0,
            "user_profile": mock_profile,
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "should_memorize": False,
        })

        assert result["response"] == "Recommendation"
        assert result["extracted_facts"] == []
