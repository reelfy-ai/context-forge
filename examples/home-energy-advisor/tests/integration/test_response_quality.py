"""Integration tests for response quality using DeepEval.

Uses DeepEval's GEval metric with Ollama as the LLM judge to evaluate
whether the advisor's responses adequately address energy questions.

Requires: Ollama running at localhost:11434 with llama3.2 pulled.
"""

import pytest

from deepeval.metrics import GEval
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from .conftest import model_required, ollama_required

pytestmark = [ollama_required, model_required]

# Initialize the judge model (same Ollama instance)
judge_model = OllamaModel(model="llama3.2", base_url="http://localhost:11434")

# Define the relevance metric
relevance_metric = GEval(
    name="Response Relevance",
    model=judge_model,
    criteria="The response directly answers the user's question. For definitional questions it provides a clear explanation. For advice questions it provides recommendations.",
    evaluation_steps=[
        "Check if the response is about the same topic as the question",
        "Check if the response provides useful information related to the question",
        "A response that answers the question at all should score at least 0.5",
    ],
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.3,
)

# Define the correctness metric (when expected output is provided)
correctness_metric = GEval(
    name="Response Correctness",
    model=judge_model,
    criteria="The response covers the same topic as the expected output and does not contradict it.",
    evaluation_steps=[
        "Check if the actual output addresses the same topic as the expected output",
        "A response about the right topic should score at least 0.5 even if wording differs",
        "Only penalize if the response is completely off-topic or factually wrong",
    ],
    evaluation_params=[
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
    ],
    threshold=0.3,
)


def _invoke_advisor(integration_config, demo_profile, message: str) -> str:
    """Helper to invoke the advisor and return the response text."""
    from langgraph.store.memory import InMemoryStore

    from src.agents.advisor import build_advisor_graph

    store = InMemoryStore()
    graph = build_advisor_graph(store=store)
    result = graph.invoke({
        "user_id": "quality_test_user",
        "session_id": "quality_session",
        "message": message,
        "messages": [],
        "turn_count": 0,
        "user_profile": demo_profile,
        "weather_data": None,
        "rate_data": None,
        "solar_estimate": None,
        "retrieved_docs": [],
        "tool_observations": [],
        "response": None,
        "extracted_facts": [],
        "should_memorize": False,
    })
    return result["response"]


class TestResponseRelevance:
    """Tests that responses are relevant to the user's question."""

    def test_ev_charging_relevance(self, integration_config, demo_profile):
        """EV charging response should address timing and cost."""
        response = _invoke_advisor(
            integration_config, demo_profile,
            "When should I charge my EV tonight to minimize cost?",
        )

        test_case = LLMTestCase(
            input="When should I charge my EV tonight to minimize cost?",
            actual_output=response,
        )
        relevance_metric.measure(test_case)
        assert relevance_metric.score >= 0.3, (
            f"Relevance score {relevance_metric.score}: {relevance_metric.reason}"
        )

    def test_solar_production_relevance(self, integration_config, demo_profile):
        """Solar production response should reference system and conditions."""
        response = _invoke_advisor(
            integration_config, demo_profile,
            "How much solar will my panels produce today?",
        )

        test_case = LLMTestCase(
            input="How much solar will my panels produce today?",
            actual_output=response,
        )
        relevance_metric.measure(test_case)
        assert relevance_metric.score >= 0.3, (
            f"Relevance score {relevance_metric.score}: {relevance_metric.reason}"
        )

    def test_faq_relevance(self, integration_config, demo_profile):
        """FAQ response should define the concept clearly."""
        response = _invoke_advisor(
            integration_config, demo_profile,
            "What is a kilowatt hour?",
        )

        test_case = LLMTestCase(
            input="What is a kilowatt hour?",
            actual_output=response,
        )
        relevance_metric.measure(test_case)
        assert relevance_metric.score >= 0.3, (
            f"Relevance score {relevance_metric.score}: {relevance_metric.reason}"
        )


class TestResponseCorrectness:
    """Tests that responses contain expected key points."""

    def test_ev_charging_mentions_off_peak(self, integration_config, demo_profile):
        """EV charging response should mention off-peak timing."""
        response = _invoke_advisor(
            integration_config, demo_profile,
            "When should I charge my EV tonight to minimize cost?",
        )

        test_case = LLMTestCase(
            input="When should I charge my EV tonight to minimize cost?",
            actual_output=response,
            expected_output="Charge your EV during off-peak hours (typically after 9 PM or late night) when TOU electricity rates are lowest to minimize cost.",
        )
        correctness_metric.measure(test_case)
        assert correctness_metric.score >= 0.3, (
            f"Correctness score {correctness_metric.score}: {correctness_metric.reason}"
        )

    def test_kwh_definition_accurate(self, integration_config, demo_profile):
        """kWh definition should be factually correct."""
        response = _invoke_advisor(
            integration_config, demo_profile,
            "What is a kilowatt hour?",
        )

        test_case = LLMTestCase(
            input="What is a kilowatt hour?",
            actual_output=response,
            expected_output="A kilowatt hour (kWh) is a unit of energy equal to one kilowatt of power used for one hour. It is the standard unit for measuring electricity consumption on utility bills.",
        )
        correctness_metric.measure(test_case)
        assert correctness_metric.score >= 0.3, (
            f"Correctness score {correctness_metric.score}: {correctness_metric.reason}"
        )

    def test_solar_mentions_system_size(self, integration_config, demo_profile):
        """Solar response should reference the user's system capacity."""
        response = _invoke_advisor(
            integration_config, demo_profile,
            "How much solar will my panels produce today?",
        )

        test_case = LLMTestCase(
            input="How much solar will my panels produce today?",
            actual_output=response,
            expected_output="Your 7.5 kW solar system production depends on weather conditions (cloud cover, temperature) and daylight hours. On a clear day you can expect peak production during midday hours.",
        )
        correctness_metric.measure(test_case)
        assert correctness_metric.score >= 0.3, (
            f"Correctness score {correctness_metric.score}: {correctness_metric.reason}"
        )
