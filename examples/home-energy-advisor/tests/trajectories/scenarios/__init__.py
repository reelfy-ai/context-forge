"""Scenario definitions for trajectory testing."""

from .ev_charging import ev_charging_scenario, ev_charging_persona
from .solar_advice import solar_advice_scenario, solar_advice_persona
from .general_advice import general_advice_scenario, general_advice_persona
from .stale_memory import (
    stale_work_schedule_persona,
    stale_work_schedule_scenario,
    stale_solar_persona,
    stale_solar_scenario,
    multi_update_persona,
    multi_update_scenario,
    stale_work_schedule_generative_scenario,
)

__all__ = [
    "ev_charging_scenario",
    "ev_charging_persona",
    "solar_advice_scenario",
    "solar_advice_persona",
    "general_advice_scenario",
    "general_advice_persona",
    # Stale memory scenarios
    "stale_work_schedule_persona",
    "stale_work_schedule_scenario",
    "stale_solar_persona",
    "stale_solar_scenario",
    "multi_update_persona",
    "multi_update_scenario",
    "stale_work_schedule_generative_scenario",
]
