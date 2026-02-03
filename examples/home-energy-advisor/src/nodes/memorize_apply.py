"""Memorize Apply node: filters facts by confidence and updates profile."""

from datetime import datetime

from src.core.models import ExtractedFact, UserProfile
from src.core.state import MemorizerState
from src.config import get_config


def memorize_apply_node(state: MemorizerState) -> dict:
    """Apply extracted facts to the user profile.

    - Filters facts by confidence threshold (default 0.7)
    - Updates the appropriate profile section fields
    - Refreshes section-level updated_at timestamps

    Returns:
        Dict with 'validated_facts' and updated 'user_profile'.
    """
    config = get_config()
    threshold = config.memorizer.confidence_threshold

    extracted = state.get("extracted_facts", [])
    validated = [f for f in extracted if f.confidence >= threshold]

    profile = state["user_profile"]
    if profile is None:
        return {"validated_facts": validated, "user_profile": profile}

    # Create a mutable copy
    profile = profile.model_copy(deep=True)

    for fact in validated:
        _apply_fact(profile, fact)

    return {
        "validated_facts": validated,
        "user_profile": profile,
    }


def _apply_fact(profile: UserProfile, fact: ExtractedFact) -> None:
    """Apply a single fact to the profile, refreshing timestamps."""
    parts = fact.field.split(".")
    if len(parts) != 2:
        return

    section_name, field_name = parts
    section = getattr(profile, section_name, None)
    if section is None:
        # Create the section if it doesn't exist
        from src.core.models import Equipment, Household, Location, Preferences
        section_map = {
            "equipment": Equipment,
            "preferences": Preferences,
            "household": Household,
            "location": Location,
        }
        cls = section_map.get(section_name)
        if cls is None:
            return
        section = cls()
        setattr(profile, section_name, section)

    # Check if the field actually exists on this section
    if field_name not in type(section).model_fields:
        return

    # Convert value to appropriate type
    value = _coerce_value(field_name, fact.new_value, section)
    try:
        setattr(section, field_name, value)
    except (ValueError, TypeError):
        return

    # Refresh timestamps
    if hasattr(section, "updated_at"):
        section.updated_at = datetime.now(tz=None)
    profile.updated_at = datetime.now(tz=None)


def _coerce_value(field_name: str, raw_value: str, section) -> object:
    """Coerce a string value to the appropriate Python type based on the field."""
    # Get type hint from the model
    field_info = type(section).model_fields.get(field_name)
    if field_info is None:
        return raw_value

    annotation = field_info.annotation

    # Handle Optional types
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        args = getattr(annotation, "__args__", ())
        # For Optional[X], get X
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            annotation = non_none[0]

    # Coerce based on type
    if annotation is float:
        return _extract_number(raw_value, float)
    elif annotation is int:
        return _extract_number(raw_value, int)
    elif annotation is bool:
        return raw_value.lower() in ("true", "yes", "1")
    else:
        return raw_value


def _extract_number(raw_value: str, target_type: type):
    """Extract a numeric value from a string, stripping units."""
    import re
    match = re.search(r"[-+]?\d*\.?\d+", raw_value)
    if match:
        return target_type(match.group())
    return target_type(raw_value)
