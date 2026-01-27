"""General energy saving advice scenario."""

from context_forge.harness.user_simulator import (
    Behavior,
    CommunicationStyle,
    GenerativeScenario,
    Goal,
    Persona,
    TechnicalLevel,
)


def general_advice_persona() -> Persona:
    """Create persona for general advice scenario."""
    return Persona(
        persona_id="cost_conscious_family",
        name="Jennifer",
        description="A cost-conscious parent looking to reduce household energy bills",
        background="Family of 4, work from home, concerned about rising electricity costs",
        situation="Looking for practical ways to reduce monthly electricity bill",
        behavior=Behavior(
            communication_style=CommunicationStyle.CASUAL,
            technical_level=TechnicalLevel.BEGINNER,
            patience_level=5,
            asks_followup_questions=True,
        ),
        goals=[
            Goal(
                description="Get actionable energy saving tips",
                success_criteria="Agent provides specific, practical recommendations",
                priority=1,
            ),
            Goal(
                description="Understand biggest energy consumers",
                success_criteria="Agent identifies main energy usage areas",
                priority=2,
            ),
            Goal(
                description="Learn about time-of-use optimization",
                success_criteria="Agent explains peak/off-peak strategies",
                priority=3,
            ),
        ],
    )


def general_advice_scenario(max_turns: int = 5) -> GenerativeScenario:
    """Create general energy advice scenario.

    This scenario tests:
    - Knowledge retrieval: energy saving best practices
    - Memory: household profile and preferences
    - Personalization: tailored advice based on user situation
    """
    return GenerativeScenario(
        scenario_id="general_advice",
        name="General Energy Advice",
        description="User asks for general energy saving tips",
        persona=general_advice_persona(),
        initial_message="What are some ways I can reduce my electricity bill?",
        max_turns=max_turns,
        allowed_topics=["energy", "electricity", "savings", "tips", "appliances", "solar", "EV"],
        forbidden_topics=["politics", "religion", "specific financial advice"],
        temperature=0.7,
        max_response_tokens=500,
    )
