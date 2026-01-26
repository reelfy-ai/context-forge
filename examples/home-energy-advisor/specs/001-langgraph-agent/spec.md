# Feature Specification: Home Energy Advisor LangGraph Agent

**Feature Branch**: `001-langgraph-agent`
**Created**: 2026-01-21
**Status**: Draft
**Priority**: P1 (Required for Article Series)

## Overview

A LangGraph-based agent that helps homeowners optimize energy use, solar production, EV charging, and electricity costs. This example demonstrates trajectory evaluation scenarios where **correct outputs mask behavioral problems** that only ContextForge can detect.

**Purpose**: Running example for the "Forging Better Agents" Medium article series.

### Architectural Position: Orchestrator, Not Optimizer

**Critical distinction**: The energy sector has used ML for optimization (forecasting, control loops, grid balancing) for decades. Those systems are deterministic, auditable, and regulator-trusted. **This agent does NOT replace that layer.**

Traditional ML + optimization already wins for core energy decisions:
- Deterministic and auditable
- Predictable under tight constraints
- Regulators trust it

Agentic AI shines **one layer above the optimizer** as:

> "Operator, negotiator, explainer, coordinator — not controller."

**Three-Layer Architecture**:

| Layer | Responsibility | Technology |
|-------|---------------|------------|
| **Layer 1: Energy Core** | Forecasting, optimization, control loops, hard constraints | Traditional ML/algorithms (out of scope) |
| **Layer 2: Agentic Orchestrator** | Goal negotiation, explanation, exception handling, user interaction | LLM agent (this example) |
| **Layer 3: Evaluation** | Decision trajectories, context usage, memory hygiene, behavioral consistency | ContextForge |

**Where this agent adds value** (not optimization):
- **Human-in-the-loop decisions**: Explain trade-offs, negotiate goals ("Charge now at higher cost, or wait?")
- **Cross-asset coordination**: Reason across EV, solar, battery, tariffs, weather, travel plans
- **Multi-objective, changing goals**: Handle "cost today, carbon this week, convenience tomorrow"
- **Failure handling**: Detect anomalies, reason about uncertainty, escalate with context

**Why this is perfect for ContextForge**: Outputs can look "correct" while behavioral errors compound invisibly. Safety + money are involved. Classic ML evals don't cover reasoning quality, context usage, or goal negotiation. Trajectory evaluation does.

## Clarifications

### Session 2026-01-21

- Q: Which LLM provider should the agent use? → A: Ollama only (local LLM, no API keys needed)
- Q: Are external API keys acceptable for tools? → A: Yes, free-tier APIs (weather, rates, solar) with keys are acceptable
- Q: Which Ollama model should be used? → A: Configurable with llama3.1:8b as documented default
- Q: How should memory be persisted? → A: JSON files supporting both short-term (session) and long-term (preferences) memory
- Q: How should embeddings for retrieval work? → A: Ollama embeddings via nomic-embed-text (local, same runtime)
- Q: What is the agent's architectural role? → A: Orchestrator/negotiator/explainer layer ABOVE traditional ML optimization (not replacing it)
- Q: What vector store for RAG retrieval? → A: Milvus Lite (local file-based) with pre-ingestion pipeline before agent starts

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Energy Query (Priority: P1)

As a **homeowner with solar panels and an EV**, I want to ask the advisor when to charge my car, so that I can minimize electricity costs while maximizing solar self-consumption.

**Why this priority**: The core use case that demonstrates the agent's value proposition.

**Acceptance Scenarios**:

1. **Given** a user with a configured profile (solar capacity, EV model, utility rate schedule), **When** they ask "When should I charge my EV?", **Then** the agent responds with a time recommendation based on their rate schedule and solar forecast
2. **Given** a first-time user, **When** they ask about charging, **Then** the agent prompts for essential profile information before recommending
3. **Given** a user with time-of-use rates, **When** they ask for charging advice, **Then** the agent references off-peak hours specific to their utility

---

### User Story 2 - Multi-Session Memory (Priority: P1)

As a **returning user**, I want the advisor to remember my preferences and equipment from previous conversations, so that I don't have to repeat information.

**Why this priority**: Core demonstration of compound memory across sessions (key article scenario).

**Acceptance Scenarios**:

1. **Given** a user who mentioned "I work from home" in Session 1, **When** they ask about charging in Session 5, **Then** the agent's recommendation accounts for their WFH schedule
2. **Given** a user who updated their EV model in a past session, **When** they ask about range, **Then** the agent uses the correct vehicle specifications
3. **Given** a user who updated facts across sessions (e.g., "gas heating" then "just installed a heat pump"), **When** the memorize node runs, **Then** the profile is updated with the latest value and the section timestamp is refreshed

---

### User Story 3 - Tool Integration (Priority: P1)

As a **user asking about current conditions**, I want the advisor to fetch real-time data from external sources, so that recommendations reflect actual weather, rates, and solar production.

**Why this priority**: Demonstrates tool_call capture and evaluation.

**Acceptance Scenarios**:

1. **Given** a user in San Francisco, **When** they ask about solar production today, **Then** the agent calls the weather API with correct coordinates and incorporates cloud cover into the response
2. **Given** a user on PG&E's EV-TOU-5 rate schedule, **When** they ask about charging costs, **Then** the agent retrieves current rate information
3. **Given** a user with a 6kW solar system, **When** they ask about production estimates, **Then** the agent uses solar calculation tools with their system parameters

---

### User Story 4 - Knowledge Base Retrieval (Priority: P2)

As a **user with general questions**, I want the advisor to access a knowledge base of energy efficiency tips, so that it can provide educational context beyond my personal data.

**Why this priority**: Demonstrates retrieval capture and waste detection.

**Acceptance Scenarios**:

1. **Given** a user asking "How do heat pumps work?", **When** the advisor processes the query, **Then** it retrieves relevant documents from the knowledge base
2. **Given** retrieved documents, **When** the agent formulates a response, **Then** it cites or references the used content
3. **Given** a query that requires both memory and retrieval, **When** the agent responds, **Then** it combines personal context with general knowledge

---

### Evaluation Scenarios (ContextForge Demonstration)

These scenarios exist specifically to demonstrate trajectory evaluation capabilities:

#### Scenario A - Stale Memory Detection (P1)

**Setup**:
- User registered 8 months ago with `work_schedule: "Office 9-5"`
- User mentioned "I started working from home" in a later session
- The memorize node **did not run** (or failed to extract this fact)
- User's profile still shows `work_schedule: "Office 9-5"` with `household.updated_at: 220 days ago`

**Query**: "When should I charge my EV?"

**Expected Output**: Recommendation based on commute schedule (APPEARS CORRECT)

**Trajectory Evaluation**:
- `MemoryHygieneGrader`: FAIL - memory field > 90 days stale, memorize node didn't refresh timestamp
- Output evaluation: PASS

**Demonstration Value**: Shows how trajectory evaluation catches what output evaluation misses. The memorize node should have extracted the "WFH" fact and updated the profile — but it didn't.

#### Scenario B - Retrieval Waste Detection (P1)

**Setup**:
- User asks about EV charging best practices
- Agent retrieves 5 documents from knowledge base
- Agent only references 1 document in response

**Query**: "What are best practices for EV charging at home?"

**Trajectory Evaluation**:
- `RetrievalRelevanceGrader`: WARN - usage_ratio 0.2 < 0.5 threshold
- ~1200 tokens wasted on unused context

**Demonstration Value**: Shows context pollution and token waste detection.

#### Scenario C - Tool Loop Detection (P2)

**Setup**:
- Agent in reasoning loop about weather uncertainty
- Calls weather API 4 times with identical parameters

**Query**: "Should I run my AC today given the forecast?"

**Trajectory Evaluation**:
- `LoopGrader`: FAIL - tool repeated > 3 times

**Demonstration Value**: Shows loop detection for stuck agents.

#### Scenario D - Budget Overrun (P2)

**Setup**:
- User with 18 months of conversation history
- Agent loads full history into context

**Query**: Simple question about current rates

**Trajectory Evaluation**:
- `BudgetGrader`: FAIL - tokens_used 8500 > max_tokens 5000

**Demonstration Value**: Shows resource constraint enforcement.

---

### Edge Cases

- **EC-001: External APIs unavailable** → Graceful degradation: return cached/mock data with disclaimer, or apologize and suggest retry
- **EC-002: Empty user profile (new user)** → Guided onboarding: prompt for location (zip code), utility provider, then optionally solar/EV equipment
- **EC-003: Ambiguous location** → Ask for zip code or city before proceeding with recommendations
- **EC-004: Large conversation histories** → Memory offload agent summarizes and extracts facts; raw history capped at 20 turns, older turns summarized to profile notes

## Requirements *(mandatory)*

### Functional Requirements

**Agent Core**
- **FR-001**: Agent MUST be implemented using LangGraph StateGraph
- **FR-002**: Agent MUST maintain persistent user profiles across sessions
- **FR-003**: Agent MUST support the following minimum AdvisorState fields: user_id, session_id, message, messages (conversation history), turn_count, user_profile, tool_observations, retrieved_docs, response, extracted_facts, should_memorize. Additional fields (weather_data, rate_data, solar_estimate) are defined in data-model.md.
- **FR-004**: Agent MUST implement three sub-agents within a single LangGraph StateGraph:
  - **Advisor (orchestrator)**: Custom StateGraph — Intake → Recall → [Analyzer] → Recommend → [Memorizer?]
  - **Analyzer (native ReAct)**: Built with `create_agent()` from `langchain.agents` using `@tool`-decorated functions
  - **Memorizer (learning subgraph)**: Custom StateGraph — Extract → Apply → Summarize
- **FR-005**: Agent MUST use Ollama as the LLM provider (local execution, no API keys required)
- **FR-006**: Agent MUST support configurable Ollama model with llama3.1:8b as the documented default
- **FR-007**: Analyzer MUST use `create_agent()` with `@tool`-decorated functions for native ReAct; loop depth controlled by `recursion_limit` at invocation
- **FR-008**: Analyzer MUST exit when LLM stops issuing tool_calls (natural completion) OR `recursion_limit` is reached (forced exit)
- **FR-009**: Agent configuration MUST be defined in YAML files (config/agents.yaml, config/tools.yaml)

**Memory Operations**
- **FR-010**: Agent MUST support two memory types:
  - **Short-term (session)**: Conversation history within current session
  - **Long-term (persistent)**: User profile, preferences, equipment across sessions
- **FR-011**: Agent MUST read user profile on each session start (memory_read)
- **FR-012**: Agent MUST write profile updates when user provides new information (memory_write)
- **FR-013**: Memory MUST be persisted as JSON files (human-readable, no database required)
- **FR-014**: Memory entries MUST include timestamps for staleness detection
- **FR-015**: Agent MUST implement a **memory offload mechanism** (memorize node) that:
  - Runs at session end or after a turn threshold (default: 10 turns)
  - Uses LLM to extract new facts about the user (equipment changes, preference updates, household info)
  - Applies extracted facts directly to the profile, refreshing `updated_at` timestamps
  - Summarizes old conversation turns (>20) into ProfileNotes for future context
- **FR-016**: Extracted facts MUST include source attribution (source_turn, source_text) for traceability
- **FR-017**: Agent MUST support these profile fields:
  - `equipment`: solar_capacity_kw, ev_model, ev_battery_kwh, has_battery_storage, heating_type
  - `preferences`: budget_priority (low/medium/high), comfort_priority, green_priority
  - `household`: work_schedule, occupants, typical_usage_pattern
  - `location`: lat, lon, utility_provider, rate_schedule

**Tool Integrations**
- **FR-020**: Agent MUST integrate with weather API (OpenWeatherMap or similar)
- **FR-021**: Agent MUST integrate with utility rate API (NREL or similar)
- **FR-022**: Agent MUST integrate with solar calculation API (NREL PVWatts or similar)
- **FR-023**: All tool calls MUST be captured with arguments and results
- **FR-024**: Tool calls SHOULD include latency and success/failure status

**Knowledge Base**
- **FR-030**: Agent MUST have access to a retrieval system with energy efficiency documents
- **FR-031**: Retrieval MUST use Milvus Lite as the vector store (local file-based, no server required)
- **FR-032**: Embeddings MUST use Ollama nomic-embed-text (768 dimensions, local)
- **FR-033**: A RAG ingestion pipeline MUST run before agent starts to load knowledge base documents
- **FR-034**: Retrieval queries and results MUST be captured in the trace
- **FR-035**: Retrieved documents MUST include relevance scores

**Instrumentation**
- **FR-040**: Agent MUST be instrumentable with `LangGraphInstrumentor().instrument()`
- **FR-041**: All step types MUST be captured: user_input, llm_call, tool_call, retrieval, memory_read, memory_write, state_change, final_output
- **FR-042**: Traces MUST be exportable to JSON in ContextForge format

**Sample Traces**
- **FR-050**: Repository MUST include pre-recorded sample traces demonstrating each evaluation scenario
- **FR-051**: Sample traces MUST include: ev-charging-good.json, ev-charging-stale-memory.json, ev-charging-loop.json, ev-charging-retrieval-waste.json

### Non-Functional Requirements

**Documentation**
- **NFR-001**: README MUST include setup instructions for API keys
- **NFR-002**: README MUST explain how to run the agent
- **NFR-003**: README MUST explain how to evaluate traces with ContextForge

**APIs**
- **NFR-010**: External APIs MUST be free tier compatible (no paid API keys required for demo)
- **NFR-011**: Agent MUST support mock/stub mode for APIs (for offline demos and CI)

**Portability**
- **NFR-020**: Example MUST work with Python 3.10+
- **NFR-021**: Example MUST have minimal dependencies beyond langchain/langgraph and context-forge

### Key Entities

- **UserProfile**: Persistent user data (equipment, preferences, household, location)
- **Equipment**: User's energy equipment (solar, EV, battery, HVAC)
- **ConversationHistory**: Past interactions for context
- **RateSchedule**: Utility time-of-use rate structure
- **WeatherForecast**: Current and forecasted weather conditions
- **SolarEstimate**: Estimated solar production for given system and conditions

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Agent produces coherent recommendations for EV charging, solar optimization, and cost reduction
- **SC-002**: Agent correctly retrieves and uses user profile data from previous sessions
- **SC-003**: `LangGraphInstrumentor().instrument()` captures all agent activities with no code changes
- **SC-004**: Sample traces demonstrate all four evaluation scenarios (stale memory, retrieval waste, loops, budget)
- **SC-005**: Running `evaluate.py` on sample traces produces expected grader results (PASS/FAIL/WARN as documented)
- **SC-006**: Example can be set up and run within 10 minutes using documented instructions

### Evaluation Demonstration

The example succeeds when:

1. **Stale Memory Scenario**: MemoryHygieneGrader correctly identifies 220-day-old work_schedule as stale
2. **Retrieval Waste Scenario**: RetrievalRelevanceGrader correctly calculates usage_ratio and flags waste
3. **Loop Scenario**: LoopGrader correctly detects repeated tool calls
4. **Budget Scenario**: BudgetGrader correctly flags token overruns

## Next Steps

Run `/speckit.plan` to generate:
- `plan.md` - Technical implementation plan
- `research.md` - Technology decisions and rationale
- `data-model.md` - UserProfile, Equipment, State entity definitions
- `contracts/` - API specifications for tools, memory, retrieval