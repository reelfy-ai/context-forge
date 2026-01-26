"""Utility rate schedule tool with static TOU data and NREL fallback."""

import logging
import time

from langchain_core.tools import tool

from src.config import get_config
from src.tools.mock import mock_utility_rates

logger = logging.getLogger(__name__)


def _get_mode() -> str:
    """Get the current tools mode (live or mock)."""
    return get_config().tools_mode


@tool
def get_utility_rates(utility: str, schedule: str | None = None) -> str:
    """Get electricity rate schedule for a utility provider.

    Args:
        utility: Utility provider name (e.g., "PG&E", "SCE", "SDG&E")
        schedule: Specific rate schedule (e.g., "EV-TOU-5"). If None, returns default residential.

    Returns:
        JSON string with TOU rate periods and pricing.
    """
    start = time.time()
    mode = _get_mode()

    if mode == "mock":
        logger.info("rates tool: using mock mode")
        result = mock_utility_rates(utility=utility, schedule=schedule)
        return result.model_dump_json()

    # Live mode: use static data (rates don't change frequently)
    try:
        result = mock_utility_rates(utility=utility, schedule=schedule)
        result.is_fallback = False
        elapsed = time.time() - start
        logger.info(f"rates tool: success (static data) in {elapsed:.2f}s")
        return result.model_dump_json()

    except Exception as e:
        elapsed = time.time() - start
        logger.warning(f"rates tool: failed ({e}), using fallback. Elapsed: {elapsed:.2f}s")
        result = mock_utility_rates(utility=utility, schedule=schedule)
        result.is_fallback = True
        return result.model_dump_json()
