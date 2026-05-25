"""Candidate model representing a physician in the talent pool."""

from pydantic import BaseModel, Field


class Candidate(BaseModel):
    """A physician candidate stored in the database.

    PII note: name is stored for display but MUST be excluded from
    any data sent to the LLM for scoring to prevent bias.
    """

    id: str = Field(..., description="Unique candidate identifier")
    name: str = Field(..., description="Full name (excluded from scoring payload)")
    specialty: str = Field(..., description="Primary medical specialty")
    years_experience: int = Field(..., ge=0, description="Years of post-residency experience")
    location: str = Field(..., description="Current city and state")
    board_certified: bool = Field(..., description="Whether the candidate holds board certification")
    licenses: list[str] = Field(
        default_factory=list,
        description="List of active state medical licenses",
    )
    education: str | None = Field(default=None, description="Medical school and residency")
    skills: list[str] = Field(
        default_factory=list,
        description="Clinical skills and procedure proficiencies",
    )
    availability: str | None = Field(
        default=None,
        description="When the candidate can start, e.g. 'Immediately', '30 days'",
    )
    preferred_employment: list[str] = Field(
        default_factory=list,
        description="Preferred employment types: full-time, part-time, locum tenens",
    )
