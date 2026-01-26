# Data Model: Home Energy Advisor

**Feature**: 001-langgraph-agent | **Date**: 2026-01-21

## Entity Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       UserProfile                           │
│  user_id, equipment, preferences, household, location       │
│  notes (summarized conversation history)                    │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Equipment  │ │ Preferences │ │  Household  │           │
│  │ (solar, EV) │ │ (priorities)│ │ (schedule)  │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AdvisorState (Orchestrator)             │
│  user_id, session_id, message, messages, turn_count         │
│  user_profile, tool_observations, retrieved_docs, response   │
│  extracted_facts, should_memorize                            │
│                                                             │
│  Subgraphs:                                                 │
│  ┌───────────────────────┐  ┌─────────────────┐            │
│  │  Analyzer (create_agent) │  │ MemorizerState   │            │
│  │  (native ReAct loop)    │  │ (fact extraction) │            │
│  │  @tool functions,        │  │ messages, profile │            │
│  │  managed internally      │  │ extracted_facts,  │            │
│  └───────────────────────┘  │ summary, turns    │            │
│                              └─────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Entities

### UserProfile

Complete user record persisted across sessions.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | `str` | Yes | Unique user identifier |
| `equipment` | `Equipment` | No | User's energy equipment |
| `preferences` | `Preferences` | No | User priorities |
| `household` | `Household` | No | Household information |
| `location` | `Location` | No | Geographic and utility info |
| `notes` | `list[ProfileNote]` | No | Summarized conversation history |
| `created_at` | `datetime` | Yes | Profile creation timestamp |
| `updated_at` | `datetime` | Yes | Last update timestamp |

**Constraints**:
- `user_id` must be globally unique
- `updated_at` >= `created_at`

### ProfileNote

Summarized conversation content stored in long-term profile.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | `str` | Yes | Summarized text |
| `source_session` | `str` | Yes | Session ID this note came from |
| `source_turns` | `list[int]` | Yes | Turn numbers that were summarized |
| `created_at` | `datetime` | Yes | When note was created |

### Equipment

User's energy-related equipment.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `solar_capacity_kw` | `float` | No | Solar system size in kW |
| `ev_model` | `str` | No | Electric vehicle model |
| `ev_battery_kwh` | `float` | No | EV battery capacity |
| `has_battery_storage` | `bool` | No | Home battery present |
| `battery_capacity_kwh` | `float` | No | Home battery size |
| `heating_type` | `str` | No | gas, electric, heat_pump |
| `cooling_type` | `str` | No | central_ac, mini_split, none |
| `updated_at` | `datetime` | Yes | Last update timestamp |

### Preferences

User's priorities for recommendations.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `budget_priority` | `Literal['low', 'medium', 'high']` | No | Cost sensitivity |
| `comfort_priority` | `Literal['low', 'medium', 'high']` | No | Comfort vs savings |
| `green_priority` | `Literal['low', 'medium', 'high']` | No | Environmental focus |
| `updated_at` | `datetime` | Yes | Last update timestamp |

### Household

Household composition and patterns.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `work_schedule` | `str` | No | e.g., "Office 9-5", "WFH", "Hybrid" |
| `occupants` | `int` | No | Number of household members |
| `typical_usage_pattern` | `str` | No | morning_heavy, evening_heavy, constant |
| `updated_at` | `datetime` | Yes | Last update timestamp |

**Note**: The `updated_at` field on Household is critical for staleness detection. The demo scenario intentionally has this field 220+ days old.

### Location

Geographic and utility information.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lat` | `float` | No | Latitude |
| `lon` | `float` | No | Longitude |
| `zip_code` | `str` | No | ZIP code |
| `utility_provider` | `str` | No | Utility company name |
| `rate_schedule` | `str` | No | Rate plan identifier |

---

## Memory Offload Models

### ExtractedFact

Fact extracted from conversation by the memorize node. When applied, the profile field is updated directly with the new value and the section's `updated_at` timestamp is refreshed.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `field` | `str` | Yes | Profile field to update (e.g., "household.work_schedule") |
| `new_value` | `str` | Yes | New value extracted from conversation |
| `confidence` | `float` | Yes | LLM confidence in extraction (0-1) |
| `source_turn` | `int` | Yes | Turn number where fact was mentioned |
| `source_text` | `str` | Yes | Exact text that contained the fact |

**Behavior**: When an ExtractedFact is applied, the profile field is overwritten with `new_value` and the section's `updated_at` is set to now. This prevents staleness. The MemoryHygieneGrader catches failures when the memorize node **doesn't run** or **misses a fact** — leading to stale `updated_at` timestamps.

**Example**:
```json
{
  "field": "household.work_schedule",
  "new_value": "WFH",
  "confidence": 0.95,
  "source_turn": 3,
  "source_text": "I actually started working from home last month"
}
```

---

## LangGraph State

### AdvisorState

State object passed through the LangGraph flow.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | `str` | Yes | User making the request |
| `session_id` | `str` | Yes | Current session identifier |
| `message` | `str` | Yes | User's input message |
| `messages` | `list[BaseMessage]` | Yes | Conversation history |
| `turn_count` | `int` | Yes | Number of turns in current session |
| `user_profile` | `UserProfile` | No | Loaded user profile |
| `weather_data` | `WeatherForecast` | No | Weather API response |
| `rate_data` | `RateSchedule` | No | Utility rate data |
| `solar_estimate` | `SolarEstimate` | No | PVWatts calculation |
| `retrieved_docs` | `list[Document]` | No | RAG retrieval results |
| `response` | `str` | No | Generated response |
| `tool_observations` | `list[dict]` | No | Tool call results from Analyzer (populated from create_agent output messages) |
| `extracted_facts` | `list[ExtractedFact]` | No | Facts extracted by memorize node |
| `should_memorize` | `bool` | No | Flag to trigger memorize node (session end or turn threshold) |

### Analyzer (create_agent)

The Analyzer uses `create_agent()` from `langchain.agents` (LangGraph v1) and does **not** need a custom state definition. The `create_agent()` function manages its own internal state (messages with AIMessage tool_calls and ToolMessage results).

**Configuration**:
- `model`: ChatOllama instance (configured per agents.yaml)
- `tools`: List of `@tool`-decorated functions (weather, rates, solar)
- `system_prompt`: Analyzer system prompt from prompts.py
- `name`: `"analyzer"` (identifies subgraph in traces)

**Exit Conditions**:
- LLM stops issuing tool_calls → natural exit
- `recursion_limit` reached at invocation → forced exit (prevents loops)
- Same tool called with same args > 3 times → LoopGrader failure (detected in trace)

**Output**: After the Analyzer subgraph completes, the Advisor extracts tool observations from the Analyzer's output messages (ToolMessage objects) and populates `tool_observations` in AdvisorState.

### MemorizerState

State for the memory offload subgraph. Passed into the Memorizer at session end or turn threshold.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | `list[BaseMessage]` | Yes | Conversation to analyze |
| `user_profile` | `UserProfile` | Yes | Current profile to update |
| `extracted_facts` | `list[ExtractedFact]` | No | Facts found by LLM |
| `validated_facts` | `list[ExtractedFact]` | No | Facts passing confidence threshold (>= 0.7) |
| `summary` | `str` | No | Generated conversation summary |
| `turns_to_summarize` | `list[int]` | No | Turn indices > 20 to compress |

**Behavior**:
- Extract: LLM analyzes messages, outputs structured `ExtractedFact[]`
- Apply: Updates profile fields with `new_value`, refreshes `updated_at` timestamps
- Summarize: Creates `ProfileNote` from old turns, appends to `profile.notes`

---

## Tool Response Models

### WeatherForecast

Response from weather API.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | `dict` | Yes | lat, lon, city |
| `current` | `dict` | Yes | temp, cloud_cover, conditions |
| `forecast` | `list[dict]` | Yes | Hourly/daily forecasts |
| `solar_hours` | `float` | No | Estimated solar production hours |
| `timestamp` | `datetime` | Yes | Forecast retrieval time |

### RateSchedule

Response from utility rates API.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `utility_name` | `str` | Yes | Utility provider |
| `schedule_name` | `str` | Yes | Rate schedule ID |
| `periods` | `list[RatePeriod]` | Yes | TOU periods |
| `effective_date` | `date` | Yes | Rate effective date |

### RatePeriod

Time-of-use rate period.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | off_peak, peak, partial_peak |
| `start_hour` | `int` | Yes | Period start (0-23) |
| `end_hour` | `int` | Yes | Period end (0-23) |
| `rate_kwh` | `float` | Yes | Rate in $/kWh |
| `days` | `list[str]` | Yes | Applicable days |

### SolarEstimate

Response from PVWatts API.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `system_capacity_kw` | `float` | Yes | System size |
| `ac_annual_kwh` | `float` | Yes | Annual production |
| `monthly_kwh` | `list[float]` | Yes | Monthly breakdown |
| `solrad_annual` | `float` | Yes | Solar radiation |
| `capacity_factor` | `float` | Yes | System efficiency |

### RetrievedDocument

Document from knowledge base retrieval.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | `str` | Yes | Document content |
| `source` | `str` | Yes | Source file/identifier |
| `score` | `float` | Yes | Relevance score (0-1) |

---

## Pydantic Schema Definition

```python
from datetime import datetime, date
from typing import Literal, Optional, Annotated
from pydantic import BaseModel, Field
from operator import add


class Equipment(BaseModel):
    """User's energy equipment."""
    solar_capacity_kw: Optional[float] = None
    ev_model: Optional[str] = None
    ev_battery_kwh: Optional[float] = None
    has_battery_storage: Optional[bool] = None
    battery_capacity_kwh: Optional[float] = None
    heating_type: Optional[Literal['gas', 'electric', 'heat_pump']] = None
    cooling_type: Optional[Literal['central_ac', 'mini_split', 'none']] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Preferences(BaseModel):
    """User priority settings."""
    budget_priority: Optional[Literal['low', 'medium', 'high']] = None
    comfort_priority: Optional[Literal['low', 'medium', 'high']] = None
    green_priority: Optional[Literal['low', 'medium', 'high']] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Household(BaseModel):
    """Household information."""
    work_schedule: Optional[str] = None
    occupants: Optional[int] = None
    typical_usage_pattern: Optional[Literal['morning_heavy', 'evening_heavy', 'constant']] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Location(BaseModel):
    """Geographic and utility info."""
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    zip_code: Optional[str] = Field(None, pattern=r'^\d{5}$')
    utility_provider: Optional[str] = None
    rate_schedule: Optional[str] = None


class ProfileNote(BaseModel):
    """Summarized conversation content stored in long-term profile."""
    content: str
    source_session: str
    source_turns: list[int]
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RatePeriod(BaseModel):
    """Time-of-use rate period."""
    name: Literal['off_peak', 'peak', 'partial_peak']
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=0, le=23)
    rate_kwh: float = Field(gt=0)
    days: list[str]


class RateSchedule(BaseModel):
    """Utility rate schedule."""
    utility_name: str
    schedule_name: str
    periods: list[RatePeriod]
    effective_date: date


class WeatherForecast(BaseModel):
    """Weather API response."""
    location: dict
    current: Optional[dict] = None
    forecast: list[dict]
    solar_hours: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SolarEstimate(BaseModel):
    """PVWatts API response."""
    system_capacity_kw: float
    ac_annual_kwh: float
    monthly_kwh: list[float]
    solrad_annual: float
    capacity_factor: Optional[float] = None


class RetrievedDocument(BaseModel):
    """Document from knowledge base."""
    text: str
    source: str
    score: float = Field(ge=0, le=1)


# LangGraph State (using TypedDict for compatibility)
from typing import TypedDict
from langchain_core.messages import BaseMessage


class AdvisorState(TypedDict):
    """State passed through the main orchestrator graph."""
    user_id: str
    session_id: str
    message: str
    messages: Annotated[list[BaseMessage], add]
    turn_count: int
    user_profile: Optional[UserProfile]
    weather_data: Optional[WeatherForecast]
    rate_data: Optional[RateSchedule]
    solar_estimate: Optional[SolarEstimate]
    retrieved_docs: list[RetrievedDocument]
    tool_observations: list[dict]  # Tool results from Analyzer (extracted from create_agent output)
    response: Optional[str]
    extracted_facts: list[ExtractedFact]
    should_memorize: bool


## Analyzer uses create_agent() — no custom state needed.
# create_agent() from langchain.agents manages its own internal
# MessagesState (AIMessage with tool_calls + ToolMessage results).


class MemorizerState(TypedDict):
    """State for the memory offload subgraph."""
    messages: list[BaseMessage]
    user_profile: UserProfile
    extracted_facts: list[ExtractedFact]
    validated_facts: list[ExtractedFact]
    summary: Optional[str]
    turns_to_summarize: list[int]
```

---

## Sample Data: Demo User Profile

This profile is intentionally configured for the stale memory demonstration:

```json
{
  "user_id": "home_123",
  "equipment": {
    "solar_capacity_kw": 6.0,
    "ev_model": "Tesla Model 3",
    "ev_battery_kwh": 57.5,
    "has_battery_storage": false,
    "heating_type": "heat_pump",
    "updated_at": "2025-09-20T10:00:00Z"
  },
  "preferences": {
    "budget_priority": "high",
    "comfort_priority": "medium",
    "green_priority": "high",
    "updated_at": "2025-09-20T10:00:00Z"
  },
  "household": {
    "work_schedule": "Office 9-5",
    "occupants": 2,
    "typical_usage_pattern": "evening_heavy",
    "updated_at": "2025-06-15T10:00:00Z"
  },
  "location": {
    "lat": 37.7749,
    "lon": -122.4194,
    "zip_code": "94102",
    "utility_provider": "PG&E",
    "rate_schedule": "EV-TOU-5"
  },
  "created_at": "2025-05-01T10:00:00Z",
  "updated_at": "2025-09-20T10:00:00Z"
}
```

**Key staleness indicator**: `household.updated_at` is "2025-06-15" — 220 days before the demo date (2026-01-21). This triggers the `MemoryHygieneGrader` failure.

---

## State Transitions

### Advisor Graph (Orchestrator)

```
┌────────────────────────────────────────────────────────────────┐
│                          Intake                                 │
│  Input: user_id, message                                       │
│  Output: messages (with new user message), turn_count           │
│  Check: new user → onboarding flow                             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                          Recall                                 │
│  Input: user_id                                                │
│  Actions: memory_read, retrieval (if needed)                   │
│  Output: user_profile, retrieved_docs                          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌════════════════════════════════════════════════════════════════┐
║     Analyzer (create_agent — native ReAct)                     ║
║                                                                ║
║  ┌──────────────────────┐                                      ║
║  │     Agent (LLM)       │  LLM decides: call tools or respond ║
║  │  Sees: messages +     │                                      ║
║  │  system_prompt +      │                                      ║
║  │  tool schemas          │                                      ║
║  └──────────┬────────────┘                                      ║
║        has tool_calls?                                           ║
║    ┌─────────┴─────────┐                                        ║
║   yes                  no                                        ║
║    │                    │                                        ║
║    ▼                    ▼                                        ║
║  ┌──────────────────┐  ┌────────┐                              ║
║  │  ToolNode         │  │  END   │                              ║
║  │  Execute @tool    │  └────────┘                              ║
║  │  functions        │                                          ║
║  └──────────┬────────┘                                          ║
║             │ (ToolMessage → back to Agent)                      ║
║             ▼                                                    ║
║         [Agent]                                                  ║
║         (loop)                                                   ║
╚════════════════════════════════════════════════════════════════╝
                              │
                              ▼  (ToolMessages → tool_observations)
┌────────────────────────────────────────────────────────────────┐
│                        Recommend                                │
│  Input: all context (profile, tool_observations, retrieved_docs)│
│  Actions: llm_call                                             │
│  Output: response, updated messages, should_memorize flag      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ should_memorize? │
                    └────────┬────────┘
                    yes      │        no
              ┌──────────────┴──────────────┐
              ▼                             ▼
╔═════════════════════════════╗     ┌──────────┐
║   Memorizer Subgraph         ║     │   END    │
║                              ║     └──────────┘
║  ┌──────────────────────┐   ║
║  │      Extract          │   ║
║  │  LLM: find new facts  │   ║
║  │  Output: ExtractedFact[]║  ║
║  └──────────┬────────────┘   ║
║             │                 ║
║             ▼                 ║
║  ┌──────────────────────┐   ║
║  │       Apply           │   ║
║  │  Update profile fields │   ║
║  │  Refresh timestamps    │   ║
║  └──────────┬────────────┘   ║
║             │                 ║
║             ▼                 ║
║  ┌──────────────────────┐   ║
║  │     Summarize         │   ║
║  │  Compress old turns   │   ║
║  │  → ProfileNotes       │   ║
║  └──────────────────────┘   ║
╚═════════════════════════════╝
              │
              ▼
         ┌────────┐
         │  END   │
         └────────┘
```

### Trigger Conditions

**Analyzer (create_agent)** — entered when:
- User query requires real-time data (weather, rates, solar estimates)
- Simple FAQ/knowledge-base queries may skip it (routed directly to Recommend)

**Memorizer Subgraph** — entered when `should_memorize = True`:
- Session ends (user says "bye", "exit", or closes connection)
- Turn count exceeds threshold (default: 10 turns)
- Explicit user request ("Remember that I work from home now")

### Evaluation Failure Modes

| Failure | Grader | Trigger |
|---------|--------|---------|
| Stale profile field | MemoryHygieneGrader | Memorizer doesn't run → `updated_at` stays old |
| Tool loop | LoopGrader | Analyzer calls same tool+args > 3 times |
| Retrieval waste | RetrievalRelevanceGrader | Recall retrieves docs not used by Recommend |
| Budget overrun | BudgetGrader | Too many Analyzer iterations → tokens > budget |

---

## Validation Rules

### UserProfile Validation
1. `user_id` must be non-empty string
2. `created_at` must be valid ISO8601 datetime
3. `updated_at` >= `created_at`
4. Nested objects must have valid `updated_at` for staleness checks

### Location Validation
1. `lat` must be between -90 and 90
2. `lon` must be between -180 and 180
3. `zip_code` must be 5 digits (US)

### Rate Period Validation
1. `start_hour` and `end_hour` must be 0-23
2. `rate_kwh` must be positive
3. `days` must contain valid day names

---

## Memory Staleness Calculation

For `MemoryHygieneGrader` integration:

```python
from datetime import datetime, timedelta

def calculate_staleness_days(field_updated_at: datetime) -> int:
    """Calculate days since field was updated."""
    now = datetime.utcnow()
    delta = now - field_updated_at
    return delta.days

def is_stale(field_updated_at: datetime, threshold_days: int = 90) -> bool:
    """Check if a field is stale based on threshold."""
    return calculate_staleness_days(field_updated_at) > threshold_days
```

Example with demo data:
- `household.updated_at` = 2025-06-15
- Current date = 2026-01-21
- Staleness = 220 days
- Threshold = 90 days
- Result: **STALE**