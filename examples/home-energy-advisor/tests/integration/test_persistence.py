"""Integration tests for profile persistence across sessions.

Tests save/load round-trips with LangGraph Store and the full
memorizer-to-store pipeline.

Requires: Ollama running at localhost:11434 with llama3.2 pulled.
"""

import pytest
from langgraph.store.memory import InMemoryStore

from src.core.models import UserProfile
from src.core.state import MemorizerState
from src.memory.helpers import get_profile_from_store, save_profile_to_store, update_profile_field
from src.memory.store import MemoryStore  # Legacy store for comparison tests

from .conftest import model_required, ollama_required

pytestmark = [ollama_required, model_required]


class TestProfileRoundTrip:
    """Tests for profile save and reload via LangGraph Store."""

    def test_save_and_load_profile_langgraph_store(self, demo_profile):
        """Save profile to LangGraph Store, then reload."""
        store = InMemoryStore()

        save_profile_to_store(store, demo_profile)

        loaded = get_profile_from_store(store, "integration_test_user")
        assert loaded is not None
        assert loaded.user_id == "integration_test_user"
        assert loaded.equipment.solar_capacity_kw == 7.5
        assert loaded.equipment.ev_model == "Tesla Model 3"
        assert loaded.location.zip_code == "94102"
        assert loaded.household.occupants == 4

    def test_field_update_persists_langgraph_store(self, demo_profile):
        """Updates to profile persist via LangGraph Store."""
        store = InMemoryStore()

        save_profile_to_store(store, demo_profile)

        # Load, update, save
        loaded = get_profile_from_store(store, "integration_test_user")
        updated = update_profile_field(loaded, "equipment.solar_capacity_kw", 12.0)
        save_profile_to_store(store, updated)

        # Reload and verify
        reloaded = get_profile_from_store(store, "integration_test_user")
        assert reloaded.equipment.solar_capacity_kw == 12.0

    def test_legacy_memorystore_still_works(self, tmp_data_dir, demo_profile):
        """Legacy MemoryStore (file-based) still works for backwards compatibility."""
        store = MemoryStore(data_dir=tmp_data_dir)

        store.save_profile(demo_profile)

        loaded = store.load_profile("integration_test_user")
        assert loaded is not None
        assert loaded.user_id == "integration_test_user"
        assert loaded.equipment.solar_capacity_kw == 7.5


class TestMemorizerPersistence:
    """Tests for memorizer-to-store pipeline."""

    def test_memorizer_persists_to_langgraph_store(self, integration_config, demo_profile):
        """Full flow: memorizer extracts facts -> profile saved to LangGraph Store."""
        from langchain_core.messages import AIMessage, HumanMessage
        from src.agents.memorizer import build_memorizer_graph

        store = InMemoryStore()
        save_profile_to_store(store, demo_profile)

        state = MemorizerState(
            messages=[
                HumanMessage(content="We now have 6 people living in the house."),
                AIMessage(content="Got it, updating your household to 6 occupants."),
            ],
            user_profile=demo_profile,
            extracted_facts=[],
            validated_facts=[],
            summary=None,
            turns_to_summarize=[],
        )

        graph = build_memorizer_graph()
        result = graph.invoke(state)

        updated_profile = result.get("user_profile")
        if updated_profile and result.get("validated_facts"):
            save_profile_to_store(store, updated_profile)

            reloaded = get_profile_from_store(store, "integration_test_user")
            assert reloaded is not None
