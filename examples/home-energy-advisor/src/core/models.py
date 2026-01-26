"""Pydantic models for the Home Energy Advisor."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- User Profile Models ---


class Equipment(BaseModel):
    """User's energy equipment."""

    solar_capacity_kw: Optional[float] = None
    ev_model: Optional[str] = None
    ev_battery_kwh: Optional[float] = None
    has_battery_storage: Optional[bool] = None
    battery_capacity_kwh: Optional[float] = None
    heating_type: Optional[Literal["gas", "electric", "heat_pump"]] = None
    cooling_type: Optional[Literal["central_ac", "mini_split", "none"]] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class Preferences(BaseModel):
    """User priority settings."""

    budget_priority: Optional[Literal["low", "medium", "high"]] = None
    comfort_priority: Optional[Literal["low", "medium", "high"]] = None
    green_priority: Optional[Literal["low", "medium", "high"]] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class Household(BaseModel):
    """Household information."""

    work_schedule: Optional[str] = None
    occupants: Optional[int] = None
    typical_usage_pattern: Optional[Literal["morning_heavy", "evening_heavy", "constant"]] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class Location(BaseModel):
    """Geographic and utility info."""

    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    zip_code: Optional[str] = Field(None, pattern=r"^\d{5}$")
    utility_provider: Optional[str] = None
    rate_schedule: Optional[str] = None


class ProfileNote(BaseModel):
    """Summarized conversation content stored in long-term profile."""

    content: str
    source_session: str
    source_turns: list[int]
    created_at: datetime = Field(default_factory=datetime.now)


class ExtractedFact(BaseModel):
    """Fact extracted from conversation by memorize node."""

    field: str
    new_value: str
    confidence: float = Field(ge=0, le=1)
    source_turn: int
    source_text: str


class UserProfile(BaseModel):
    """Complete user profile persisted across sessions."""

    user_id: str
    equipment: Optional[Equipment] = None
    preferences: Optional[Preferences] = None
    household: Optional[Household] = None
    location: Optional[Location] = None
    notes: list[ProfileNote] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# --- Tool Response Models ---


class WeatherLocation(BaseModel):
    """Location info in weather response."""

    lat: float
    lon: float
    city: str = "Unknown"


class CurrentWeather(BaseModel):
    """Current weather conditions."""

    temp: float
    cloud_cover: int = Field(ge=0, le=100)
    conditions: str


class ForecastDay(BaseModel):
    """Single day forecast entry."""

    date: str
    high_f: Optional[float] = None
    low_f: Optional[float] = None
    cloud_cover: int = Field(ge=0, le=100)
    conditions: str


class WeatherForecast(BaseModel):
    """Weather API response."""

    location: WeatherLocation
    current: CurrentWeather
    forecast: list[ForecastDay] = Field(default_factory=list)
    solar_hours: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_fallback: bool = False


class RatePeriod(BaseModel):
    """Time-of-use rate period."""

    name: str
    start_hour: int = Field(ge=0, le=24)
    end_hour: int = Field(ge=0, le=24)
    rate_kwh: float = Field(gt=0)
    days: list[str]


class RateSchedule(BaseModel):
    """Utility rate schedule."""

    utility_name: str
    schedule_name: str
    periods: list[RatePeriod]
    effective_date: str
    is_fallback: bool = False


class SolarEstimate(BaseModel):
    """PVWatts API response."""

    system_capacity_kw: float
    ac_annual_kwh: float
    monthly_kwh: list[float]
    solrad_annual: float
    capacity_factor: Optional[float] = None
    is_fallback: bool = False


class FactExtractionResult(BaseModel):
    """Structured output for LLM fact extraction."""

    facts: list[ExtractedFact] = Field(default_factory=list)


class RetrievedDocument(BaseModel):
    """Document from knowledge base."""

    text: str
    source: str
    score: float = Field(ge=0, le=1)
