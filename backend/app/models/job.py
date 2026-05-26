"""Job description model for matching requests."""

from pydantic import BaseModel, Field


class JobDescription(BaseModel):
    """A physician job posting that candidates will be matched against.

    All text fields are validated for reasonable length to prevent
    prompt injection via absurdly long inputs and to catch empty submissions.
    """

    title: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Job title, e.g. 'Cardiologist - Heart Failure Specialist'",
    )
    specialty: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Medical specialty, e.g. 'Cardiology'",
    )
    location: str = Field(
        default="",
        max_length=200,
        description="Job location, e.g. 'Boston, MA'. Leave empty for remote/any location.",
    )
    requirements: str = Field(
        ...,
        min_length=50,
        max_length=5000,
        description="Full job requirements and responsibilities text",
    )
    preferred_experience_years: int | None = Field(
        default=None,
        ge=0,
        le=50,
        description="Preferred years of experience",
    )
    employment_type: str | None = Field(
        default=None,
        description="Employment type: full-time, part-time, locum tenens, etc.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Interventional Cardiologist",
                    "specialty": "Cardiology",
                    "location": "Boston, MA",
                    "requirements": (
                        "Seeking a board-certified interventional cardiologist "
                        "to join a growing cardiology practice. Must have completed "
                        "an ACGME-accredited fellowship in interventional cardiology. "
                        "Experience with structural heart procedures preferred. "
                        "Active Massachusetts medical license required. "
                        "Minimum 3 years post-fellowship experience."
                    ),
                    "preferred_experience_years": 3,
                    "employment_type": "full-time",
                }
            ]
        }
    }
