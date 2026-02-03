"""Trajectory evaluation tests for the Home Energy Advisor.

Two Test Levels
===============

Level 2: Simple (tests/trajectories/simple/)
    Single-turn evaluation with minimal setup.
    Use evaluate_agent() for quick testing.

    Example:
        from context_forge.evaluation import evaluate_agent

        result = evaluate_agent(
            graph=my_graph,
            message="I work from home now",
            store=my_store,
        )
        result.print_report()

Level 3: Simulation (tests/trajectories/simulation/)
    Multi-turn conversations with personas and scenarios.
    Use SimulationRunner for systematic testing.

    Example:
        from context_forge import SimulationRunner, LangGraphAdapter
        from context_forge.harness.user_simulator import GenerativeScenario, Persona

        persona = Persona(name="Sarah", background="Homeowner with solar")
        scenario = GenerativeScenario(persona=persona, max_turns=5)
        runner = SimulationRunner(adapter=adapter)
        result = await runner.run(scenario)

Which to Use?
=============
- Start with Level 2 (simple/) for quick evaluation
- Use Level 3 (simulation/) for comprehensive multi-turn testing
"""
