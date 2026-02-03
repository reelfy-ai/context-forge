# Research: Home Energy Advisor Agent

**Feature**: 001-langgraph-agent | **Date**: 2026-01-21

## Overview

This document captures technology decisions and research findings for implementing the Home Energy Advisor LangGraph agent.

---

## 1. LangGraph StateGraph Patterns

### Decision
Use LangGraph's `StateGraph` with typed state, conditional edges, and **subgraphs** for the multi-agent architecture: Advisor (orchestrator) → Analyzer (ReAct subgraph) → Memorizer (learning subgraph).

### Rationale
- LangGraph is the standard for building stateful, multi-step agent workflows
- StateGraph provides clear node boundaries for instrumentation
- Conditional edges allow dynamic routing (e.g., skip tools if cached data exists)
- Built-in support for state persistence and checkpointing

### Implementation Pattern

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from operator import add

class AdvisorState(TypedDict):
    user_id: str
    message: str
    messages: Annotated[list, add]  # Accumulates conversation
    user_profile: dict | None
    weather_data: dict | None
    rate_data: dict | None
    solar_estimate: dict | None
    retrieved_docs: list[dict]
    response: str | None

# Build graph
graph = StateGraph(AdvisorState)
graph.add_node("intake", intake_node)
graph.add_node("recall", recall_node)
graph.add_node("analyze", analyze_node)
graph.add_node("recommend", recommend_node)

graph.set_entry_point("intake")
graph.add_edge("intake", "recall")
graph.add_edge("recall", "analyze")
graph.add_edge("analyze", "recommend")
graph.add_edge("recommend", END)

app = graph.compile()
```

### Subgraph Pattern (with create_agent)

LangGraph v1 supports composing graphs via subgraphs. The Analyzer uses `create_agent()` which returns a `CompiledStateGraph` that can be added directly as a node in the parent graph.

```python
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

# Define Analyzer using create_agent (native ReAct)
@tool
async def get_weather_forecast(lat: float, lon: float, days: int = 1) -> dict:
    """Get weather forecast including cloud cover for solar estimation."""
    ...

@tool
async def get_utility_rates(utility: str, schedule: str | None = None) -> dict:
    """Get electricity rate schedule for a utility."""
    ...

@tool
async def get_solar_estimate(lat: float, lon: float, system_capacity_kw: float) -> dict:
    """Estimate solar production for a PV system."""
    ...

analyzer_agent = create_agent(
    model=ChatOllama(model="llama3.1:8b", temperature=0.3),
    tools=[get_weather_forecast, get_utility_rates, get_solar_estimate],
    system_prompt="You are an energy data analyst...",
    name="analyzer",
)

# Parent graph references create_agent's compiled graph as a node
parent_graph = StateGraph(AdvisorState)
parent_graph.add_node("intake", intake_node)
parent_graph.add_node("recall", recall_node)
parent_graph.add_node("analyzer", analyzer_agent)  # create_agent as subgraph node
parent_graph.add_node("recommend", recommend_node)
parent_graph.add_node("memorizer", memorizer_subgraph)
# ... wire edges
```

**Key Benefit**: `create_agent()` returns a `CompiledStateGraph` — it slots directly into the parent as a node. No custom AnalyzerState, no manual ReAct wiring. The `LangGraphInstrumentor` captures all tool_call steps automatically because tools use the `@tool` decorator.

### Alternatives Considered
- **LangChain AgentExecutor**: Less control over execution flow; harder to instrument individual steps
- **Custom state machine**: More flexibility but reinvents LangGraph's battle-tested patterns
- **CrewAI**: Overkill for single-agent demo; adds unnecessary complexity

---

## 1b. Native ReAct via `create_agent()` (LangGraph v1)

### Decision
Implement the Analyzer using `create_agent()` from `langchain.agents` — the LangGraph v1 native ReAct pattern with `@tool`-decorated functions.

### Rationale
- **Iterative reasoning**: LLM natively decides which tools to call and processes results before deciding next step
- **Loop detection**: `recursion_limit` at invocation prevents infinite loops; LoopGrader detects repeated calls in traces
- **Observability**: `@tool` decorator provides automatic schema for LLM binding AND automatic trace capture via `LangGraphInstrumentor`
- **Simplicity**: Eliminates 3 custom node files (think, execute, observe) and custom AnalyzerState
- **LangGraph v1 best practice**: `create_agent()` is the recommended approach replacing deprecated `create_react_agent()`

### Implementation Pattern

```python
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

@tool
async def get_weather_forecast(lat: float, lon: float, days: int = 1) -> dict:
    """Get weather forecast including cloud cover for solar estimation."""
    # Real or mock implementation based on config
    ...

@tool
async def get_utility_rates(utility: str, schedule: str | None = None) -> dict:
    """Get electricity rate schedule for a utility."""
    ...

@tool
async def get_solar_estimate(lat: float, lon: float, system_capacity_kw: float) -> dict:
    """Estimate solar production for a PV system."""
    ...

# The entire Analyzer is this one call:
analyzer = create_agent(
    model=ChatOllama(model="llama3.1:8b", temperature=0.3),
    tools=[get_weather_forecast, get_utility_rates, get_solar_estimate],
    system_prompt="You are an energy data analyst. Use the available tools to gather information needed to answer the user's energy question.",
    name="analyzer",  # Identifies subgraph in traces
)

# Use in parent graph:
advisor_graph.add_node("analyzer", analyzer)

# Control max iterations at invocation:
result = advisor_app.invoke(state, config={"recursion_limit": 10})
```

### Internal Architecture (managed by create_agent)

```
┌─────────────────────────────┐
│  Agent Node (LLM call)       │
│  - Receives messages         │
│  - Has tool schemas bound    │
│  - Outputs AIMessage         │
└─────────┬───────────────────┘
     has tool_calls?
  ┌────────┴────────┐
 yes                no → END
  │
  ▼
┌─────────────────────────────┐
│  ToolNode (execute @tools)   │
│  - Calls @tool functions     │
│  - Returns ToolMessage       │
└─────────┬───────────────────┘
          │ (back to Agent)
          ▼
      [Agent Node]
      (loop continues)
```

### Why create_agent Over Custom ReAct

| Aspect | Custom 3-Node | create_agent |
|--------|---------------|--------------|
| Files needed | react_think.py, react_execute.py, react_observe.py | None (one call in analyzer.py) |
| State management | Custom AnalyzerState TypedDict | Managed internally |
| LLM calls per iteration | 2 (think + observe) | 1 (native tool calling) |
| Tool registration | TOOL_REGISTRY dict | `@tool` decorator (auto-schema) |
| Trace capture | Manual emission | Automatic via LangGraphInstrumentor |
| Loop control | Custom iteration counter | recursion_limit at invocation |
| Maintenance | Must maintain parity with LangGraph updates | Uses official API |

---

## 1c. YAML Configuration

### Decision
Use YAML files for agent and tool configuration, loaded by Python config module.

### Rationale
- Non-developers can tune agent behavior without touching code
- Different YAML configs can simulate different evaluation scenarios (mock vs live mode)
- Follows agentic AI best practices (from reference architecture)
- Clear separation of code (logic) from configuration (behavior)

### Implementation Pattern

```python
import yaml
from pathlib import Path
from pydantic import BaseModel

class AgentConfig(BaseModel):
    model: str = "llama3.1:8b"
    temperature: float = 0.7

class AnalyzerConfig(AgentConfig):
    temperature: float = 0.3
    max_iterations: int = 5

class MemorizerConfig(AgentConfig):
    temperature: float = 0.2
    confidence_threshold: float = 0.7
    turn_threshold: int = 10
    max_turns_before_summary: int = 20

def load_config(config_dir: str = "./config") -> dict:
    agents_path = Path(config_dir) / "agents.yaml"
    tools_path = Path(config_dir) / "tools.yaml"
    agents = yaml.safe_load(agents_path.read_text()) if agents_path.exists() else {}
    tools = yaml.safe_load(tools_path.read_text()) if tools_path.exists() else {}
    return {"agents": agents, "tools": tools}
```

### Alternatives Considered
- **Python-only config (pydantic-settings)**: Less accessible to non-developers; mixes code and config
- **TOML**: Less readable than YAML for nested config; overkill for this project
- **Environment variables only**: Hard to represent nested structures (agent-specific temperatures)

---

## 2. Ollama Integration with LangChain

### Decision
Use `langchain_ollama.ChatOllama` for LLM calls and `langchain_ollama.OllamaEmbeddings` for embeddings.

### Rationale
- Official LangChain integration with Ollama
- Consistent interface with other LangChain components
- Supports streaming, tool calling, and structured output
- Local execution without API keys

### Implementation Pattern

```python
from langchain_ollama import ChatOllama, OllamaEmbeddings

# LLM for chat
llm = ChatOllama(
    model="llama3.1:8b",
    temperature=0.7,
    base_url="http://localhost:11434",
)

# Embeddings for RAG
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434",
)
```

### Configuration

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3.1:8b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768
    DEFAULT_TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 2048

settings = Settings()
```

### Alternatives Considered
- **Direct Ollama API**: More control but loses LangChain integration benefits
- **OpenAI API**: Requires paid API key; violates local-first principle
- **llama-cpp-python**: Lower-level; requires model file management

---

## 3. Milvus Lite Vector Store

### Decision
Use Milvus Lite with local file storage (`milvus.db`) for the knowledge base vector store.

### Rationale
- No server setup required (single file)
- Same API as full Milvus (easy to scale later)
- Proven pattern from reference implementation
- Supports Inner Product (IP) similarity metric

### Implementation Pattern

```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

class MilvusStore:
    def __init__(self, db_path: str = "./data/milvus.db"):
        self.collection_name = "knowledge_base"
        connections.connect(uri=db_path)

    def create_collection(self, dim: int = 768):
        if utility.has_collection(self.collection_name):
            Collection(self.collection_name).drop()

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]

        schema = CollectionSchema(fields=fields)
        collection = Collection(name=self.collection_name, schema=schema)
        collection.create_index(
            field_name="embedding",
            index_params={"metric_type": "IP", "index_type": "AUTOINDEX"}
        )
        collection.load()

    def retrieve(self, query_embedding: list[float], limit: int = 3) -> list[dict]:
        collection = Collection(self.collection_name)
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "IP"},
            limit=limit,
            output_fields=["text", "source"],
        )
        return [
            {"text": hit.entity.get("text"), "source": hit.entity.get("source"), "score": hit.score}
            for hit in results[0]
        ]
```

### Alternatives Considered
- **ChromaDB**: Good alternative but less feature-rich than Milvus
- **FAISS**: Lower-level; requires more boilerplate
- **Pinecone**: Cloud-only; requires API key

---

## 4. OpenWeatherMap API

### Decision
Use OpenWeatherMap's free tier for weather data (forecast endpoint).

### Rationale
- Free tier: 1,000 calls/day (sufficient for demo)
- Simple REST API with JSON responses
- Includes cloud cover (important for solar estimation)
- Well-documented

### API Details

**Endpoint**: `https://api.openweathermap.org/data/2.5/forecast`

**Required Parameters**:
- `lat`, `lon`: Coordinates
- `appid`: API key (free registration)
- `units`: `metric` or `imperial`

**Response Fields Used**:
- `main.temp`: Temperature
- `clouds.all`: Cloud cover percentage (0-100)
- `weather[0].description`: Conditions
- `dt_txt`: Forecast timestamp

### Implementation Pattern

```python
import httpx

async def get_weather_forecast(lat: float, lon: float, days: int = 1) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={
                "lat": lat,
                "lon": lon,
                "appid": settings.OPENWEATHERMAP_API_KEY,
                "units": "metric",
                "cnt": days * 8,  # 3-hour intervals
            }
        )
        response.raise_for_status()
        data = response.json()

        # Calculate solar hours from cloud cover
        solar_hours = sum(
            3 * (1 - item["clouds"]["all"] / 100)
            for item in data["list"]
        ) / 8  # Normalize to daily hours

        return {
            "location": {"lat": lat, "lon": lon, "city": data["city"]["name"]},
            "forecast": data["list"],
            "solar_hours_estimate": round(solar_hours, 1),
        }
```

### Mock Implementation

```python
def mock_weather_forecast(lat: float, lon: float, days: int = 1) -> dict:
    return {
        "location": {"lat": lat, "lon": lon, "city": "San Francisco"},
        "forecast": [...],  # Sample data
        "solar_hours_estimate": 6.5,
    }
```

---

## 5. NREL APIs

### Decision
Use NREL PVWatts v8 for solar production estimates and NREL Utility Rates v3 for electricity rate information.

### Rationale
- Free with API key registration
- 1,000 requests/hour (generous for demo)
- Authoritative source for US energy data
- Well-documented REST APIs

### PVWatts API

**Endpoint**: `https://developer.nrel.gov/api/pvwatts/v8.json`

**Required Parameters**:
- `api_key`: NREL API key
- `lat`, `lon`: System location
- `system_capacity`: System size in kW
- `azimuth`: Panel orientation (180 for south-facing)
- `tilt`: Panel tilt angle
- `array_type`: 0=fixed open rack, 1=fixed roof mount
- `module_type`: 0=standard, 1=premium, 2=thin film
- `losses`: System losses percentage

**Response Fields Used**:
- `outputs.ac_annual`: Annual AC production (kWh)
- `outputs.solrad_annual`: Annual solar radiation (kWh/m²/day)
- `outputs.ac_monthly`: Monthly production array

### Utility Rates API

**Endpoint**: `https://developer.nrel.gov/api/utility_rates/v3.json`

**Required Parameters**:
- `api_key`: NREL API key
- `lat`, `lon`: Location

**Response Fields Used**:
- `outputs.utility_name`: Utility company
- `outputs.residential`: Residential rate ($/kWh)
- `outputs.commercial`: Commercial rate ($/kWh)

**Note**: For TOU rates, we'll use static data for major utilities (PG&E, SCE, SDG&E) since the API provides average rates only.

### Implementation Pattern

```python
async def get_solar_estimate(
    lat: float, lon: float, system_capacity_kw: float
) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://developer.nrel.gov/api/pvwatts/v8.json",
            params={
                "api_key": settings.NREL_API_KEY,
                "lat": lat,
                "lon": lon,
                "system_capacity": system_capacity_kw,
                "azimuth": 180,
                "tilt": 20,
                "array_type": 1,  # Fixed roof mount
                "module_type": 1,  # Premium
                "losses": 14,
            }
        )
        data = response.json()
        return {
            "system_capacity_kw": system_capacity_kw,
            "ac_annual_kwh": data["outputs"]["ac_annual"],
            "monthly_kwh": data["outputs"]["ac_monthly"],
            "solrad_annual": data["outputs"]["solrad_annual"],
        }
```

---

## 6. ContextForge Instrumentation

### Decision
Use `LangGraphInstrumentor().instrument()` for automatic trace capture.

### Rationale
- One-line integration (Level 2)
- Captures all LangGraph node transitions
- Records LLM calls, tool invocations, state changes
- Produces ContextForge-compatible trace format

### Implementation Pattern

```python
from context_forge.instrumentation import LangGraphInstrumentor

# Add BEFORE creating the graph
instrumentor = LangGraphInstrumentor(
    output_path="./traces",
    agent_info={"name": "home-energy-advisor", "version": "1.0.0"}
)
instrumentor.instrument()

# Then create and run your agent normally
graph = create_advisor_graph()
app = graph.compile()
result = app.invoke({"user_id": "home_123", "message": "When should I charge my EV?"})
```

### Step Type Mapping

| LangGraph Event | ContextForge Step Type |
|-----------------|------------------------|
| Graph input | `user_input` |
| LLM call | `llm_call` |
| Tool invocation | `tool_call` |
| Vector search | `retrieval` |
| Profile load | `memory_read` |
| Profile update | `memory_write` |
| Node transition | `state_change` |
| Graph output | `final_output` |

---

## 7. Memory Persistence Pattern

### Decision
Use JSON files with timestamped fields for user profile persistence.

### Rationale
- Human-readable (easy debugging)
- No database setup required
- Timestamps enable staleness detection
- Simple file I/O operations

### Implementation Pattern

```python
import json
from pathlib import Path
from datetime import datetime

class MemoryStore:
    def __init__(self, data_dir: str = "./data/profiles"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_profile(self, user_id: str) -> dict | None:
        path = self.data_dir / f"{user_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save_profile(self, user_id: str, profile: dict) -> None:
        profile["updated_at"] = datetime.utcnow().isoformat()
        path = self.data_dir / f"{user_id}.json"
        path.write_text(json.dumps(profile, indent=2))

    def update_field(self, user_id: str, section: str, field: str, value: any) -> None:
        profile = self.load_profile(user_id) or {}
        if section not in profile:
            profile[section] = {}
        profile[section][field] = value
        profile[section]["updated_at"] = datetime.utcnow().isoformat()
        self.save_profile(user_id, profile)
```

---

## Summary of Technology Stack

| Component | Technology | Version/Config |
|-----------|------------|----------------|
| Agent Framework | LangGraph | v1 (StateGraph + create_agent) |
| Agent Patterns | create_agent ReAct (Analyzer), Learning (Memorizer), Orchestrator (Advisor) | create_agent + custom subgraphs |
| LLM | Ollama | llama3.1:8b (configurable per agent) |
| Embeddings | Ollama | nomic-embed-text (768d) |
| Vector Store | Milvus Lite | File-based |
| Configuration | YAML | agents.yaml + tools.yaml |
| Weather API | OpenWeatherMap | Free tier |
| Solar API | NREL PVWatts | v8 |
| Rates API | NREL Utility Rates | v3 + static TOU |
| Memory | JSON files | With timestamps |
| Testing | pytest + pytest-asyncio | - |
| Instrumentation | ContextForge | LangGraphInstrumentor |