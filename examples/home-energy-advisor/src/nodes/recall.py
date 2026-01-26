"""Recall node: loads user profile from LangGraph Store.

This node uses LangGraph's native Store for cross-session profile persistence.
The store is injected by the graph runtime when compiled with store=...
"""

from langgraph.store.base import BaseStore

from src.core.models import UserProfile
from src.core.state import AdvisorState
from src.memory.helpers import get_all_stale_sections, get_profile_from_store


def recall_node(state: AdvisorState, *, store: BaseStore) -> dict:
    """Load user profile from LangGraph Store.

    Reads the profile for the current user_id and sets it in state.
    Returns empty dict if no profile exists (new user).

    Args:
        state: Current advisor state
        store: LangGraph Store (injected by runtime)

    Returns:
        Dict with 'user_profile' if found, empty dict otherwise
    """
    user_id = state.get("user_id")
    if not user_id:
        return {}

    profile = get_profile_from_store(store, user_id)

    if profile is None:
        # Create a new profile for new users
        profile = UserProfile(user_id=user_id)

    # Check for stale sections (for potential future use in recommendations)
    stale_sections = get_all_stale_sections(profile)
    if stale_sections:
        # Could add these to state for the advisor to mention
        pass

    return {"user_profile": profile}
