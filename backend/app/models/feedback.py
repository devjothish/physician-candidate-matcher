"""Recruiter feedback model for match quality tracking."""

from typing import Literal

from pydantic import BaseModel, Field


class RecruiterFeedback(BaseModel):
    """Feedback from a recruiter on a candidate match.

    Used to track match quality over time and identify systematic
    scoring issues for continuous improvement.
    """

    match_id: str = Field(..., description="ID of the match being reviewed")
    candidate_id: str = Field(..., description="ID of the candidate")
    feedback_type: Literal["good_match", "bad_match", "hired", "interviewed"] = Field(
        ..., description="Type of feedback"
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional recruiter notes",
    )
