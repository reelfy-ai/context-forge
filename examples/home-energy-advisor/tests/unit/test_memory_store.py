"""Unit tests for the MemoryStore persistence layer."""

import json
import os
import tempfile
from datetime import datetime, timedelta

import pytest

from src.core.models import (
    Equipment,
    Household,
    Location,
    Preferences,
    ProfileNote,
    UserProfile,
)
from src.memory.store import MemoryStore


@pytest.fixture
def tmp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def store(tmp_data_dir):
    """Create a MemoryStore with a temporary directory."""
    return MemoryStore(data_dir=tmp_data_dir)


@pytest.fixture
def sample_profile():
    """A sample UserProfile for testing."""
    return UserProfile(
        user_id="user_42",
        equipment=Equipment(
            solar_capacity_kw=5.0,
            ev_model="Chevy Bolt",
            ev_battery_kwh=66.0,
            updated_at=datetime(2024, 6, 1, 12, 0, 0),
        ),
        preferences=Preferences(
            budget_priority="high",
            comfort_priority="medium",
            green_priority="low",
            updated_at=datetime(2024, 6, 1, 12, 0, 0),
        ),
        household=Household(
            work_schedule="9-5 weekdays",
            occupants=3,
            typical_usage_pattern="evening_heavy",
            updated_at=datetime(2024, 1, 1, 12, 0, 0),  # Intentionally stale
        ),
        location=Location(
            zip_code="90210",
            utility_provider="SCE",
            rate_schedule="TOU-D-PRIME",
        ),
        created_at=datetime(2024, 1, 1, 0, 0, 0),
        updated_at=datetime(2024, 6, 1, 12, 0, 0),
    )


class TestLoadProfile:
    """Tests for MemoryStore.load_profile."""

    def test_load_nonexistent_returns_none(self, store):
        """Loading a profile that doesn't exist returns None."""
        result = store.load_profile("nonexistent_user")
        assert result is None

    def test_load_existing_profile(self, store, sample_profile):
        """Loading a saved profile returns the correct UserProfile."""
        store.save_profile(sample_profile)
        loaded = store.load_profile("user_42")
        assert loaded is not None
        assert loaded.user_id == "user_42"
        assert loaded.equipment.solar_capacity_kw == 5.0
        assert loaded.equipment.ev_model == "Chevy Bolt"
        assert loaded.location.zip_code == "90210"

    def test_load_preserves_timestamps(self, store, sample_profile):
        """Loading preserves the original timestamps."""
        store.save_profile(sample_profile)
        loaded = store.load_profile("user_42")
        assert loaded.equipment.updated_at == datetime(2024, 6, 1, 12, 0, 0)
        assert loaded.household.updated_at == datetime(2024, 1, 1, 12, 0, 0)


class TestSaveProfile:
    """Tests for MemoryStore.save_profile."""

    def test_save_creates_file(self, store, sample_profile, tmp_data_dir):
        """Saving a profile creates a JSON file."""
        store.save_profile(sample_profile)
        profile_path = os.path.join(tmp_data_dir, "profiles", "user_42.json")
        assert os.path.exists(profile_path)

    def test_save_writes_valid_json(self, store, sample_profile, tmp_data_dir):
        """Saved file contains valid JSON."""
        store.save_profile(sample_profile)
        profile_path = os.path.join(tmp_data_dir, "profiles", "user_42.json")
        with open(profile_path) as f:
            data = json.load(f)
        assert data["user_id"] == "user_42"

    def test_save_overwrites_existing(self, store, sample_profile):
        """Saving again overwrites the previous profile."""
        store.save_profile(sample_profile)
        sample_profile.equipment.solar_capacity_kw = 10.0
        store.save_profile(sample_profile)
        loaded = store.load_profile("user_42")
        assert loaded.equipment.solar_capacity_kw == 10.0

    def test_save_creates_profiles_directory(self, tmp_data_dir):
        """Save creates profiles/ subdirectory if it doesn't exist."""
        store = MemoryStore(data_dir=tmp_data_dir)
        profile = UserProfile(user_id="new_user")
        store.save_profile(profile)
        assert os.path.isdir(os.path.join(tmp_data_dir, "profiles"))


class TestUpdateField:
    """Tests for MemoryStore.update_field."""

    def test_update_existing_field(self, store, sample_profile):
        """Updating an existing field changes its value."""
        store.save_profile(sample_profile)
        store.update_field("user_42", "equipment.solar_capacity_kw", 12.0)
        loaded = store.load_profile("user_42")
        assert loaded.equipment.solar_capacity_kw == 12.0

    def test_update_refreshes_section_timestamp(self, store, sample_profile):
        """Updating a field refreshes the section's updated_at."""
        store.save_profile(sample_profile)
        old_ts = sample_profile.equipment.updated_at
        store.update_field("user_42", "equipment.ev_model", "Tesla Model Y")
        loaded = store.load_profile("user_42")
        assert loaded.equipment.updated_at > old_ts

    def test_update_nonexistent_profile_raises(self, store):
        """Updating a nonexistent profile raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            store.update_field("ghost_user", "equipment.ev_model", "Bolt")

    def test_update_nested_field(self, store, sample_profile):
        """Updating a household field works correctly."""
        store.save_profile(sample_profile)
        store.update_field("user_42", "household.occupants", 5)
        loaded = store.load_profile("user_42")
        assert loaded.household.occupants == 5


class TestFieldStaleness:
    """Tests for MemoryStore.get_field_staleness."""

    def test_fresh_field(self, store, sample_profile):
        """Recently updated field is not stale."""
        sample_profile.equipment.updated_at = datetime.now(tz=None)
        store.save_profile(sample_profile)
        result = store.get_field_staleness("user_42", "equipment")
        assert result["is_stale"] is False
        assert result["days_old"] < 1

    def test_stale_field_over_90_days(self, store, sample_profile):
        """Field older than 90 days is marked stale."""
        sample_profile.household.updated_at = datetime.now(tz=None) - timedelta(days=100)
        store.save_profile(sample_profile)
        result = store.get_field_staleness("user_42", "household")
        assert result["is_stale"] is True
        assert result["days_old"] >= 100

    def test_staleness_nonexistent_user(self, store):
        """Staleness check on nonexistent user raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            store.get_field_staleness("ghost", "equipment")

    def test_staleness_threshold(self, store, sample_profile):
        """Field at exactly 90 days is marked stale."""
        sample_profile.equipment.updated_at = datetime.now(tz=None) - timedelta(days=90)
        store.save_profile(sample_profile)
        result = store.get_field_staleness("user_42", "equipment")
        assert result["is_stale"] is True


class TestSessionManagement:
    """Tests for session message management."""

    def test_append_and_get_messages(self, store):
        """Append messages and retrieve them."""
        store.append_message("session_1", {"role": "user", "content": "Hello"})
        store.append_message("session_1", {"role": "assistant", "content": "Hi!"})
        messages = store.get_session_messages("session_1")
        assert len(messages) == 2
        assert messages[0]["content"] == "Hello"
        assert messages[1]["content"] == "Hi!"

    def test_get_empty_session(self, store):
        """Getting messages from nonexistent session returns empty list."""
        messages = store.get_session_messages("nonexistent")
        assert messages == []

    def test_clear_session(self, store):
        """Clearing a session removes all messages."""
        store.append_message("session_1", {"role": "user", "content": "test"})
        store.clear_session("session_1")
        messages = store.get_session_messages("session_1")
        assert messages == []

    def test_multiple_sessions_independent(self, store):
        """Messages from different sessions don't interfere."""
        store.append_message("sess_a", {"role": "user", "content": "A"})
        store.append_message("sess_b", {"role": "user", "content": "B"})
        assert len(store.get_session_messages("sess_a")) == 1
        assert store.get_session_messages("sess_a")[0]["content"] == "A"
        assert store.get_session_messages("sess_b")[0]["content"] == "B"
