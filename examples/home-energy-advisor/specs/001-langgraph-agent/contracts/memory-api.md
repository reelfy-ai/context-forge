# API Contract: Memory Store

**Feature**: 001-langgraph-agent | **Date**: 2026-01-26 | **Updated for LangGraph Native Memory**

## Overview

This document defines the memory architecture for the Home Energy Advisor agent. The agent uses **LangGraph's native memory primitives** for both short-term and long-term memory:

| Memory Type | LangGraph Primitive | Purpose |
|-------------|-------------------|---------|
| Short-term (session) | **Checkpointer** | Automatically persists graph state between invocations |
| Long-term (profile) | **Store** | Cross-session key-value storage for user profiles |

The legacy `MemoryStore` class (JSON file-based) remains available for testing and standalone use.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Advisor Graph                            │
│                                                                  │
│  Intake → Recall → [Analyze?] → Recommend → [Memorize?] → END   │
│              │                                    │              │
│              ▼                                    ▼              │
│     ┌─────────────────┐                 ┌─────────────────┐     │
│     │  LangGraph      │                 │  LangGraph      │     │
│     │  Store          │                 │  Store          │     │
│     │  (profile read) │                 │  (profile write)│     │
│     └─────────────────┘                 └─────────────────┘     │
│                                                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │     Checkpointer        │
              │  (auto-saves state      │
              │   after each node)      │
              └─────────────────────────┘
```

---

## Short-Term Memory: Checkpointer

LangGraph's Checkpointer automatically persists the entire graph state after each node execution. This eliminates the need for manual session management.

### Usage

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from src.agents.advisor import build_advisor_graph

# Create checkpointer (SQLite for persistence)
conn = sqlite3.connect("data/checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

# Build graph with checkpointer
graph = build_advisor_graph(checkpointer=checkpointer, store=store)

# Invoke with thread_id for session continuity
config = {"configurable": {"thread_id": "session-abc-123"}}
result = graph.invoke(input_state, config=config)
```

### Behavior

- **Automatic persistence**: State saved after every node execution
- **Session restoration**: Same `thread_id` restores previous state automatically
- **No manual message management**: `messages` list accumulates naturally
- **SQLite backend**: Supports concurrent access with `check_same_thread=False`

### Migration from Legacy MemoryStore

| Legacy Operation | LangGraph Equivalent |
|-----------------|---------------------|
| `MemoryStore.append_message()` | Automatic via checkpointer |
| `MemoryStore.get_session_messages()` | Restored automatically with `thread_id` |
| `MemoryStore.clear_session()` | Delete checkpoint by `thread_id` |
| `_persist_session` node | **Removed** — checkpointer handles this |

---

## Long-Term Memory: LangGraph Store

LangGraph's Store provides cross-session key-value storage for user profiles.

### Helper Functions

Located in `src/memory/helpers.py`:

```python
from langgraph.store.base import BaseStore
from src.memory.helpers import get_profile_from_store, save_profile_to_store

# Load profile
profile = get_profile_from_store(store, user_id="home_123")

# Save profile
save_profile_to_store(store, profile)
```

### Store Namespace Convention

Profiles are stored with namespace `("profiles", user_id)`:

```python
PROFILES_NAMESPACE = ("profiles",)

# Internal storage structure:
# namespace: ("profiles", "home_123")
# key: "profile"
# value: profile.model_dump(mode="json")
```

### Accessing Store from Nodes

Nodes receive the store as a parameter (injected by LangGraph runtime):

```python
from langgraph.store.base import BaseStore

def recall_node(state: AdvisorState, *, store: BaseStore) -> dict:
    """Load profile from LangGraph Store."""
    profile = get_profile_from_store(store, state["user_id"])
    return {"user_profile": profile}

def memorize_node(state: AdvisorState, *, store: BaseStore) -> dict:
    """Save updated profile to LangGraph Store."""
    save_profile_to_store(store, state["user_profile"])
    return {}
```

---

## Profile Staleness Detection

Staleness checking remains available via helper functions:

```python
from src.memory.helpers import get_section_staleness, get_all_stale_sections

# Check single section
staleness = get_section_staleness(profile, "equipment")
# Returns: {"days_old": 45.5, "is_stale": False}

# Get all stale sections
stale = get_all_stale_sections(profile)
# Returns: ["household"] if household.updated_at > 90 days
```

### Staleness Threshold

Default: **90 days**

Configurable via `src/memory/helpers.STALENESS_THRESHOLD_DAYS`

---

## Legacy MemoryStore (File-Based)

The original `MemoryStore` class remains available for testing and standalone use:

```python
from src.memory.store import MemoryStore

store = MemoryStore(data_dir="./data")

# Profile operations
store.save_profile(profile)
profile = store.load_profile("home_123")
store.update_field("home_123", "equipment.solar_capacity_kw", 12.0)

# Session operations (not needed with LangGraph checkpointer)
store.append_message("session_1", {"role": "human", "content": "Hello"})
messages = store.get_session_messages("session_1")
```

### File Structure (Legacy)

```
data/
├── profiles/
│   ├── home_123.json
│   └── home_456.json
└── sessions/
    ├── session_abc.json
    └── session_def.json
```

---

## Graph Compilation

### Factory Function

```python
from src.agents.advisor import create_advisor

# Create advisor with SQLite persistence
graph = create_advisor(data_dir="./data")

# Or build manually with custom store/checkpointer
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.sqlite import SqliteSaver
from src.agents.advisor import build_advisor_graph

store = InMemoryStore()
checkpointer = SqliteSaver(conn)
graph = build_advisor_graph(checkpointer=checkpointer, store=store)
```

### Store Options

| Store Type | Use Case |
|-----------|----------|
| `InMemoryStore` | Testing, development |
| Custom persistent store | Production (implement `BaseStore`) |

### Checkpointer Options

| Checkpointer | Use Case |
|-------------|----------|
| `None` | No persistence (stateless) |
| `SqliteSaver` | Local persistence |
| `PostgresSaver` | Production (multi-instance) |

---

## ContextForge Trace Integration

Memory operations emit trace steps for ContextForge evaluation:

```python
# recall_node emits:
{
    "step_type": "memory_read",
    "query": {"user_id": "home_123"},
    "results": [profile_data],
    "match_count": 1
}

# memorize_node emits:
{
    "step_type": "memory_write",
    "entity_type": "user_profile",
    "operation": "update",
    "data": {"equipment.solar_capacity_kw": 12.0}
}
```

Note: Trace emission requires ContextForge instrumentation (see `001-trace-capture` spec).

---

## Thread Safety

- **LangGraph Store**: Thread-safe by design
- **LangGraph Checkpointer**: Thread-safe (use `check_same_thread=False` for SQLite)
- **Legacy MemoryStore**: NOT thread-safe (use for single-user scenarios only)
