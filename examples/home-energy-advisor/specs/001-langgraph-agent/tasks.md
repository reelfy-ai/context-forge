# Tasks: Home Energy Advisor LangGraph Agent

**Input**: Design documents from `examples/home-energy-advisor/specs/001-langgraph-agent/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Tests included for critical paths (agent integration, memory, tools, knowledge).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Project root**: `examples/home-energy-advisor/`
- **Source**: `src/` (agents/, core/, nodes/, tools/, memory/, knowledge/, llm/)
- **Config**: `config/` (agents.yaml, tools.yaml)
- **Tests**: `tests/`
- **Data**: `data/`, `knowledge_base/`, `traces/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, configuration, and basic structure

- [x] T001 Create project directory structure per plan.md in examples/home-energy-advisor/
- [x] T002 Create pyproject.toml with dependencies (langgraph, langchain, langchain-ollama, pymilvus, httpx, pydantic, pydantic-settings, python-dotenv, pyyaml)
- [x] T003 Create requirements.txt from pyproject.toml dependencies
- [x] T004 [P] Create .env.example with API key placeholders in examples/home-energy-advisor/.env.example
- [x] T005 [P] Create .gitignore for Python, .env, data/, __pycache__ in examples/home-energy-advisor/.gitignore

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Configuration & Settings

- [x] T006 Create config/agents.yaml (advisor, analyzer, memorizer settings: model, temperature, thresholds)
- [x] T007 [P] Create config/tools.yaml (mode: live/mock, API endpoints, api_key_env references)
- [x] T008 Implement config loader in src/config.py (load YAML configs + env vars, expose Settings with Pydantic)
- [x] T009 Create src/__init__.py with package exports

### Core Infrastructure

- [x] T010 [P] Create src/core/__init__.py with exports
- [x] T011 [P] Implement Equipment Pydantic model in src/core/models.py (solar_capacity_kw, ev_model, ev_battery_kwh, has_battery_storage, heating_type, cooling_type, updated_at)
- [x] T012 [P] Implement Preferences Pydantic model in src/core/models.py (budget_priority, comfort_priority, green_priority, updated_at)
- [x] T013 [P] Implement Household Pydantic model in src/core/models.py (work_schedule, occupants, typical_usage_pattern, updated_at)
- [x] T014 [P] Implement Location Pydantic model in src/core/models.py (lat, lon, zip_code, utility_provider, rate_schedule)
- [x] T015 Implement UserProfile, ProfileNote, ExtractedFact models in src/core/models.py (per data-model.md)
- [x] T016 [P] Implement tool response models in src/core/models.py (WeatherForecast, RateSchedule, RatePeriod, SolarEstimate, RetrievedDocument)
- [x] T017 Create src/core/prompts.py (system prompts for advisor, analyzer, memorizer extract/summarize)

### LangGraph State Definitions

- [x] T018 Define AdvisorState TypedDict in src/core/state.py (user_id, session_id, message, messages, turn_count, user_profile, tool_observations, retrieved_docs, response, extracted_facts, should_memorize)
- [x] T019 [P] Add Analyzer configuration helper in src/core/state.py (AnalyzerConfig with system_prompt, recursion_limit; no custom TypedDict needed — create_agent manages state internally)
- [x] T020 [P] Define MemorizerState TypedDict in src/core/state.py (messages, user_profile, extracted_facts, validated_facts, summary, turns_to_summarize)

### LLM Wrapper

- [x] T021 Implement Ollama LLM wrapper in src/llm/ollama.py (ChatOllama initialization with per-agent model/temperature from config)
- [x] T022 [P] Implement Ollama embeddings wrapper in src/llm/ollama.py (OllamaEmbeddings with nomic-embed-text, 768 dimensions)
- [x] T023 Create src/llm/__init__.py with exports (get_llm, get_embeddings)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Energy Query (Priority: P1) 🎯 MVP

**Goal**: Agent responds to energy queries (EV charging, solar optimization) using profile data and external tools via create_agent native ReAct

**Independent Test**: Run `python main.py --query "When should I charge my EV?"` with mock tools and verify coherent response with rate schedule recommendations

### Tests for User Story 1

- [x] T024 [P] [US1] Create test fixtures in tests/conftest.py (mock profile, mock LLM responses, mock tool responses)
- [x] T025 [P] [US1] Create advisor agent integration test in tests/test_advisor_agent.py (test full flow with mocked dependencies)
- [x] T026 [P] [US1] Create analyzer agent test in tests/test_analyzer_agent.py (test create_agent tool calling: invoke with mock tools, verify tool_calls in messages)

### Advisor Agent (Orchestrator)

- [x] T027 [US1] Create src/nodes/__init__.py with node exports
- [x] T028 [US1] Implement intake_node in src/nodes/intake.py (parse user message, append to messages, increment turn_count)
- [x] T029 [US1] Implement recommend_node in src/nodes/recommend.py (generate final response using LLM with all context: profile, tool_observations, retrieved_docs)
- [x] T030 [US1] Create src/agents/__init__.py with exports
- [x] T031 [US1] Build Advisor StateGraph in src/agents/advisor.py (Intake → Recall → [Analyzer] → Recommend → [Memorizer?] → END)
- [x] T032 [US1] Implement conditional edge for Analyzer (skip if simple FAQ, enter for tool-requiring queries)
- [x] T033 [US1] Implement conditional edge for Memorizer (enter if should_memorize=True)

### Analyzer Agent (create_agent — Native ReAct)

- [x] T034 [US1] Create Analyzer system prompt in src/core/prompts.py (instruct LLM to use available tools to gather energy data for user queries)
- [x] T035 [US1] Build Analyzer in src/agents/analyzer.py using create_agent() from langchain.agents (model=ChatOllama per config, tools=[@tool functions], system_prompt, name="analyzer")

### Entry Point

- [x] T039 [US1] Create main.py CLI entry point with argparse (--query, --user-id, --trace, --output flags)
- [x] T040 [US1] Add basic interactive mode in main.py (input loop, graceful exit)

**Checkpoint**: At this point, Advisor orchestrates Analyzer (create_agent) with stub @tool functions, no memory

---

## Phase 4: User Story 2 - Multi-Session Memory (Priority: P1)

**Goal**: Agent persists user profiles across sessions and retrieves them on session start. Memorizer subgraph extracts facts and updates profile.

**Independent Test**: Create profile in Session 1, restart, verify profile loaded in Session 2 without re-entering data

### Tests for User Story 2

- [x] T041 [P] [US2] Create memory store unit tests in tests/test_memory_store.py (test load_profile, save_profile, update_field, staleness calculation)
- [x] T042 [P] [US2] Create memorizer agent test in tests/test_memorizer_agent.py (test extract→apply→summarize flow, verify timestamp refresh)

### Memory Store Implementation

- [x] T043 [US2] Implement MemoryStore class in src/memory/store.py (init with data_dir path)
- [x] T044 [US2] Implement load_profile in src/memory/store.py (read JSON, deserialize to UserProfile, return None if not exists)
- [x] T045 [US2] Implement save_profile in src/memory/store.py (atomic write with temp file, update updated_at timestamp)
- [x] T046 [US2] Implement update_field in src/memory/store.py (partial update with section-level timestamps)
- [x] T047 [US2] Implement get_field_staleness in src/memory/store.py (calculate days_old, is_stale flag with 90-day threshold)
- [x] T048 [US2] Implement session management in src/memory/store.py (get_session_messages, append_message, clear_session)
- [x] T049 [US2] Create src/memory/__init__.py with MemoryStore export

### Recall Node

- [x] T050 [US2] Implement recall_node in src/nodes/recall.py (load user profile from MemoryStore, set user_profile in state)

### Memorizer Agent (Learning Subgraph)

- [x] T051 [US2] Implement memorize_extract_node in src/nodes/memorize_extract.py (LLM analyzes conversation, outputs ExtractedFact[])
- [x] T052 [US2] Create fact extraction prompt in src/core/prompts.py (structured output: field, new_value, confidence, source_turn, source_text)
- [x] T053 [US2] Implement memorize_apply_node in src/nodes/memorize_apply.py (filter facts by confidence >= 0.7, apply to profile, refresh updated_at timestamps)
- [x] T054 [US2] Implement memorize_summarize_node in src/nodes/memorize_summarize.py (summarize turns > 20 into ProfileNote, append to profile.notes)
- [x] T055 [US2] Build Memorizer subgraph in src/agents/memorizer.py (Extract → Apply → Summarize → END)
- [x] T056 [US2] Wire Memorizer subgraph into Advisor (conditional edge: should_memorize=True)

### Demo Data

- [x] T057 [US2] Create demo profile data/profiles/home_123.json per data-model.md (intentionally stale household.updated_at — memorize never ran)
- [x] T058 [US2] Create data/profiles/ and data/sessions/ directories with .gitkeep

**Checkpoint**: At this point, Memorizer subgraph extracts facts, updates profile, and refreshes timestamps. Staleness is detectable when it doesn't run.

---

## Phase 5: User Story 3 - Tool Integration (Priority: P1)

**Goal**: Agent calls real external APIs (weather, rates, solar) via the Analyzer's @tool functions and incorporates results into recommendations

**Independent Test**: Ask about solar production today, verify weather API called with correct coordinates, response includes cloud cover impact

### Tests for User Story 3

- [x] T059 [P] [US3] Create mock tool implementations in src/tools/mock.py (mock_weather_forecast, mock_utility_rates, mock_solar_estimate with realistic data)
- [x] T060 [P] [US3] Create tool integration tests in tests/test_tools.py (test each tool with mock mode, verify response schema)

### Implementation for User Story 3

- [x] T061 [US3] Create src/tools/__init__.py with tool exports (list of @tool-decorated functions for create_agent)
- [x] T062 [US3] Implement get_weather_forecast tool in src/tools/weather.py (OpenWeatherMap API, calculate solar_hours from cloud_cover)
- [x] T063 [US3] Implement get_utility_rates tool in src/tools/rates.py (static TOU data for PG&E, SCE, SDG&E; NREL fallback)
- [x] T064 [US3] Implement get_solar_estimate tool in src/tools/solar.py (NREL PVWatts API with lat, lon, system_capacity_kw)
- [x] T065 [US3] Add mock mode conditional in each tool (use config/tools.yaml mode: mock to return mock data)
- [x] T066 [US3] Create ToolError exception class in src/tools/__init__.py (tool_name, message, retry_after)
- [x] T067 [US3] Implement graceful degradation in each tool (catch API errors, return cached/mock with is_fallback flag) [EC-001]
- [x] T068 [US3] Wire @tool functions into Analyzer create_agent() call in src/agents/analyzer.py (pass real tool implementations)
- [x] T069 [US3] Add latency and success/failure logging within each @tool function (captured automatically by LangGraphInstrumentor)

**Checkpoint**: At this point, Analyzer's create_agent calls real @tool functions with graceful fallback

---

## Phase 6: User Story 4 - Knowledge Base Retrieval (Priority: P2)

**Goal**: Agent retrieves relevant documents from knowledge base for educational queries

**Independent Test**: Ask "How do heat pumps work?", verify documents retrieved from Milvus, response references retrieved content

### Tests for User Story 4

- [ ] T070 [P] [US4] Create knowledge base tests in tests/test_knowledge.py (test embedding generation, test retrieval with test collection)

### Implementation for User Story 4

- [ ] T071 [US4] Create knowledge base source documents in knowledge_base/ (ev-charging.md, solar-basics.md, rate-optimization.md, heat-pump-guide.md, energy-efficiency-tips.md)
- [ ] T072 [US4] Implement MilvusStore class in src/knowledge/vectorstore.py (connect to Milvus Lite file, create_collection, retrieve)
- [ ] T073 [US4] Implement embedding generation in src/knowledge/embeddings.py (generate_embedding using OllamaEmbeddings)
- [ ] T074 [US4] Implement ingestion pipeline in src/knowledge/ingest.py (load markdown files, chunk text, generate embeddings, insert into Milvus)
- [ ] T075 [US4] Create scripts/ingest_knowledge_base.py (CLI to run ingestion, print progress)
- [ ] T076 [US4] Create src/knowledge/__init__.py with exports (MilvusStore, generate_embedding, ingest_documents)
- [ ] T077 [US4] Update recall_node in src/nodes/recall.py (embed query, retrieve relevant docs, set retrieved_docs in state)
- [ ] T078 [US4] Update recommend_node in src/nodes/recommend.py (include retrieved_docs in LLM context, track which docs were used)

**Checkpoint**: At this point, agent has full RAG capability with knowledge base

---

## Phase 7: Edge Case Handling (Priority: P1)

**Goal**: Agent handles edge cases gracefully (empty profiles, ambiguous input)

**Independent Test**: Start with no profile, verify onboarding flow prompts for essential info

### Implementation for Edge Cases

- [ ] T079 [US1] Implement new user detection in intake_node (check if profile exists) [EC-002]
- [ ] T080 [US1] Create onboarding prompt sequence in intake_node (location → utility → equipment) [EC-002]
- [ ] T081 [US1] Implement location clarification in intake_node (detect ambiguous location, ask for zip) [EC-003]

**Checkpoint**: At this point, agent handles new users and edge cases gracefully

---

## Phase 8: Instrumentation & Tracing (Priority: P1)

**Goal**: Agent traces are captured in ContextForge format for evaluation

**Independent Test**: Run query with --trace flag, verify trace JSON contains all step types

### Implementation for Instrumentation

- [ ] T082 Add ContextForge instrumentation setup in src/agents/advisor.py (LangGraphInstrumentor().instrument() before graph creation — covers advisor + subgraphs)
- [ ] T083 Add trace output handling in main.py (save trace to --output path when --trace flag set)
- [ ] T084 Implement step type mapping (ensure user_input, llm_call, tool_call, retrieval, memory_read, memory_write, state_change, final_output captured across all 3 agents per FR-041)

---

## Phase 9: Sample Traces & Evaluation (Priority: P1)

**Goal**: Pre-recorded traces demonstrate evaluation scenarios; evaluate.py produces expected results

**Independent Test**: Run `python evaluate.py traces/ev-charging-stale-memory.json`, verify HybridMemoryHygieneGrader FAIL (LLM judge detects missed fact)

### Implementation for Sample Traces

- [ ] T085 Create traces/ directory structure
- [ ] T086 [P] Create traces/ev-charging-good.json (all graders pass — Memorizer extracts facts, timestamps fresh, Analyzer exits cleanly)
- [ ] T087 [P] Create traces/ev-charging-stale-memory.json (HybridMemoryHygieneGrader FAIL: Memorizer didn't run, user fact not saved)
- [ ] T088 [P] Create traces/ev-charging-loop.json (LoopGrader FAIL: Analyzer calls weather API 4x with same args)
- [ ] T089 [P] Create traces/ev-charging-retrieval-waste.json (RetrievalRelevanceGrader WARN: 5 retrieved, 1 used)
- [ ] T090 Create scripts/generate_sample_traces.py (optional: generate traces programmatically)
- [ ] T091 Implement evaluate.py (load trace, run graders, print results)

**Checkpoint**: All evaluation scenarios demonstrable with sample traces

---

## Phase 10: Polish & Documentation

**Purpose**: Final documentation, cleanup, and validation

- [ ] T092 [P] Create README.md in examples/home-energy-advisor/ (overview, agent architecture, setup, usage, evaluation)
- [ ] T093 [P] Update quickstart.md with final commands and expected output
- [ ] T094 Code cleanup: add docstrings to public functions in agents/, core/, nodes/
- [ ] T095 Run Black/Ruff formatting on all source files
- [ ] T096 Run quickstart.md validation (follow steps end-to-end)
- [ ] T097 Verify all tests pass with `pytest tests/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - MVP target (includes Advisor + Analyzer agents)
- **User Story 2 (Phase 4)**: Depends on Foundational, can parallel with US1 (includes Memorizer agent)
- **User Story 3 (Phase 5)**: Depends on US1 (Analyzer create_agent must exist to wire real @tool functions)
- **User Story 4 (Phase 6)**: Depends on Foundational - P2 priority
- **Edge Cases (Phase 7)**: Depends on US1, US2 (onboarding and memory)
- **Instrumentation (Phase 8)**: Depends on US1 complete (agents exist)
- **Sample Traces (Phase 9)**: Depends on all US complete + instrumentation
- **Polish (Phase 10)**: Depends on all features complete

### User Story Dependencies

| Story | Can Start After | Integrates With | Agent Focus |
|-------|-----------------|-----------------|-------------|
| US1 (Basic Query) | Phase 2 | None | Advisor + Analyzer agents |
| US2 (Memory) | Phase 2 | US1 (recall_node) | Memorizer agent |
| US3 (Tools) | US1 (create_agent) | US1 (analyzer) | Analyzer @tool functions |
| US4 (Retrieval) | Phase 2 | US1, US2 (recall_node) | Recall node + Recommend |

### Within Each User Story

1. Tests written first (TDD approach)
2. Core state/models before logic
3. Node implementations before graph wiring
4. Subgraph integration last

### Parallel Opportunities

**Phase 1 (Setup)**: T004, T005 can run in parallel

**Phase 2 (Foundational)**: T006-T007, T010-T014, T016, T019-T020, T022 can run in parallel

**Phase 3 (US1)**: T024-T026 tests can run in parallel; T034 (prompt) is independent of T027-T033 (advisor nodes)

**Phase 4 (US2)**: T041-T042 tests can run in parallel; T051, T053-T054 memorizer nodes can run in parallel

**Phase 5 (US3)**: T059-T060 tests can run in parallel; T062-T064 tool implementations in parallel

**Phase 9 (Sample Traces)**: T086-T089 can run in parallel

---

## Parallel Example: Analyzer Setup (Phase 3)

```bash
# Create Analyzer system prompt (independent of create_agent wiring):
Task: T034 "Create Analyzer system prompt in src/core/prompts.py"

# Then build the Analyzer (depends on prompt + tools existing):
Task: T035 "Build Analyzer in src/agents/analyzer.py using create_agent()"
```

---

## Implementation Strategy

### MVP First (Advisor + Analyzer + Memory)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - core/, config/, state, models, LLM)
3. Complete Phase 3: User Story 1 (Advisor orchestrator + Analyzer create_agent)
4. Complete Phase 4: User Story 2 (Memorizer subgraph + memory persistence)
5. **STOP and VALIDATE**: Test with `python main.py` interactive mode
6. All 3 agents work end-to-end with mock tools

### Full Implementation

1. Add User Story 3 (real API tools wired into Analyzer)
2. Add User Story 4 (knowledge base RAG in Recall)
3. Add Instrumentation (Phase 8)
4. Create Sample Traces (Phase 9)
5. Polish & Documentation (Phase 10)

### Article Series Alignment

- **After MVP**: Can demonstrate 3-agent architecture for Article 2
- **After US3**: Can demonstrate create_agent tool integration for Article 3
- **After Phase 9**: Can demonstrate full evaluation scenarios for Article 4

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Mock mode (config/tools.yaml mode: mock) enables offline development and CI

---

## Summary

| Phase | Tasks | Parallel | Story | Agent Focus |
|-------|-------|----------|-------|-------------|
| 1. Setup | T001-T005 | 2 | - | - |
| 2. Foundational | T006-T023 | 10 | - | Core + Config + State |
| 3. US1 Basic Query | T024-T035, T039-T040 | 4 | P1 🎯 | Advisor + Analyzer |
| 4. US2 Memory + Offload | T041-T058 | 4 | P1 | Memorizer |
| 5. US3 Tools | T059-T069 | 4 | P1 | Analyzer tools |
| 6. US4 Retrieval | T070-T078 | 1 | P2 | Recall + Recommend |
| 7. Edge Cases | T079-T081 | 0 | P1 | Intake |
| 8. Instrumentation | T082-T084 | 0 | P1 | All agents |
| 9. Sample Traces | T085-T091 | 4 | P1 | Evaluation |
| 10. Polish | T092-T097 | 2 | - | Documentation |

**Total Tasks**: 94
**Parallel Opportunities**: 31
**MVP Scope**: Phases 1-4 (55 tasks, includes all 3 agents)

### Agent Architecture Summary

The project implements 3 agents as LangGraph subgraphs:

| Agent | Pattern | Graph File | Node Files |
|-------|---------|-----------|------------|
| **Advisor** | Orchestrator | `agents/advisor.py` | intake.py, recall.py, recommend.py |
| **Analyzer** | create_agent (native ReAct) | `agents/analyzer.py` | (managed internally by create_agent) |
| **Memorizer** | Learning + Semantic Memory | `agents/memorizer.py` | memorize_extract.py, memorize_apply.py, memorize_summarize.py |

### Evaluation Failure Modes

| Failure | Grader | Agent Involved | How It's Triggered |
|---------|--------|----------------|-------------------|
| Missed fact | HybridMemoryHygieneGrader | Memorizer | Memorizer doesn't run → user-stated facts not saved |
| Tool loop | LoopGrader | Analyzer | Analyzer calls same tool+args > 3 times |
| Retrieval waste | RetrievalRelevanceGrader | Recall (Advisor) | Retrieved docs not cited by Recommend |
| Budget overrun | BudgetGrader | Analyzer | Too many tool round-trips → tokens exceed budget |