"""Memory persistence layer.

This module provides two approaches to memory:

1. LangGraph Native (recommended):
   - Use `get_profile_from_store` / `save_profile_to_store` with LangGraph's Store
   - Checkpointer handles session state automatically

2. Legacy JSON-file based (for testing/standalone):
   - Use `MemoryStore` class for file-based persistence
"""

from src.memory.helpers import (
    PROFILES_NAMESPACE,
    STALENESS_THRESHOLD_DAYS,
    get_all_stale_sections,
    get_profile_from_store,
    get_section_staleness,
    save_profile_to_store,
    update_profile_field,
)
from src.memory.store import MemoryStore

__all__ = [
    # LangGraph Store helpers
    "PROFILES_NAMESPACE",
    "STALENESS_THRESHOLD_DAYS",
    "get_profile_from_store",
    "save_profile_to_store",
    "get_section_staleness",
    "get_all_stale_sections",
    "update_profile_field",
    # Legacy file-based store
    "MemoryStore",
]
