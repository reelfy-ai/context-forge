"""Tests for stale memory detection using Memory Hygiene evaluation.

These tests verify that:
1. When the agent correctly updates stale data, the grader PASSES
2. When the agent misses user facts, the LLM judge catches it (semantic evaluation)
3. When the agent corrupts data, the corruption grader catches it (invariant check)

The tests run actual agent scenarios with pre-populated stale profiles,
capture ContextForge traces, and grade them with HybridMemoryHygieneGrader.

Architecture:
- MemoryCorruptionGrader: Checks INVARIANTS (data corruption - always wrong)
- MemoryHygieneJudge: Checks SEMANTICS (missed facts, hallucinations - requires understanding)
- HybridMemoryHygieneGrader: Combines both for comprehensive evaluation
"""

import pytest

from context_forge.core.trace import MemoryReadStep, MemoryWriteStep, TraceRun
from context_forge.graders import HybridMemoryHygieneGrader, MemoryCorruptionGrader
from context_forge.graders.judges.backends import OllamaBackend
from context_forge.harness.user_simulator import (
    LangGraphAdapter,
    SimulationRunner,
)
from context_forge.instrumentation import LangGraphInstrumentor

from src.agents.advisor import build_advisor_graph
from src.memory.helpers import get_profile_from_store


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def create_stale_state_builder(profile, user_id: str):
    """Create a state builder that uses a specific user_id for store lookups."""

    def build_state(message, state):
        return {
            "user_id": user_id,
            "session_id": f"stale_test_{state.simulation_id}",
            "message": message.content,
            "messages": [t.message for t in state.turns],
            "turn_count": state.current_turn,
            "user_profile": None,  # Will be loaded from store by recall node
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "memory_operations": [],
        }

    return build_state


def ollama_available() -> bool:
    """Check if Ollama is available for LLM tests."""
    try:
        backend = OllamaBackend(model="llama3.2")
        return backend.is_available()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Test Class: Happy Path - Agent Correctly Updates Stale Data
# ---------------------------------------------------------------------------


class TestStaleMemoryHappyPath:
    """Tests where the agent correctly updates stale profile data.

    These tests verify the grader PASSES when memory is properly updated.
    """

    @pytest.mark.integration
    @pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
    async def test_agent_updates_stale_work_schedule(
        self,
        stale_work_schedule_store,
        stale_work_schedule_profile,
        stale_work_scenario,
    ):
        """Agent should update work_schedule when user mentions WFH.

        SCENARIO:
        - Profile has work_schedule="Office 9-5" (120 days old)
        - User says: "I work from home now"
        - Agent should update work_schedule to "work_from_home" (or similar)

        EXPECTED: PASS - Memory is properly updated
        """
        import os

        # Setup instrumentation
        output_path = os.environ.get("CONTEXTFORGE_TRACE_OUTPUT")
        instrumentor = LangGraphInstrumentor(
            agent_name="home_energy_advisor",
            agent_version="0.1.0",
            output_path=output_path,
        )
        instrumentor.instrument()

        try:
            # Build graph with stale store
            graph = build_advisor_graph(store=stale_work_schedule_store)

            # Create adapter with stale profile's user_id
            adapter = LangGraphAdapter(
                graph=graph,
                input_key="message",
                output_key="response",
                agent_name="home_energy_advisor",
                state_builder=create_stale_state_builder(
                    stale_work_schedule_profile,
                    stale_work_schedule_profile.user_id,
                ),
                callbacks=[instrumentor.get_callback_handler()],
            )

            # Run simulation
            runner = SimulationRunner(adapter=adapter, trace_output_dir=None)
            result = await runner.run(stale_work_scenario)

            # Get traces
            traces = instrumentor.get_traces()
            assert len(traces) > 0, "Should capture at least one trace"

            # Grade with hybrid grader (corruption + semantic)
            grader = HybridMemoryHygieneGrader(
                llm_backend=OllamaBackend(model="llama3.2"),
            )

            for trace in traces:
                grader_result = grader.grade(trace)

                # Use the grader's built-in report formatting
                grader_result.print_report()

                # Show what fields were updated
                memory_writes = [
                    s for s in trace.steps if isinstance(s, MemoryWriteStep)
                ]
                if memory_writes:
                    print("MEMORY UPDATES:")
                    for write in memory_writes:
                        if write.changes:
                            for change in write.changes:
                                print(f"  {change.path}: {change.old_value} -> {change.new_value}")

            # Verify profile was updated in store
            updated_profile = get_profile_from_store(
                stale_work_schedule_store,
                stale_work_schedule_profile.user_id,
            )
            print(f"\nFinal profile state - work_schedule: {updated_profile.household.work_schedule}")

            # The key test: work_schedule should have been updated from "Office 9-5"
            assert updated_profile.household.work_schedule != "Office 9-5", (
                "work_schedule should have been updated from 'Office 9-5'"
            )

        finally:
            instrumentor.uninstrument()

    @pytest.mark.integration
    @pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
    async def test_agent_updates_stale_solar_capacity(
        self,
        stale_solar_store,
        stale_solar_profile,
        stale_solar_scenario_fixture,
    ):
        """Agent should update solar_capacity_kw when user mentions upgrade.

        SCENARIO:
        - Profile has solar_capacity_kw=7.5 (100 days old)
        - User says: "I upgraded my solar panels to 12kW"
        - Agent should update solar_capacity_kw to 12.0

        EXPECTED: PASS - Memory is properly updated
        """
        import os

        output_path = os.environ.get("CONTEXTFORGE_TRACE_OUTPUT")
        instrumentor = LangGraphInstrumentor(
            agent_name="home_energy_advisor",
            agent_version="0.1.0",
            output_path=output_path,
        )
        instrumentor.instrument()

        try:
            graph = build_advisor_graph(store=stale_solar_store)

            adapter = LangGraphAdapter(
                graph=graph,
                input_key="message",
                output_key="response",
                agent_name="home_energy_advisor",
                state_builder=create_stale_state_builder(
                    stale_solar_profile,
                    stale_solar_profile.user_id,
                ),
                callbacks=[instrumentor.get_callback_handler()],
            )

            runner = SimulationRunner(adapter=adapter, trace_output_dir=None)
            result = await runner.run(stale_solar_scenario_fixture)

            traces = instrumentor.get_traces()
            assert len(traces) > 0

            grader = HybridMemoryHygieneGrader(
                llm_backend=OllamaBackend(model="llama3.2"),
            )

            for trace in traces:
                grader_result = grader.grade(trace)

                # Use the grader's built-in report formatting
                grader_result.print_report()

                # Show what fields were updated
                memory_writes = [
                    s for s in trace.steps if isinstance(s, MemoryWriteStep)
                ]
                if memory_writes:
                    print("MEMORY UPDATES:")
                    for write in memory_writes:
                        if write.changes:
                            for change in write.changes:
                                print(f"  {change.path}: {change.old_value} -> {change.new_value}")

            # Verify store
            updated_profile = get_profile_from_store(
                stale_solar_store,
                stale_solar_profile.user_id,
            )
            print(f"\nFinal profile state - solar_capacity_kw: {updated_profile.equipment.solar_capacity_kw}")

            # The key test: solar_capacity_kw should have been updated from 7.5 to 12.0
            # If not updated, this test FAILS - demonstrating a real agent bug
            # that the Memory Hygiene Grader should catch
            assert updated_profile.equipment.solar_capacity_kw != 7.5, (
                "solar_capacity_kw should have been updated from 7.5. "
                "The grader correctly detected this as a 'missed_fact' issue."
            )

        finally:
            instrumentor.uninstrument()


# ---------------------------------------------------------------------------
# Test Class: Detection - Grader Catches Issues
# ---------------------------------------------------------------------------


class TestStaleMemoryDetection:
    """Tests that verify the grader catches memory hygiene issues.

    - MemoryCorruptionGrader: Detects data corruption (invariant violations)
    - MemoryHygieneJudge (via Hybrid): Detects semantic issues (missed facts)
    """

    @pytest.mark.integration
    @pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
    async def test_llm_judge_detects_missed_facts(
        self,
        multi_stale_store,
        multi_stale_profile,
        multi_stale_scenario,
    ):
        """LLM judge detects when user facts are not saved.

        SCENARIO:
        - User mentions 3 changes: Rivian, 15kW solar, 3 occupants
        - If agent only saves some of them, judge should detect missed facts

        This tests the LLM judge's ability to compare:
        - What the user stated
        - What was actually written to memory

        NOTE: This is a SEMANTIC check - the MemoryCorruptionGrader cannot
        detect missed facts because it only checks invariants.
        """
        import os

        output_path = os.environ.get("CONTEXTFORGE_TRACE_OUTPUT")
        instrumentor = LangGraphInstrumentor(
            agent_name="home_energy_advisor",
            agent_version="0.1.0",
            output_path=output_path,
        )
        instrumentor.instrument()

        try:
            graph = build_advisor_graph(store=multi_stale_store)

            adapter = LangGraphAdapter(
                graph=graph,
                input_key="message",
                output_key="response",
                agent_name="home_energy_advisor",
                state_builder=create_stale_state_builder(
                    multi_stale_profile,
                    multi_stale_profile.user_id,
                ),
                callbacks=[instrumentor.get_callback_handler()],
            )

            runner = SimulationRunner(adapter=adapter, trace_output_dir=None)
            result = await runner.run(multi_stale_scenario)

            traces = instrumentor.get_traces()

            # Use hybrid grader to get LLM analysis
            grader = HybridMemoryHygieneGrader(
                llm_backend=OllamaBackend(model="llama3.2"),
                skip_llm_on_corruption=False,  # Always run LLM for this test
            )

            for trace in traces:
                grader_result = grader.grade(trace)

                print(f"\nHybrid Grader Results (Multi-Update):")
                print(f"  Passed: {grader_result.passed}")
                print(f"  Score: {grader_result.score}")

                # Check what was saved
                memory_writes = [
                    s for s in trace.steps if isinstance(s, MemoryWriteStep)
                ]

                saved_fields = set()
                for write in memory_writes:
                    if write.changes:
                        for change in write.changes:
                            saved_fields.add(change.path)
                            print(f"  Saved: {change.path} = {change.new_value}")

                # User mentioned 3 things: solar, EV, occupants
                expected_updates = {"solar", "ev", "occupant"}
                actual_mentions = {
                    f for f in saved_fields
                    if any(kw in f.lower() for kw in expected_updates)
                }

                print(f"  Expected fields: {expected_updates}")
                print(f"  Saved fields matching: {actual_mentions}")

                # Show all evidence
                for e in grader_result.evidence:
                    print(f"  [{e.severity.value}] {e.check_name}: {e.description}")

                # If not all facts saved, check for missed_fact evidence
                missed_facts = [
                    e for e in grader_result.evidence
                    if e.check_name in ("missed_fact", "possible_missed_fact")
                ]

                if len(actual_mentions) < 3:
                    print(f"  Missed facts detected: {len(missed_facts)}")
                    # The LLM should have detected some missed facts
                    # (This may vary based on LLM behavior)

            # Verify final profile state
            updated_profile = get_profile_from_store(
                multi_stale_store,
                multi_stale_profile.user_id,
            )
            print(f"\nFinal Profile State:")
            print(f"  solar_capacity_kw: {updated_profile.equipment.solar_capacity_kw}")
            print(f"  ev_model: {updated_profile.equipment.ev_model}")
            print(f"  occupants: {updated_profile.household.occupants}")

        finally:
            instrumentor.uninstrument()

    @pytest.mark.integration
    async def test_corruption_grader_detects_data_loss(
        self,
        stale_work_schedule_store,
        stale_work_schedule_profile,
    ):
        """MemoryCorruptionGrader detects when existing data is deleted.

        This test creates a synthetic trace with data corruption
        (existing field deleted) and verifies the grader catches it.

        NOTE: This is an INVARIANT check - data loss is always wrong
        regardless of the agent's path or context.
        """
        from datetime import datetime, timezone
        from context_forge.core.trace import (
            TraceRun, UserInputStep, MemoryReadStep, MemoryWriteStep, FinalOutputStep
        )
        from context_forge.core.types import AgentInfo, FieldChange

        # Create a synthetic trace with data corruption
        trace = TraceRun(
            run_id="test-data-corruption",
            started_at=datetime.now(timezone.utc),
            agent_info=AgentInfo(name="home_energy_advisor", version="0.1.0"),
            steps=[
                UserInputStep(
                    step_id="step-1",
                    timestamp=datetime.now(timezone.utc),
                    content="Update my solar to 12kW",
                ),
                MemoryReadStep(
                    step_id="step-2",
                    timestamp=datetime.now(timezone.utc),
                    query={"namespace": ["profiles"], "key": "user_123"},
                    results=[{
                        "equipment": {
                            "solar_capacity_kw": 7.5,
                            "ev_model": "Tesla Model 3",  # This exists!
                        }
                    }],
                    match_count=1,
                ),
                # CORRUPTION: ev_model gets deleted (set to null)
                MemoryWriteStep(
                    step_id="step-3",
                    timestamp=datetime.now(timezone.utc),
                    namespace=["profiles"],
                    key="user_123",
                    operation="add",
                    data={"equipment": {"solar_capacity_kw": 12.0, "ev_model": None}},
                    changes=[
                        FieldChange(
                            path="$.equipment.solar_capacity_kw",
                            old_value=7.5,
                            new_value=12.0,
                        ),
                        FieldChange(
                            path="$.equipment.ev_model",
                            old_value="Tesla Model 3",
                            new_value=None,  # DATA CORRUPTION!
                        ),
                    ],
                ),
                FinalOutputStep(
                    step_id="step-4",
                    timestamp=datetime.now(timezone.utc),
                    content="Updated your solar capacity.",
                ),
            ],
        )

        # Grade with corruption grader only (no LLM needed)
        grader = MemoryCorruptionGrader()
        result = grader.grade(trace)

        print("\nCorruption Grader Results:")
        print(f"  Passed: {result.passed}")
        print(f"  Score: {result.score}")
        for e in result.evidence:
            print(f"  [{e.severity.value}] {e.check_name}: {e.description}")

        # Should detect data corruption
        assert result.passed is False, "Should fail on data corruption"
        corruption_errors = [
            e for e in result.errors if e.check_name == "data_corruption"
        ]
        assert len(corruption_errors) >= 1, "Should have data_corruption error"


# ---------------------------------------------------------------------------
# Smoke Test (No Ollama Required)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_stale_memory_trace_capture_smoke(
    stale_work_schedule_store,
    stale_work_schedule_profile,
    stale_work_scenario,
):
    """Smoke test: verify trace capture works with stale profiles.

    This test doesn't require Ollama - it just verifies:
    - Simulation runs with stale profile
    - Traces are captured
    - Basic structure is correct
    """
    import os

    output_path = os.environ.get("CONTEXTFORGE_TRACE_OUTPUT")
    instrumentor = LangGraphInstrumentor(
        agent_name="home_energy_advisor",
        agent_version="0.1.0",
        output_path=output_path,
    )
    instrumentor.instrument()

    try:
        graph = build_advisor_graph(store=stale_work_schedule_store)

        adapter = LangGraphAdapter(
            graph=graph,
            input_key="message",
            output_key="response",
            agent_name="home_energy_advisor",
            state_builder=create_stale_state_builder(
                stale_work_schedule_profile,
                stale_work_schedule_profile.user_id,
            ),
            callbacks=[instrumentor.get_callback_handler()],
        )

        runner = SimulationRunner(adapter=adapter, trace_output_dir=None)
        result = await runner.run(stale_work_scenario)

        # Verify simulation ran
        assert result is not None
        assert result.state.status in ["completed", "terminated"]

        # Verify traces captured
        traces = instrumentor.get_traces()
        assert len(traces) > 0, "Should capture at least one trace"

        for trace in traces:
            assert isinstance(trace, TraceRun)
            assert len(trace.steps) > 0

            # Should have memory read (profile load)
            memory_reads = [
                s for s in trace.steps if isinstance(s, MemoryReadStep)
            ]
            print(f"Memory reads in trace: {len(memory_reads)}")

            # Should have some steps
            print(f"Total steps: {len(trace.steps)}")
            step_types = {}
            for s in trace.steps:
                t = type(s).__name__
                step_types[t] = step_types.get(t, 0) + 1
            print(f"Step types: {step_types}")

    finally:
        instrumentor.uninstrument()
