# Implementation Plan: Home Energy Advisor LangGraph Agent

**Branch**: `001-langgraph-agent` | **Date**: 2026-01-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `examples/home-energy-advisor/specs/001-langgraph-agent/spec.md`

## Summary

Build a LangGraph-based agent that helps homeowners optimize energy use, demonstrating trajectory evaluation scenarios for the ContextForge Medium article series. The agent operates as an **orchestration layer** (negotiator, explainer, coordinator) above traditional ML optimization — not replacing proven energy optimization systems.

**Key Technical Decisions**:
- LLM: Ollama (llama3.1:8b default, configurable)
- Vector Store: Milvus Lite (local file-based)
- Embeddings: Ollama nomic-embed-text (768 dimensions)
- Memory: JSON files (short-term session + long-term profile)
- External APIs: OpenWeatherMap, NREL (free tier)

## Technical Context

**Language/Version**: Python 3.10+ (per constitution)
**Primary Dependencies**: LangGraph, LangChain, Ollama, pymilvus, httpx, PyYAML
**Storage**: JSON files (memory), Milvus Lite file (vectors)
**Testing**: pytest with pytest-asyncio
**Target Platform**: Local development (macOS, Linux)
**Project Type**: Single project (example/demo)
**Performance Goals**: Response within 10s for typical queries
**Constraints**: No paid API keys required; fully local LLM execution
**Scale/Scope**: Single-user demo with persistent profile across sessions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Framework Agnosticism | N/A | This is an example agent, not a grader |
| II. Traces as First-Class Citizens | PASS | Agent produces ContextForge-compatible traces |
| III. Multi-Level Integration | PASS | Uses Level 2 (LangGraphInstrumentor) |
| IV. Spec-Driven Development | PASS | Spec completed before implementation |
| V. CI-Safe by Design | PASS | Mock mode for APIs; sample traces included |
| VI. Grader Quality Standards | N/A | Example agent, not a grader |
| VII. Local-First, Ollama-First | PASS | Ollama for LLM + embeddings; no cloud required |

**Technical Constraints**:
- [x] Python 3.10+
- [x] Type hints for public APIs
- [x] Pydantic for data models
- [ ] Black/Ruff formatting (will apply)
- [x] No heavy runtime dependencies in core

## Project Structure

### Documentation (this feature)

```text
examples/home-energy-advisor/specs/001-langgraph-agent/
├── spec.md              # Feature specification (DONE)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output
    ├── tools-api.md
    └── memory-api.md
```

### Source Code

```text
examples/home-energy-advisor/
├── README.md                  # Setup and usage instructions
├── pyproject.toml             # Package configuration
├── requirements.txt           # Python dependencies
├── .env.example               # API key template
│
├── config/                    # YAML configuration
│   ├── agents.yaml            # Agent behavior (models, temperatures, thresholds)
│   └── tools.yaml             # Tool endpoints, mock mode, API keys ref
│
├── src/
│   ├── __init__.py
│   ├── config.py              # Loads YAML configs + env vars
│   │
│   ├── agents/                # Agent graph definitions
│   │   ├── __init__.py
│   │   ├── advisor.py         # Main orchestrator graph (Intake→Recall→[Analyzer]→Recommend→[Memorizer?])
│   │   ├── analyzer.py        # create_agent() with @tool-decorated tools (native ReAct loop)
│   │   └── memorizer.py       # Memory offload subgraph (Extract→Apply→Summarize)
│   │
│   ├── core/                  # Shared infrastructure
│   │   ├── __init__.py
│   │   ├── state.py           # AdvisorState, MemorizerState
│   │   ├── models.py          # Pydantic models (UserProfile, Equipment, etc.)
│   │   └── prompts.py         # System prompts + extraction templates
│   │
│   ├── nodes/                 # Node implementations
│   │   ├── __init__.py
│   │   ├── intake.py          # Parse input, detect intent, onboarding detection
│   │   ├── recall.py          # Load profile + RAG retrieval
│   │   ├── recommend.py       # Generate response using all context
│   │   ├── memorize_extract.py    # Extract facts from conversation (LLM)
│   │   ├── memorize_apply.py      # Apply facts to profile, refresh timestamps
│   │   └── memorize_summarize.py  # Summarize old turns into ProfileNotes
│   │
│   ├── tools/                 # External API integrations
│   │   ├── __init__.py
│   │   ├── weather.py         # OpenWeatherMap integration
│   │   ├── rates.py           # NREL Utility Rates + static TOU
│   │   ├── solar.py           # NREL PVWatts integration
│   │   └── mock.py            # Mock implementations for testing/CI
│   │
│   ├── memory/                # Persistence layer
│   │   ├── __init__.py
│   │   └── store.py           # MemoryStore (JSON file I/O)
│   │
│   ├── knowledge/             # RAG system
│   │   ├── __init__.py
│   │   ├── vectorstore.py     # Milvus Lite wrapper
│   │   ├── embeddings.py      # Ollama embeddings
│   │   └── ingest.py          # Ingestion pipeline
│   │
│   └── llm/                   # LLM wrappers
│       ├── __init__.py
│       └── ollama.py          # ChatOllama + OllamaEmbeddings
│
├── knowledge_base/            # Source documents for RAG
│   ├── ev-charging.md
│   ├── solar-basics.md
│   ├── rate-optimization.md
│   ├── heat-pump-guide.md
│   └── energy-efficiency-tips.md
│
├── data/                      # Runtime data (gitignored except demo profile)
│   ├── profiles/
│   │   └── home_123.json      # Demo user (intentionally stale)
│   ├── sessions/
│   └── milvus.db              # Vector store file
│
├── traces/                    # Sample trajectories for evaluation
│   ├── ev-charging-good.json
│   ├── ev-charging-stale-memory.json
│   ├── ev-charging-loop.json
│   └── ev-charging-retrieval-waste.json
│
├── scripts/
│   ├── ingest_knowledge_base.py   # Run before first use
│   └── generate_sample_traces.py  # Create demo traces
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Fixtures (mock APIs, test profiles)
│   ├── test_advisor_agent.py      # Main graph integration tests
│   ├── test_analyzer_agent.py     # create_agent tool calling tests
│   ├── test_memorizer_agent.py    # Memory offload tests
│   ├── test_memory_store.py       # Memory store tests
│   ├── test_tools.py              # Tool integration tests
│   └── test_knowledge.py          # RAG pipeline tests
│
├── evaluate.py                # Run ContextForge evaluation on traces
└── main.py                    # CLI entry point
```

**Structure Decision**: Three-agent architecture within a single LangGraph StateGraph. The `agents/` directory holds graph definitions (orchestration logic), `core/` holds shared state and models, `nodes/` holds individual node implementations. The Analyzer uses `create_agent()` from LangGraph v1 (native ReAct loop with `@tool`-decorated functions), eliminating the need for custom react nodes. This separates *what the agents do* from *how they are wired together*.

## Agent Architecture

### Agents and Patterns

| Agent | Pattern | Implementation | LLM Usage |
|-------|---------|----------------|-----------|
| **Advisor** | Planning (orchestrator) | Custom StateGraph (Intake→Recall→Analyzer→Recommend→Memorizer) | 1 LLM call (recommend) |
| **Analyzer** | ReAct (native tool calling) | `create_agent()` with `@tool`-decorated functions | N LLM calls (1 per iteration, recursion_limit controls max) |
| **Memorizer** | Learning + Semantic Memory | Custom StateGraph (Extract→Apply→Summarize) | 1-2 LLM calls (extract + summarize) |

### Flow Diagram

```
User Message
     │
     ▼
┌──────────┐
│  Intake   │  Parse input, detect intent, append to messages
└────┬─────┘
     │
     ▼
┌──────────┐
│  Recall   │  Load profile, RAG retrieval (if knowledge query)
└────┬─────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  Analyzer (create_agent — native ReAct)              │
│                                                      │
│  ┌─────────────┐         ┌──────────────┐           │
│  │   Agent      │────────▶│   ToolNode   │           │
│  │ (LLM call)   │◀────────│ (execute @tool)│          │
│  └──────┬──────┘         └──────────────┘           │
│         │ no tool_calls                              │
│         ▼                                            │
│    ┌────────┐                                        │
│    │  END   │                                        │
│    └────────┘                                        │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌────────────┐
│ Recommend   │  Generate response using all context
└────┬───────┘
     │
     ▼
┌──────────────────┐
│ should_memorize? │
└───┬──────────┬───┘
   yes         no
    │           │
    ▼           ▼
┌──────────────────────────────────────────────┐
│  Memorizer Subgraph                           │  ┌─────┐
│                                               │  │ END │
│  ┌──────────┐  ┌─────────┐  ┌───────────┐   │  └─────┘
│  │ Extract   │─▶│  Apply  │─▶│ Summarize │   │
│  │ (LLM)    │  │(profile)│  │ (old turns)│   │
│  └──────────┘  └─────────┘  └───────────┘   │
└──────────────────────────────────────────────┘
     │
     ▼
┌─────┐
│ END │
└─────┘
```

### Agent Responsibilities

**Advisor Agent** (`agents/advisor.py`):
- Owns the top-level StateGraph: Intake → Recall → [Analyzer] → Recommend → [Memorizer?]
- Routes to Analyzer subgraph only when tools are needed (simple FAQ can skip)
- Decides if Memorizer should run (session end, turn threshold >= 10, explicit user request)
- Generates the final user-facing recommendation

**Analyzer Agent** (`agents/analyzer.py`):
- Built with `create_agent()` from `langchain.agents` (LangGraph v1 native ReAct)
- Tools are `@tool`-decorated async functions (weather, rates, solar)
- LLM automatically decides which tools to call and processes results
- Native 2-node loop: Agent (LLM) → ToolNode (execute) → Agent → ... → END
- Exit: LLM stops issuing tool_calls, or `recursion_limit` reached at invocation
- LoopGrader evaluates: same tool+args called > 3 times = stuck
- `LangGraphInstrumentor` captures all tool_call steps automatically via `@tool`

**Memorizer Agent** (`agents/memorizer.py`):
- Implements Learning pattern as a LangGraph subgraph
- Extract node: LLM analyzes conversation, outputs `ExtractedFact[]`
- Apply node: Updates profile fields, refreshes `updated_at` timestamps
- Summarize node: Compresses turns > 20 into ProfileNotes
- HybridMemoryHygieneGrader evaluates: if this agent doesn't run, user-stated facts won't be saved (LLM judge detects missed facts)

### Configuration (YAML)

**config/agents.yaml**:
```yaml
advisor:
  model: llama3.1:8b
  temperature: 0.7

analyzer:
  model: llama3.1:8b
  temperature: 0.3
  recursion_limit: 10  # Max LangGraph steps (agent→tool round-trips)

memorizer:
  model: llama3.1:8b
  temperature: 0.2
  confidence_threshold: 0.7
  turn_threshold: 10
  max_turns_before_summary: 20
```

**config/tools.yaml**:
```yaml
mode: live  # or "mock" for testing/CI

weather:
  provider: openweathermap
  endpoint: https://api.openweathermap.org/data/2.5
  api_key_env: OPENWEATHER_API_KEY

rates:
  provider: nrel
  endpoint: https://developer.nrel.gov/api/utility_rates/v3
  api_key_env: NREL_API_KEY

solar:
  provider: nrel_pvwatts
  endpoint: https://developer.nrel.gov/api/pvwatts/v8
  api_key_env: NREL_API_KEY
```

---

## Complexity Tracking

No constitution violations requiring justification.

## Phase 0: Research Topics

1. **LangGraph StateGraph patterns** - Best practices for multi-node agent workflows
2. **LangGraph subgraphs** - How to compose sub-agents within a parent graph (state passing, entry/exit)
3. **`create_agent()` pattern** - LangGraph v1 native ReAct via `langchain.agents.create_agent` with `@tool` functions
4. **Ollama integration with LangChain** - ChatOllama and OllamaEmbeddings configuration
5. **Milvus Lite usage** - Local file-based vector store setup
6. **OpenWeatherMap API** - Free tier endpoints and rate limits
7. **NREL APIs** - PVWatts and Utility Rates API authentication and usage
8. **ContextForge instrumentation** - LangGraphInstrumentor integration patterns
9. **YAML configuration loading** - PyYAML or pydantic-settings with YAML support

## Phase 1: Design Artifacts

### Deliverables

1. **research.md** - Technology decisions with rationale
2. **data-model.md** - Pydantic models for UserProfile, Equipment, State, etc.
3. **contracts/tools-api.md** - Tool function signatures and schemas
4. **contracts/memory-api.md** - Memory store interface
5. **quickstart.md** - Setup and run instructions

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | Ollama | Local-first, no API keys, aligns with constitution |
| Model | llama3.1:8b (configurable) | Balance of capability and hardware requirements |
| Vector Store | Milvus Lite | Local file-based, no server, proven pattern |
| Embeddings | nomic-embed-text | 768 dims, runs in Ollama, good retrieval quality |
| Memory Persistence | JSON files | Human-readable, no database setup, simple |
| External APIs | OpenWeatherMap, NREL | Free tier, no paid keys required |
| Agent Pattern (main) | Planning/Orchestrator | Routes between subgraphs, owns user interaction |
| Agent Pattern (tools) | `create_agent()` native ReAct | LangGraph v1 native tool calling with `@tool`; automatic trace capture |
| Agent Pattern (memory) | Learning + Semantic Memory | Introspective fact extraction, profile updates |
| Configuration | YAML files (config/) | Easy to tune without code changes, supports eval scenarios |
| Subgraph vs Separate | LangGraph subgraphs | Single entry point, shared state, simpler debugging |

## Next Steps

After Phase 1 artifacts are complete, run `/speckit.tasks` to generate `tasks.md` with implementation work items.