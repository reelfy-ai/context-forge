"""Solar production advice scenario."""

from context_forge.harness.user_simulator import (
    Behavior,
    CommunicationStyle,
    GenerativeScenario,
    Goal,
    Persona,
    TechnicalLevel,
)


def solar_advice_persona() -> Persona:
    """Create persona for solar advice scenario."""
    return Persona(
        persona_id="curious_homeowner",
        name="Mike",
        description="A homeowner curious about their solar panel performance",
        background="Recently installed 7.5kW solar system, wants to understand production patterns",
        situation="Checking if solar panels are performing as expected",
        behavior=Behavior(
            communication_style=CommunicationStyle.CASUAL,
            technical_level=TechnicalLevel.BEGINNER,
            patience_level=7,
            asks_followup_questions=True,
        ),
        goals=[
            Goal(
                description="Get solar production estimate for today",
                success_criteria="Agent provides kWh estimate",
                priority=1,
            ),
            Goal(
                description="Understand factors affecting production",
                success_criteria="Agent explains weather/season impact",
                priority=2,
            ),
        ],
    )


def solar_advice_scenario(max_turns: int = 5) -> GenerativeScenario:
    """Create solar production advice scenario.

    This scenario tests:
    - Tool calls: weather API, solar estimation
    - Memory: user's solar system specs
    - Explanation quality: making technical info accessible
    """
    return GenerativeScenario(
        scenario_id="solar_advice",
        name="Solar Production Query",
        description="User asks about solar panel production for the day",
        persona=solar_advice_persona(),
        initial_message="How much solar will my panels produce today?",
        max_turns=max_turns,
        allowed_topics=["energy", "solar", "weather", "electricity", "production"],
        forbidden_topics=["politics", "religion"],
        temperature=0.7,
        max_response_tokens=500,
    )
