"""Simulation runner for orchestrating user-agent conversations."""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Union

from langchain_core.messages import HumanMessage

from .adapters.base import AgentAdapter
from .models import (
    ConversationRole,
    SimulationResult,
    SimulationState,
    SimulationTurn,
)
from .persona import Persona
from .scenario import GenerativeScenario, Scenario, ScriptedScenario
from .simulator import LLMUserSimulator, ScriptedUserSimulator, UserSimulator


class SimulationRunner:
    """Orchestrates simulation runs between user simulator and agent adapter.

    Handles the conversation loop, trace capture integration, and
    termination conditions.

    Example usage:
        from context_forge.harness import SimulationRunner, LangGraphAdapter

        adapter = LangGraphAdapter(graph=my_graph, ...)
        scenario = GenerativeScenario(...)

        runner = SimulationRunner(
            adapter=adapter,
            trace_output_dir="./traces",
        )

        result = await runner.run(scenario)
    """

    def __init__(
        self,
        adapter: AgentAdapter,
        trace_output_dir: Optional[Union[str, Path]] = None,
        default_max_turns: int = 20,
    ):
        """Initialize the simulation runner.

        Args:
            adapter: Framework adapter for agent invocation
            trace_output_dir: Directory for trace files
            default_max_turns: Default maximum turns if not specified in scenario
        """
        self._adapter = adapter
        self._trace_output_dir = Path(trace_output_dir) if trace_output_dir else None
        self._default_max_turns = default_max_turns

    async def run(
        self,
        scenario: Scenario,
        config: Optional[dict[str, Any]] = None,
    ) -> SimulationResult:
        """Run a complete simulation.

        Args:
            scenario: Scenario definition (scripted or generative)
            config: Additional configuration for adapter/simulator

        Returns:
            SimulationResult with conversation history and metrics
        """
        simulation_id = str(uuid.uuid4())

        # Create user simulator based on scenario type
        simulator = self._create_simulator(scenario)

        # Initialize state
        state = SimulationState(
            simulation_id=simulation_id,
            scenario_id=scenario.scenario_id,
            persona_id=scenario.persona.persona_id,
            max_turns=scenario.max_turns,
        )

        # Initialize adapter and simulator
        await self._adapter.initialize(config)
        if hasattr(simulator, "initialize"):
            await simulator.initialize()

        try:
            # Run conversation loop
            await self._run_conversation_loop(state, simulator, scenario)

            # Mark success
            state.status = "completed"
            state.ended_at = datetime.now()

            # Calculate metrics
            metrics = self._calculate_metrics(state)

            # Save trace if configured
            trace_path = None
            if self._trace_output_dir:
                trace_path = await self._save_trace(state)

            return SimulationResult(
                simulation_id=simulation_id,
                state=state,
                trace_path=str(trace_path) if trace_path else None,
                metrics=metrics,
                success=True,
            )

        except Exception as e:
            state.status = "failed"
            state.ended_at = datetime.now()
            state.termination_reason = str(e)

            return SimulationResult(
                simulation_id=simulation_id,
                state=state,
                success=False,
                error=str(e),
            )

        finally:
            await self._adapter.cleanup()
            if hasattr(simulator, "cleanup"):
                await simulator.cleanup()

    async def _run_conversation_loop(
        self,
        state: SimulationState,
        simulator: UserSimulator,
        scenario: Scenario,
    ) -> None:
        """Execute the main conversation loop."""
        # Get initial message
        initial_message_text = scenario.get_initial_message()
        initial_message = HumanMessage(content=initial_message_text)

        # Add initial user turn
        state.turns.append(SimulationTurn(
            turn_number=0,
            role=ConversationRole.USER,
            message=initial_message,
        ))

        # Invoke agent with initial message
        agent_response = await self._adapter.invoke(initial_message, state)

        state.turns.append(SimulationTurn(
            turn_number=0,
            role=ConversationRole.AGENT,
            message=agent_response,
        ))

        state.current_turn = 1

        # Main loop
        while state.current_turn < state.max_turns:
            # Check termination
            should_stop, reason = await simulator.should_terminate(state)
            if should_stop:
                state.termination_reason = reason
                break

            # Generate user response
            try:
                user_message = await simulator.generate_response(agent_response, state)
            except StopIteration as e:
                state.termination_reason = str(e)
                break

            state.turns.append(SimulationTurn(
                turn_number=state.current_turn,
                role=ConversationRole.USER,
                message=user_message,
            ))

            # Invoke agent
            agent_response = await self._adapter.invoke(user_message, state)

            state.turns.append(SimulationTurn(
                turn_number=state.current_turn,
                role=ConversationRole.AGENT,
                message=agent_response,
            ))

            # Update agent state snapshot
            state.agent_state = self._adapter.get_state()

            state.current_turn += 1

    def _create_simulator(self, scenario: Scenario) -> UserSimulator:
        """Create appropriate simulator for scenario type."""
        if isinstance(scenario, ScriptedScenario):
            llm_fallback = None
            if scenario.fallback == "generative":
                llm_fallback = LLMUserSimulator(scenario.persona)
            return ScriptedUserSimulator(scenario, llm_fallback)
        else:
            return LLMUserSimulator(scenario.persona)

    def _calculate_metrics(self, state: SimulationState) -> dict[str, Any]:
        """Calculate simulation metrics."""
        user_turns = [t for t in state.turns if t.role == ConversationRole.USER]
        agent_turns = [t for t in state.turns if t.role == ConversationRole.AGENT]

        duration = 0.0
        if state.ended_at and state.started_at:
            duration = (state.ended_at - state.started_at).total_seconds()

        return {
            "total_turns": len(state.turns),
            "user_turns": len(user_turns),
            "agent_turns": len(agent_turns),
            "avg_user_message_length": (
                sum(len(t.message.content) for t in user_turns) / max(len(user_turns), 1)
            ),
            "avg_agent_message_length": (
                sum(len(t.message.content) for t in agent_turns) / max(len(agent_turns), 1)
            ),
            "duration_seconds": duration,
            "termination_reason": state.termination_reason,
        }

    async def _save_trace(self, state: SimulationState) -> Path:
        """Save simulation state as a trace file."""
        if not self._trace_output_dir:
            raise ValueError("No trace output directory configured")

        self._trace_output_dir.mkdir(parents=True, exist_ok=True)

        trace_file = self._trace_output_dir / f"simulation_{state.simulation_id}.json"

        # Convert to JSON-serializable format
        result = SimulationResult(
            simulation_id=state.simulation_id,
            state=state,
            success=True,
        )
        trace_data = result.to_dict()

        with open(trace_file, "w") as f:
            json.dump(trace_data, f, indent=2, default=str)

        return trace_file


class BatchSimulationRunner:
    """Run multiple simulations with different scenarios/configurations.

    Useful for evaluation runs across multiple test cases.

    Example usage:
        def adapter_factory():
            return LangGraphAdapter(graph=build_graph(), ...)

        runner = BatchSimulationRunner(
            adapter_factory=adapter_factory,
            trace_output_dir="./traces",
            parallel=True,
        )

        results = await runner.run_all(scenarios)
    """

    def __init__(
        self,
        adapter_factory: Callable[[], AgentAdapter],
        trace_output_dir: Optional[Union[str, Path]] = None,
        parallel: bool = False,
        max_parallel: int = 4,
    ):
        """Initialize batch simulation runner.

        Args:
            adapter_factory: Factory function to create adapters
            trace_output_dir: Directory for trace files
            parallel: Whether to run simulations in parallel
            max_parallel: Maximum concurrent simulations
        """
        self._adapter_factory = adapter_factory
        self._trace_output_dir = Path(trace_output_dir) if trace_output_dir else None
        self._parallel = parallel
        self._max_parallel = max_parallel

    async def run_all(
        self,
        scenarios: list[Scenario],
    ) -> list[SimulationResult]:
        """Run all scenarios and collect results.

        Args:
            scenarios: List of scenarios to run

        Returns:
            List of simulation results
        """
        if self._parallel:
            return await self._run_parallel(scenarios)
        else:
            return await self._run_sequential(scenarios)

    async def _run_sequential(
        self,
        scenarios: list[Scenario],
    ) -> list[SimulationResult]:
        """Run scenarios one at a time."""
        results = []
        for scenario in scenarios:
            adapter = self._adapter_factory()
            runner = SimulationRunner(
                adapter=adapter,
                trace_output_dir=self._trace_output_dir,
            )
            result = await runner.run(scenario)
            results.append(result)
        return results

    async def _run_parallel(
        self,
        scenarios: list[Scenario],
    ) -> list[SimulationResult]:
        """Run scenarios in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(self._max_parallel)

        async def run_with_semaphore(scenario: Scenario) -> SimulationResult:
            async with semaphore:
                adapter = self._adapter_factory()
                runner = SimulationRunner(
                    adapter=adapter,
                    trace_output_dir=self._trace_output_dir,
                )
                return await runner.run(scenario)

        tasks = [run_with_semaphore(s) for s in scenarios]
        return await asyncio.gather(*tasks)
