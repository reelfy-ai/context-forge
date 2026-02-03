"""Stale memory scenarios for testing memory hygiene.

These scenarios test whether the agent correctly updates outdated
profile information when users mention changes.
"""

from context_forge.harness.user_simulator import (
    Behavior,
    CommunicationStyle,
    GenerativeScenario,
    Goal,
    Persona,
    ScriptedScenario,
    ScriptedTurn,
    TechnicalLevel,
)


def stale_work_schedule_persona() -> Persona:
    """Create persona for stale work schedule scenario.

    This user's stored profile has work_schedule="Office 9-5" but they
    now work from home and will mention this in the conversation.
    """
    return Persona(
        persona_id="remote_worker",
        name="Alex",
        description="A recent remote worker interested in optimizing home energy use",
        background="Used to commute to office, now works from home full-time",
        situation="Switched to remote work 2 months ago, wants to optimize EV charging for new schedule",
        behavior=Behavior(
            communication_style=CommunicationStyle.CASUAL,
            technical_level=TechnicalLevel.INTERMEDIATE,
            patience_level=7,
            asks_followup_questions=True,
        ),
        goals=[
            Goal(
                description="Get EV charging advice for work-from-home schedule",
                success_criteria="Agent acknowledges WFH and gives relevant advice",
                priority=1,
            ),
            Goal(
                description="Have profile updated with new work schedule",
                success_criteria="Agent saves 'work_from_home' to profile",
                priority=2,
            ),
        ],
    )


def stale_work_schedule_scenario(max_turns: int = 3) -> ScriptedScenario:
    """Scenario where user mentions they now work from home.

    The user's stored profile has stale work_schedule="Office 9-5".
    The agent should detect this new information and update memory.

    Uses ScriptedScenario for deterministic testing.
    """
    return ScriptedScenario(
        scenario_id="stale_work_schedule",
        name="Stale Work Schedule Update",
        description="User mentions working from home, agent should update stale schedule",
        persona=stale_work_schedule_persona(),
        turns=[
            ScriptedTurn(
                turn_number=1,
                user_message="I work from home now, switched jobs 2 months ago. When should I run my dishwasher to save money?",
            ),
        ],
        max_turns=max_turns,
    )


def stale_solar_persona() -> Persona:
    """Create persona for stale solar capacity scenario.

    This user's stored profile has solar_capacity_kw=7.5 but they
    upgraded to 12kW and will mention this.
    """
    return Persona(
        persona_id="solar_upgrader",
        name="Jordan",
        description="A solar enthusiast who recently upgraded their system",
        background="Had 7.5kW solar for 3 years, just upgraded to 12kW",
        situation="Excited about new solar capacity, wants to maximize self-consumption",
        behavior=Behavior(
            communication_style=CommunicationStyle.CASUAL,
            technical_level=TechnicalLevel.EXPERT,
            patience_level=8,
            asks_followup_questions=True,
        ),
        goals=[
            Goal(
                description="Understand new solar production potential",
                success_criteria="Agent uses 12kW capacity in calculations",
                priority=1,
            ),
            Goal(
                description="Have profile updated with new solar capacity",
                success_criteria="Agent saves solar_capacity_kw=12.0 to profile",
                priority=2,
            ),
        ],
    )


def stale_solar_scenario(max_turns: int = 3) -> ScriptedScenario:
    """Scenario where user mentions they upgraded solar panels.

    The user's stored profile has stale solar_capacity_kw=7.5.
    The agent should detect this and update to 12kW.
    """
    return ScriptedScenario(
        scenario_id="stale_solar",
        name="Stale Solar Capacity Update",
        description="User mentions solar upgrade, agent should update stale capacity",
        persona=stale_solar_persona(),
        turns=[
            ScriptedTurn(
                turn_number=1,
                user_message="I upgraded my solar panels to 12kW last month! How much more can I generate now compared to before?",
            ),
        ],
        max_turns=max_turns,
    )


def multi_update_persona() -> Persona:
    """Create persona for multiple stale fields scenario.

    This user has multiple outdated fields and will mention all changes.
    """
    return Persona(
        persona_id="growing_family",
        name="Morgan",
        description="A growing family with lots of recent changes",
        background="Recently had a baby, upgraded solar, got new EV",
        situation="Life has changed a lot - new baby, new EV, upgraded solar system",
        behavior=Behavior(
            communication_style=CommunicationStyle.CASUAL,
            technical_level=TechnicalLevel.NOVICE,
            patience_level=5,
            asks_followup_questions=False,
        ),
        goals=[
            Goal(
                description="Get EV charging advice accounting for all changes",
                success_criteria="Agent considers all the new information",
                priority=1,
            ),
            Goal(
                description="Have all profile changes saved",
                success_criteria="Agent saves solar, EV, and occupants updates",
                priority=2,
            ),
        ],
    )


def multi_update_scenario(max_turns: int = 3) -> ScriptedScenario:
    """Scenario where user mentions multiple changes at once.

    The user's profile has stale:
    - solar_capacity_kw: 7.5 (now 15kW)
    - ev_model: "Tesla Model 3" (now "Rivian R1T")
    - occupants: 2 (now 3)

    Tests that agent captures ALL facts, not just some.
    """
    return ScriptedScenario(
        scenario_id="multi_update",
        name="Multiple Profile Updates",
        description="User mentions multiple life changes, agent should update all",
        persona=multi_update_persona(),
        turns=[
            ScriptedTurn(
                turn_number=1,
                user_message="A lot has changed! We got a Rivian R1T, upgraded to 15kW solar, and just had a baby so we're 3 people now. What's my best EV charging time?",
            ),
        ],
        max_turns=max_turns,
    )


# Generative versions for more exploratory testing

def stale_work_schedule_generative_scenario(max_turns: int = 5) -> GenerativeScenario:
    """Generative version of stale work schedule scenario.

    Allows for multi-turn conversation where user might reveal
    additional details about their new schedule.
    """
    return GenerativeScenario(
        scenario_id="stale_work_schedule_generative",
        name="Stale Work Schedule (Generative)",
        description="User mentions WFH in a natural multi-turn conversation",
        persona=stale_work_schedule_persona(),
        initial_message="I work from home now. When should I charge my EV?",
        max_turns=max_turns,
        allowed_topics=["energy", "solar", "EV", "electricity", "charging", "rates", "work", "schedule"],
        forbidden_topics=["politics", "religion"],
        temperature=0.7,
        max_response_tokens=500,
    )
