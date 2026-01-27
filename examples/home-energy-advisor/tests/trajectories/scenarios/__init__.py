"""Scenario definitions for trajectory testing."""

from .ev_charging import ev_charging_scenario, ev_charging_persona
from .solar_advice import solar_advice_scenario, solar_advice_persona
from .general_advice import general_advice_scenario, general_advice_persona

__all__ = [
    "ev_charging_scenario",
    "ev_charging_persona",
    "solar_advice_scenario",
    "solar_advice_persona",
    "general_advice_scenario",
    "general_advice_persona",
]
