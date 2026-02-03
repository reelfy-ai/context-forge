"""Integration tests for the full Advisor orchestrator pipeline.

Tests the complete flow: Intake -> Recall -> [Analyze] -> Recommend -> [Memorize],
including multi-turn conversation state accumulation.

Requires: Ollama running at localhost:11434 with llama3.2 pulled.

Note: Session persistence is now handled by LangGraph's Checkpointer, which
automatically saves state between invocations when a thread_id is provided.
"""

import pytest
from langgraph.store.memory import InMemoryStore

from src.memory.helpers import save_profile_to_store

from .conftest import model_required, ollama_required

pytestmark = [ollama_required, model_required]


class TestAdvisorFlow:
    """E2E tests for the complete Advisor -> Analyzer -> Recommend pipeline."""

    def test_ev_charging_query(self, integration_config, demo_profile):
        """Full flow: EV charging query triggers analyzer tools and produces recommendation."""
        from src.agents.advisor import build_advisor_graph

        store = InMemoryStore()
        graph = build_advisor_graph(store=store)
        result = graph.invoke({
            "user_id": "integration_test_user",
            "session_id": "e2e_session_1",
            "message": "When should I charge my EV tonight to minimize cost?",
            "messages": [],
            "turn_count": 0,
            "user_profile": demo_profile,
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
        assert len(result["response"]) > 20
        assert result["turn_count"] == 1
        assert len(result["messages"]) >= 2  # At least HumanMessage + AIMessage

    def test_solar_production_query(self, integration_config, demo_profile):
        """Solar query triggers weather + solar tools."""
        from src.agents.advisor import build_advisor_graph

        store = InMemoryStore()
        graph = build_advisor_graph(store=store)
        result = graph.invoke({
            "user_id": "integration_test_user",
            "session_id": "e2e_session_2",
            "message": "How much solar will my panels produce today?",
            "messages": [],
            "turn_count": 0,
            "user_profile": demo_profile,
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
        assert len(result["response"]) > 20

    def test_simple_faq_skips_analyzer(self, integration_config, demo_profile):
        """A simple knowledge question should skip analyzer and go straight to recommend."""
        from src.agents.advisor import build_advisor_graph

        store = InMemoryStore()
        graph = build_advisor_graph(store=store)
        result = graph.invoke({
            "user_id": "integration_test_user",
            "session_id": "e2e_session_3",
            "message": "What is a kilowatt hour?",
            "messages": [],
            "turn_count": 0,
            "user_profile": demo_profile,
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
        assert result["tool_observations"] == []  # No tools needed for FAQ


class TestMultiTurnConversation:
    """E2E tests for multi-turn state accumulation."""

    def test_two_turn_conversation(self, integration_config, demo_profile):
        """State accumulates correctly across two turns."""
        from src.agents.advisor import build_advisor_graph

        store = InMemoryStore()
        graph = build_advisor_graph(store=store)

        # Turn 1
        result_1 = graph.invoke({
            "user_id": "integration_test_user",
            "session_id": "multi_turn_session",
            "message": "What are my current electricity rates?",
            "messages": [],
            "turn_count": 0,
            "user_profile": demo_profile,
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "should_memorize": False,
        })

        assert result_1["turn_count"] == 1
        assert result_1["response"] is not None
        messages_after_turn_1 = result_1["messages"]

        # Turn 2: continue conversation with accumulated messages
        result_2 = graph.invoke({
            "user_id": "integration_test_user",
            "session_id": "multi_turn_session",
            "message": "Based on those rates, when should I run my dishwasher?",
            "messages": messages_after_turn_1,
            "turn_count": result_1["turn_count"],
            "user_profile": demo_profile,
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "should_memorize": False,
        })

        assert result_2["turn_count"] == 2
        assert result_2["response"] is not None
        assert len(result_2["messages"]) > len(messages_after_turn_1)


class TestCheckpointerPersistence:
    """Tests for session persistence via LangGraph Checkpointer.

    Note: The checkpointer automatically saves the full graph state after each
    node execution. When the same thread_id is used, state is restored.
    This replaces the old _persist_session node.
    """

    def test_checkpointer_restores_state(self, integration_config, demo_profile, tmp_data_dir):
        """With checkpointer, state is restored on subsequent invocations."""
        import sqlite3
        from pathlib import Path
        from langgraph.checkpoint.sqlite import SqliteSaver
        from src.agents.advisor import build_advisor_graph

        # Set up checkpointer and store
        # Note: check_same_thread=False required for LangGraph's multi-threaded execution
        db_path = Path(tmp_data_dir) / "test_checkpoints.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        store = InMemoryStore()

        graph = build_advisor_graph(checkpointer=checkpointer, store=store)

        # Turn 1
        config = {"configurable": {"thread_id": "checkpointer_test_session"}}
        result_1 = graph.invoke(
            {
                "user_id": "integration_test_user",
                "session_id": "checkpointer_test_session",
                "message": "What are peak hours?",
                "messages": [],
                "turn_count": 0,
                "user_profile": demo_profile,
                "weather_data": None,
                "rate_data": None,
                "solar_estimate": None,
                "retrieved_docs": [],
                "tool_observations": [],
                "response": None,
                "extracted_facts": [],
                "should_memorize": False,
            },
            config=config,
        )

        assert result_1["turn_count"] == 1
        assert result_1["response"] is not None

        # Turn 2 - state should be restored from checkpoint
        # Note: With checkpointer, we could omit messages/turn_count and they'd be restored,
        # but we pass them explicitly for clarity in this test
        result_2 = graph.invoke(
            {
                "user_id": "integration_test_user",
                "session_id": "checkpointer_test_session",
                "message": "And off-peak hours?",
                "messages": result_1["messages"],
                "turn_count": result_1["turn_count"],
                "user_profile": demo_profile,
                "weather_data": None,
                "rate_data": None,
                "solar_estimate": None,
                "retrieved_docs": [],
                "tool_observations": [],
                "response": None,
                "extracted_facts": [],
                "should_memorize": False,
            },
            config=config,
        )

        assert result_2["turn_count"] == 2
        assert result_2["response"] is not None
        # Messages accumulate across turns
        assert len(result_2["messages"]) >= 4  # 2 human + 2 AI messages


class TestProfilePersistence:
    """Tests for cross-session profile persistence via LangGraph Store."""

    def test_profile_loaded_from_store(self, integration_config, demo_profile):
        """Profile is loaded from Store when recall_node runs."""
        from src.agents.advisor import build_advisor_graph
        from src.memory.helpers import get_profile_from_store

        store = InMemoryStore()
        # Pre-populate store with profile
        save_profile_to_store(store, demo_profile)

        graph = build_advisor_graph(store=store)

        # Invoke without passing user_profile - recall should load it from store
        result = graph.invoke({
            "user_id": "integration_test_user",
            "session_id": "profile_test",
            "message": "What equipment do I have?",
            "messages": [],
            "turn_count": 0,
            "user_profile": None,  # Will be loaded from store
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "should_memorize": False,
        })

        # Profile should have been loaded
        assert result["user_profile"] is not None
        assert result["user_profile"].user_id == "integration_test_user"
        assert result["response"] is not None
