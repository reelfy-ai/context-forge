"""EV charging optimization scenario."""

from context_forge.harness.user_simulator import (
    Behavior,
    CommunicationStyle,
    GenerativeScenario,
    Goal,
    Persona,
    TechnicalLevel,
)


def ev_charging_persona() -> Persona:
    """Create persona for EV charging scenario."""
    return Persona(
        persona_id="busy_homeowner",
        name="Sarah",
        description="A busy homeowner interested in reducing energy costs",
        background="Homeowner with 7.5kW solar system and Tesla Model 3",
        situation="Wants to optimize EV charging to minimize electricity bills",
        behavior=Behavior(
            communication_style=CommunicationStyle.CASUAL,
            technical_level=TechnicalLevel.INTERMEDIATE,
            patience_level=6,
            asks_followup_questions=True,
        ),
        goals=[
            Goal(
                description="Get specific EV charging time recommendation",
                success_criteria="Agent provides a specific time window for charging",
                priority=1,
            ),
            Goal(
                description="Understand how solar affects charging strategy",
                success_criteria="Agent explains solar/charging relationship",
                priority=2,
            ),
            Goal(
                description="Learn about off-peak rate benefits",
                success_criteria="Agent mentions utility rate schedules",
                priority=3,
            ),
        ],
    )


def ev_charging_scenario(max_turns: int = 5) -> GenerativeScenario:
    """Create EV charging optimization scenario.

    This scenario tests:
    - Tool calls: weather API, utility rates, solar estimation
    - Memory: user's equipment and preferences
    - Reasoning: combining multiple data sources for recommendation
    """
    return GenerativeScenario(
        scenario_id="ev_charging",
        name="EV Charging Optimization",
        description="User asks about optimal EV charging times to minimize cost",
        persona=ev_charging_persona(),
        initial_message="When should I charge my EV tonight to minimize cost?",
        max_turns=max_turns,
        allowed_topics=["energy", "solar", "EV", "electricity", "charging", "rates", "weather"],
        forbidden_topics=["politics", "religion", "personal finance advice"],
        temperature=0.7,
        max_response_tokens=500,
    )
