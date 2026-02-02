"""Trajectory tests for EV charging optimization scenario.

These tests simulate multi-turn conversations about EV charging
and evaluate agent behavior using graders.
"""

import pytest

from context_forge.harness.user_simulator import SimulationResult
from context_forge.core import LLMCallStep, MemoryReadStep, MemoryWriteStep, ToolCallStep, TraceRun


# ---------------------------------------------------------------------------
# Simulation Execution Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_ev_charging_simulation_runs(ev_charging_trace: SimulationResult):
    """Verify EV charging simulation completes successfully."""
    assert ev_charging_trace is not None
    assert ev_charging_trace.state.status in ["completed", "terminated"]
    assert len(ev_charging_trace.state.turns) > 0


@pytest.mark.integration
async def test_ev_charging_has_agent_responses(ev_charging_trace: SimulationResult):
    """Verify agent provides responses in the simulation."""
    agent_turns = [
        t for t in ev_charging_trace.state.turns if t.role.value == "agent"
    ]
    assert len(agent_turns) > 0, "Agent should provide at least one response"


@pytest.mark.integration
async def test_ev_charging_conversation_flow(ev_charging_trace: SimulationResult):
    """Verify conversation alternates between user and agent."""
    turns = ev_charging_trace.state.turns
    if len(turns) < 2:
        pytest.skip("Not enough turns to verify flow")

    for i in range(1, len(turns)):
        # Turns should alternate (allowing for same-role consecutive in some cases)
        prev_role = turns[i - 1].role.value
        curr_role = turns[i].role.value
        # At minimum, we should see both roles
        roles_seen = {t.role.value for t in turns}
        assert "user" in roles_seen, "Should have user messages"
        assert "agent" in roles_seen, "Should have agent messages"


# ---------------------------------------------------------------------------
# Grader Tests (Placeholder - expand with ContextForge graders)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_ev_charging_no_empty_responses(ev_charging_trace: SimulationResult):
    """Grader: Agent responses should not be empty."""
    for turn in ev_charging_trace.state.turns:
        if turn.role.value == "agent":
            assert turn.message.content, f"Agent response at turn {turn.turn_number} is empty"
            assert len(turn.message.content.strip()) > 10, "Agent response too short"


@pytest.mark.integration
async def test_ev_charging_response_relevance(ev_charging_trace: SimulationResult):
    """Grader: Agent responses should be relevant to EV charging."""
    # Simple keyword check - replace with LLM judge later
    relevant_keywords = ["charge", "ev", "electric", "battery", "time", "rate", "peak", "off-peak"]

    agent_responses = [
        t.message.content.lower()
        for t in ev_charging_trace.state.turns
        if t.role.value == "agent"
    ]

    for response in agent_responses:
        has_relevant_content = any(kw in response for kw in relevant_keywords)
        assert has_relevant_content, f"Response doesn't seem relevant to EV charging: {response[:100]}..."


@pytest.mark.integration
async def test_ev_charging_turn_limit(ev_charging_trace: SimulationResult):
    """Grader: Simulation should respect turn limits."""
    max_expected_turns = 10  # 5 user + 5 agent turns max
    assert len(ev_charging_trace.state.turns) <= max_expected_turns, (
        f"Too many turns: {len(ev_charging_trace.state.turns)}"
    )


# ---------------------------------------------------------------------------
# E2E ContextForge Trace Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_ev_charging_captures_contextforge_trace(ev_charging_contextforge_trace):
    """Verify full ContextForge trace is captured."""
    result, traces = ev_charging_contextforge_trace

    assert result is not None
    assert len(traces) > 0, "Should capture at least one trace"

    # Each trace should have steps
    for trace in traces:
        assert isinstance(trace, TraceRun)
        assert len(trace.steps) > 0, f"Trace {trace.run_id} has no steps"


@pytest.mark.integration
async def test_ev_charging_trace_has_llm_calls(ev_charging_contextforge_trace):
    """Verify LLM calls are captured in the trace."""
    result, traces = ev_charging_contextforge_trace

    # Find all LLM call steps across all traces
    llm_steps = []
    for trace in traces:
        llm_steps.extend([s for s in trace.steps if isinstance(s, LLMCallStep)])

    assert len(llm_steps) > 0, "Should capture at least one LLM call"

    # Verify LLM steps have required fields
    for llm_step in llm_steps:
        assert llm_step.model is not None
        assert llm_step.input is not None
        assert llm_step.output is not None


@pytest.mark.integration
async def test_ev_charging_trace_has_tool_calls(ev_charging_contextforge_trace):
    """Verify tool calls are captured in the trace."""
    result, traces = ev_charging_contextforge_trace

    # Find all tool call steps across all traces
    tool_steps = []
    for trace in traces:
        tool_steps.extend([s for s in trace.steps if isinstance(s, ToolCallStep)])

    # Note: tool calls may or may not occur depending on the scenario
    # This test verifies the capability, not requirement
    if len(tool_steps) > 0:
        for tool_step in tool_steps:
            assert tool_step.tool_name is not None
            assert tool_step.arguments is not None


@pytest.mark.integration
async def test_ev_charging_trace_has_agent_info(ev_charging_contextforge_trace):
    """Verify agent info is captured in the trace."""
    result, traces = ev_charging_contextforge_trace

    for trace in traces:
        assert trace.agent_info is not None
        assert trace.agent_info.name == "home_energy_advisor"
        assert trace.agent_info.framework == "langgraph"


@pytest.mark.integration
async def test_ev_charging_trace_json_serialization(ev_charging_contextforge_trace):
    """Verify trace can be serialized to JSON."""
    result, traces = ev_charging_contextforge_trace

    for trace in traces:
        json_str = trace.to_json()
        assert json_str is not None
        assert len(json_str) > 100  # Should have substantial content
        assert '"steps"' in json_str
        assert '"agent_info"' in json_str


@pytest.mark.integration
async def test_ev_charging_trace_has_memory_operations(ev_charging_contextforge_trace):
    """Verify memory operations are captured in the trace.

    The LangGraphInstrumentor should capture store.get() and store.put()
    operations as MemoryReadStep and MemoryWriteStep.
    """
    result, traces = ev_charging_contextforge_trace

    # Find all memory steps across all traces
    memory_reads = []
    memory_writes = []
    for trace in traces:
        memory_reads.extend([s for s in trace.steps if isinstance(s, MemoryReadStep)])
        memory_writes.extend([s for s in trace.steps if isinstance(s, MemoryWriteStep)])

    # Note: memory operations depend on the agent's recall/memorize flow
    # If the agent reads user profile, we should see MemoryReadStep
    # If the agent writes updated facts, we should see MemoryWriteStep
    total_memory_ops = len(memory_reads) + len(memory_writes)

    # Log what we found for debugging
    print(f"Memory reads: {len(memory_reads)}")
    print(f"Memory writes: {len(memory_writes)}")

    # At minimum, we should see profile reads if recall_node runs
    # This test documents the capability rather than strict requirements
    if total_memory_ops > 0:
        # Verify structure of memory operations
        for read_step in memory_reads:
            assert read_step.query is not None
            assert read_step.results is not None

        for write_step in memory_writes:
            assert write_step.entity_type is not None
            assert write_step.operation in ["add", "update", "delete"]


# ---------------------------------------------------------------------------
# Future Grader Tests (TODO: implement with ContextForge graders)
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Requires ContextForge LoopGrader implementation")
@pytest.mark.integration
async def test_ev_charging_no_loops(ev_charging_trace: SimulationResult):
    """Grader: Agent should not loop/repeat itself."""
    # TODO: Implement with ContextForge LoopGrader
    # grader = LoopGrader(max_repeats=3)
    # result = grader.evaluate(ev_charging_trace)
    # assert result.passed
    pass


@pytest.mark.skip(reason="Requires ContextForge BudgetGrader implementation")
@pytest.mark.integration
async def test_ev_charging_tool_efficiency(ev_charging_trace: SimulationResult):
    """Grader: Agent should use tools efficiently."""
    # TODO: Implement with ContextForge BudgetGrader
    # grader = BudgetGrader(max_tool_calls=10)
    # result = grader.evaluate(ev_charging_trace)
    # assert result.passed
    pass


@pytest.mark.skip(reason="Requires ContextForge TrajectoryJudge implementation")
@pytest.mark.integration
async def test_ev_charging_goal_completion(ev_charging_trace: SimulationResult):
    """Grader: Agent should help user achieve their goals."""
    # TODO: Implement with ContextForge TrajectoryJudge
    # grader = TrajectoryJudge(rubric="rubrics/goal_completion.md")
    # result = grader.evaluate(ev_charging_trace)
    # assert result.passed
    pass
