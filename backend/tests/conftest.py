"""Shared pytest fixtures for the physician candidate matcher test suite."""

import pytest

from app.models.candidate import Candidate
from app.models.job import JobDescription


@pytest.fixture
def sample_job() -> JobDescription:
    """A realistic interventional cardiology job posting."""
    return JobDescription(
        title="Interventional Cardiologist",
        specialty="Cardiology",
        location="Boston, MA",
        requirements=(
            "Seeking a board-certified interventional cardiologist to join "
            "a growing academic cardiology practice at a major teaching hospital. "
            "Must have completed an ACGME-accredited fellowship in interventional "
            "cardiology. Experience with structural heart procedures and TAVR "
            "preferred. Active Massachusetts medical license required. Minimum "
            "3 years post-fellowship clinical experience. Must be comfortable "
            "with complex PCI, chronic total occlusions, and mechanical "
            "circulatory support devices. Teaching responsibilities include "
            "supervision of fellows and residents."
        ),
        preferred_experience_years=5,
        employment_type="full-time",
    )


@pytest.fixture
def sample_job_psychiatry() -> JobDescription:
    """A telepsychiatry job posting."""
    return JobDescription(
        title="Telepsychiatrist",
        specialty="Psychiatry",
        location="Remote - Pacific Northwest",
        requirements=(
            "Remote telepsychiatry position serving patients in WA and OR. "
            "Must hold active medical licenses in Washington and Oregon. "
            "Board certification in psychiatry required. Experience with "
            "telemedicine platforms and electronic health records. Expertise "
            "in psychopharmacology and cognitive behavioral therapy. Interest "
            "in addiction psychiatry a plus. Minimum 3 years post-residency "
            "experience preferred."
        ),
        preferred_experience_years=3,
        employment_type="full-time",
    )


@pytest.fixture
def matching_candidate() -> Candidate:
    """A cardiologist candidate that should score well against sample_job."""
    return Candidate(
        id="test-001",
        name="Dr. Test Cardiologist",
        specialty="Cardiology",
        years_experience=8,
        location="Boston, MA",
        board_certified=True,
        licenses=["MA", "NY", "CT"],
        education="Harvard Medical School; Fellowship at Brigham and Women's Hospital",
        skills=[
            "Interventional Cardiology",
            "Cardiac Catheterization",
            "Structural Heart",
            "TAVR",
            "Complex PCI",
            "Echocardiography",
        ],
        availability="30 days",
        preferred_employment=["full-time"],
    )


@pytest.fixture
def weak_candidate() -> Candidate:
    """A dermatologist candidate that should score poorly against a cardiology job."""
    return Candidate(
        id="test-002",
        name="Dr. Test Dermatologist",
        specialty="Dermatology",
        years_experience=3,
        location="Los Angeles, CA",
        board_certified=True,
        licenses=["CA"],
        education="UCLA; Residency at UCLA Medical Center",
        skills=[
            "Cosmetic Dermatology",
            "Mohs Surgery",
            "Acne Management",
        ],
        availability="90 days",
        preferred_employment=["part-time"],
    )


@pytest.fixture
def candidate_list(matching_candidate: Candidate, weak_candidate: Candidate) -> list[Candidate]:
    """A small list of candidates for batch testing."""
    partial_match = Candidate(
        id="test-003",
        name="Dr. Test Internal Medicine",
        specialty="Internal Medicine",
        years_experience=12,
        location="New York, NY",
        board_certified=True,
        licenses=["NY", "CT", "MA"],
        education="Columbia University; Residency at NYP",
        skills=[
            "Hospital Medicine",
            "Echocardiography",
            "Critical Care",
        ],
        availability="Immediately",
        preferred_employment=["full-time"],
    )
    return [matching_candidate, partial_match, weak_candidate]
