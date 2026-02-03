"""Pydantic models for LLM judge responses.

Using Pydantic models for LLM output provides:
- Structured validation of responses
- Clear schema documentation
- Better error messages when parsing fails
- Type safety throughout the codebase
"""

from typing import Optional

from pydantic import BaseModel, Field


class UserFact(BaseModel):
    """A fact the user stated about themselves."""

    fact: str = Field(description="Description of what the user stated")
    topic: str = Field(description="Category: equipment, schedule, preference, household, location")


class CorrectSave(BaseModel):
    """A fact that was correctly saved to memory."""

    fact: str = Field(description="What the user stated")
    saved_as: str = Field(description="How it was saved to memory")


class MissedFact(BaseModel):
    """A fact the user stated but was not saved."""

    fact: str = Field(description="What the user stated")
    should_have_updated: str = Field(description="Which memory field should have been updated")


class Hallucination(BaseModel):
    """Something saved to memory that the user did not state."""

    saved: str = Field(description="What was incorrectly saved")
    reason: str = Field(description="Why this is considered a hallucination")


class DataLoss(BaseModel):
    """Correct data that was incorrectly lost or overwritten."""

    field: str = Field(description="Which field was affected")
    old_value: str = Field(description="The value that was lost")
    reason: str = Field(description="Why this loss was incorrect")


class MemoryHygieneEvaluation(BaseModel):
    """Complete evaluation result from the Memory Hygiene Judge.

    This model defines the expected structure of the LLM's response.
    The LLM is prompted to return JSON matching this schema.
    """

    user_facts_stated: list[UserFact] = Field(
        default_factory=list,
        description="Facts the user stated about themselves during the session",
    )
    facts_correctly_saved: list[CorrectSave] = Field(
        default_factory=list,
        description="Facts that were correctly identified and saved",
    )
    facts_missed: list[MissedFact] = Field(
        default_factory=list,
        description="Facts the user stated but were not saved to memory",
    )
    hallucinations: list[Hallucination] = Field(
        default_factory=list,
        description="Things saved to memory that the user did not actually state",
    )
    data_incorrectly_lost: list[DataLoss] = Field(
        default_factory=list,
        description="Correct data that was incorrectly overwritten or deleted",
    )
    summary: str = Field(
        description="One sentence summary of memory management quality"
    )
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality score from 0.0 (worst) to 1.0 (best)",
    )
    passed: bool = Field(
        description="Whether the memory management passed evaluation",
    )

    @classmethod
    def get_json_schema_prompt(cls) -> str:
        """Get a prompt-friendly description of the expected JSON schema."""
        # Note: Using single braces - this string is NOT passed through .format()
        return """{
  "user_facts_stated": [
    {"fact": "description of fact", "topic": "equipment|schedule|preference|household|location"}
  ],
  "facts_correctly_saved": [
    {"fact": "what user stated", "saved_as": "how it was saved"}
  ],
  "facts_missed": [
    {"fact": "what user stated", "should_have_updated": "which memory field"}
  ],
  "hallucinations": [
    {"saved": "what was incorrectly saved", "reason": "why this is wrong"}
  ],
  "data_incorrectly_lost": [
    {"field": "which field", "old_value": "what was lost", "reason": "why this was wrong"}
  ],
  "summary": "One sentence summary",
  "score": 0.0 to 1.0,
  "passed": true or false
}"""
