"""Memory tools for the Memorizer agent.

These tools allow the LLM to decide what to remember about the user,
updating the profile in the LangGraph Store.

The memorizer evaluates importance internally - it may decide nothing
is worth remembering and return without calling any tools.
"""

from datetime import datetime

from langchain_core.tools import tool
from langgraph.store.base import BaseStore

from src.core.models import (
    Equipment,
    Household,
    Location,
    Preferences,
    ProfileNote,
    UserProfile,
)
from src.memory.helpers import (
    get_profile_from_store,
    save_profile_to_store,
)


def create_memory_tools(user_id: str, store: BaseStore) -> list:
    """Create memory tools with user_id and store bound.

    This factory pattern allows the tools to access the store and user_id
    without using global state or complex injection patterns.

    Args:
        user_id: User identifier for profile storage
        store: LangGraph Store for profile persistence

    Returns:
        List of tools bound to this user_id and store
    """

    @tool
    def update_profile_field(field: str, value: str, reason: str) -> str:
        """Update a field in the user's profile.

        Use this when you learn something NEW about the user that should be remembered.
        Only call this for information that is:
        - Explicitly stated by the user (not inferred)
        - Different from what's already stored
        - Useful for future energy advice

        Args:
            field: The field to update in dotted notation. Examples:
                   - "equipment.solar_capacity_kw" (number, e.g., "7.5")
                   - "equipment.ev_model" (string, e.g., "Tesla Model 3")
                   - "equipment.ev_battery_kwh" (number, e.g., "75")
                   - "equipment.heating_type" (string, e.g., "heat_pump", "gas")
                   - "preferences.budget_priority" (low/medium/high)
                   - "preferences.comfort_priority" (low/medium/high)
                   - "preferences.green_priority" (low/medium/high)
                   - "household.occupants" (integer)
                   - "household.work_schedule" (e.g., "work_from_home", "9_to_5")
                   - "location.zip_code" (string)
                   - "location.utility_provider" (string, e.g., "PG&E")
            value: The new value to set (will be coerced to appropriate type)
            reason: Brief explanation of why this is being updated

        Returns:
            Confirmation message with what was updated.
        """
        # Load current profile or create new one
        profile = get_profile_from_store(store, user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)

        # Parse field path
        parts = field.split(".")
        if len(parts) != 2:
            return f"Invalid field format: {field}. Use 'section.field' format."

        section_name, field_name = parts

        # Get or create section
        section = getattr(profile, section_name, None)
        if section is None:
            section_map = {
                "equipment": Equipment,
                "preferences": Preferences,
                "household": Household,
                "location": Location,
            }
            cls = section_map.get(section_name)
            if cls is None:
                return f"Unknown section: {section_name}. Valid: equipment, preferences, household, location"
            section = cls()
            setattr(profile, section_name, section)

        # Check if field exists
        if field_name not in type(section).model_fields:
            valid_fields = list(type(section).model_fields.keys())
            return f"Unknown field: {field_name} in {section_name}. Valid: {valid_fields}"

        # Coerce value to appropriate type
        coerced_value = _coerce_value(field_name, value, section)

        # Store old value for reporting
        old_value = getattr(section, field_name, None)

        # Apply update
        try:
            setattr(section, field_name, coerced_value)
        except (ValueError, TypeError) as e:
            return f"Failed to set {field}={value}: {e}"

        # Update timestamps
        if hasattr(section, "updated_at"):
            section.updated_at = datetime.now(tz=None)
        profile.updated_at = datetime.now(tz=None)

        # Save to store
        save_profile_to_store(store, profile)

        return f"Updated {field}: {old_value} -> {coerced_value} (reason: {reason})"

    @tool
    def get_current_profile() -> str:
        """Get the current user profile to see what information is already known.

        Use this BEFORE updating to check current values and avoid redundant updates.
        Only update fields that have changed or are missing.

        Returns:
            Summary of the current profile, or indication that no profile exists.
        """
        profile = get_profile_from_store(store, user_id)
        if profile is None:
            return "No profile exists yet for this user."

        # Build a readable summary
        parts = [f"User: {profile.user_id}"]

        if profile.equipment:
            eq = profile.equipment
            equip_parts = []
            if eq.solar_capacity_kw:
                equip_parts.append(f"solar={eq.solar_capacity_kw}kW")
            if eq.ev_model:
                equip_parts.append(f"EV={eq.ev_model}")
            if eq.ev_battery_kwh:
                equip_parts.append(f"battery={eq.ev_battery_kwh}kWh")
            if eq.heating_type:
                equip_parts.append(f"heating={eq.heating_type}")
            if eq.cooling_type:
                equip_parts.append(f"cooling={eq.cooling_type}")
            if equip_parts:
                parts.append(f"Equipment: {', '.join(equip_parts)}")

        if profile.location:
            loc = profile.location
            loc_parts = []
            if loc.zip_code:
                loc_parts.append(f"zip={loc.zip_code}")
            if loc.utility_provider:
                loc_parts.append(f"utility={loc.utility_provider}")
            if loc.rate_schedule:
                loc_parts.append(f"rate={loc.rate_schedule}")
            if loc_parts:
                parts.append(f"Location: {', '.join(loc_parts)}")

        if profile.household:
            hh = profile.household
            hh_parts = []
            if hh.occupants:
                hh_parts.append(f"occupants={hh.occupants}")
            if hh.work_schedule:
                hh_parts.append(f"schedule={hh.work_schedule}")
            if hh.typical_usage_pattern:
                hh_parts.append(f"usage={hh.typical_usage_pattern}")
            if hh_parts:
                parts.append(f"Household: {', '.join(hh_parts)}")

        if profile.preferences:
            pref = profile.preferences
            pref_parts = []
            if pref.budget_priority:
                pref_parts.append(f"budget={pref.budget_priority}")
            if pref.comfort_priority:
                pref_parts.append(f"comfort={pref.comfort_priority}")
            if pref.green_priority:
                pref_parts.append(f"green={pref.green_priority}")
            if pref_parts:
                parts.append(f"Preferences: {', '.join(pref_parts)}")

        if profile.notes:
            parts.append(f"Notes: {len(profile.notes)} observation(s)")

        return "\n".join(parts)

    @tool
    def add_observation(topic: str, content: str) -> str:
        """Add an observation or note about the user that doesn't fit structured fields.

        Use this for contextual information like:
        - "Planning to buy an EV soon"
        - "Concerned about high summer bills"
        - "Interested in battery storage options"
        - "Has solar but considering expansion"

        Only add observations for significant user-stated intentions or concerns.

        Args:
            topic: Short topic/category (e.g., "future_plans", "concerns", "interests")
            content: The observation content

        Returns:
            Confirmation that the observation was stored.
        """
        profile = get_profile_from_store(store, user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)

        # Add note to profile
        note = ProfileNote(
            topic=topic,
            content=content,
            created_at=datetime.now(tz=None),
        )

        if profile.notes is None:
            profile.notes = []
        profile.notes.append(note)

        profile.updated_at = datetime.now(tz=None)
        save_profile_to_store(store, profile)

        return f"Added observation about '{topic}': {content}"

    return [update_profile_field, get_current_profile, add_observation]


def _coerce_value(field_name: str, raw_value: str, section) -> object:
    """Coerce a string value to the appropriate Python type based on the field."""
    import re

    # Handle empty strings - return None for optional fields
    if not raw_value or raw_value.strip() == "":
        return None

    field_info = type(section).model_fields.get(field_name)
    if field_info is None:
        return raw_value

    annotation = field_info.annotation

    # Handle Optional types
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        args = getattr(annotation, "__args__", ())
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            annotation = non_none[0]

    # Coerce based on type
    if annotation is float:
        match = re.search(r"[-+]?\d*\.?\d+", raw_value)
        if match:
            return float(match.group())
        return None  # Return None instead of failing
    elif annotation is int:
        match = re.search(r"[-+]?\d+", raw_value)
        if match:
            return int(match.group())
        return None  # Return None instead of failing
    elif annotation is bool:
        return raw_value.lower() in ("true", "yes", "1")
    else:
        return raw_value