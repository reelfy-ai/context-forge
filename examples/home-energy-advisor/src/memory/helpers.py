"""Memory helpers for profile staleness checking and Store operations."""

from datetime import datetime
from typing import Any

from langgraph.store.base import BaseStore

from src.core.models import UserProfile

# Profile storage namespace for LangGraph Store
PROFILES_NAMESPACE = ("profiles",)

# Staleness threshold in days
STALENESS_THRESHOLD_DAYS = 90


def get_profile_from_store(store: BaseStore, user_id: str) -> UserProfile | None:
    """Load a user profile from LangGraph Store.

    Args:
        store: LangGraph BaseStore instance
        user_id: User identifier

    Returns:
        UserProfile if found, None otherwise
    """
    namespace = (*PROFILES_NAMESPACE, user_id)
    items = list(store.search(namespace))

    if not items:
        return None

    # Get the profile data from the first item
    profile_data = items[0].value
    return UserProfile.model_validate(profile_data)


def save_profile_to_store(store: BaseStore, profile: UserProfile) -> None:
    """Save a user profile to LangGraph Store.

    Args:
        store: LangGraph BaseStore instance
        profile: UserProfile to save
    """
    namespace = (*PROFILES_NAMESPACE, profile.user_id)
    store.put(namespace, "profile", profile.model_dump(mode="json"))


def get_section_staleness(profile: UserProfile, section_name: str) -> dict:
    """Calculate staleness of a profile section.

    Args:
        profile: UserProfile to check
        section_name: One of "equipment", "preferences", "household"

    Returns:
        Dict with 'days_old' (float) and 'is_stale' (bool, True if > threshold days)
    """
    section = getattr(profile, section_name, None)
    if section is None or not hasattr(section, "updated_at"):
        return {"days_old": 0, "is_stale": False}

    now = datetime.now(tz=None)
    updated_at = section.updated_at

    # Handle timezone-aware vs naive datetimes
    if updated_at.tzinfo is not None:
        updated_at = updated_at.replace(tzinfo=None)

    delta = now - updated_at
    days_old = delta.total_seconds() / 86400

    return {
        "days_old": days_old,
        "is_stale": days_old >= STALENESS_THRESHOLD_DAYS,
    }


def get_all_stale_sections(profile: UserProfile) -> list[str]:
    """Get list of all stale sections in a profile.

    Args:
        profile: UserProfile to check

    Returns:
        List of section names that are stale
    """
    stale_sections = []
    for section_name in ["equipment", "preferences", "household"]:
        staleness = get_section_staleness(profile, section_name)
        if staleness["is_stale"]:
            stale_sections.append(section_name)
    return stale_sections


def update_profile_field(profile: UserProfile, field_path: str, value: Any) -> UserProfile:
    """Update a field in a UserProfile and return the updated profile.

    Args:
        profile: UserProfile to update (will be modified in place)
        field_path: Dotted path like "equipment.solar_capacity_kw"
        value: New value to set

    Returns:
        The updated UserProfile
    """
    parts = field_path.split(".")

    if len(parts) == 2:
        section_name, field_name = parts
        section = getattr(profile, section_name, None)
        if section is not None:
            setattr(section, field_name, value)
            # Refresh section timestamp
            if hasattr(section, "updated_at"):
                section.updated_at = datetime.now(tz=None)
    elif len(parts) == 1:
        setattr(profile, parts[0], value)

    profile.updated_at = datetime.now(tz=None)
    return profile
