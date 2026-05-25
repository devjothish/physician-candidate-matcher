"""Unit tests for Pydantic models and validation logic."""

import pytest
from pydantic import ValidationError

from app.models.candidate import Candidate
from app.models.feedback import RecruiterFeedback
from app.models.job import JobDescription
from app.models.match import CandidateMatch, MatchScore


class TestJobDescriptionModel:
    """Tests for JobDescription validation."""

    def test_valid_job(self, sample_job: JobDescription) -> None:
        """Valid job description should parse without errors."""
        assert sample_job.title == "Interventional Cardiologist"
        assert sample_job.specialty == "Cardiology"
        assert sample_job.preferred_experience_years == 5

    def test_title_too_short(self) -> None:
        """Title under 2 characters should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            JobDescription(
                title="X",
                specialty="Cardiology",
                location="Boston, MA",
                requirements="x" * 50,
            )
        assert "title" in str(exc_info.value)

    def test_requirements_too_short(self) -> None:
        """Requirements under 50 characters should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            JobDescription(
                title="Cardiologist",
                specialty="Cardiology",
                location="Boston, MA",
                requirements="Too short",
            )
        assert "requirements" in str(exc_info.value)

    def test_experience_years_negative(self) -> None:
        """Negative experience years should fail validation."""
        with pytest.raises(ValidationError):
            JobDescription(
                title="Cardiologist",
                specialty="Cardiology",
                location="Boston, MA",
                requirements="x" * 50,
                preferred_experience_years=-1,
            )

    def test_experience_years_too_high(self) -> None:
        """Experience years over 50 should fail validation."""
        with pytest.raises(ValidationError):
            JobDescription(
                title="Cardiologist",
                specialty="Cardiology",
                location="Boston, MA",
                requirements="x" * 50,
                preferred_experience_years=51,
            )

    def test_optional_fields_default_none(self) -> None:
        """Optional fields should default to None."""
        job = JobDescription(
            title="Cardiologist",
            specialty="Cardiology",
            location="Boston, MA",
            requirements="x" * 50,
        )
        assert job.preferred_experience_years is None
        assert job.employment_type is None

    def test_json_serialization(self, sample_job: JobDescription) -> None:
        """Job should serialize to and from JSON cleanly."""
        json_str = sample_job.model_dump_json()
        restored = JobDescription.model_validate_json(json_str)
        assert restored.title == sample_job.title
        assert restored.specialty == sample_job.specialty


class TestCandidateModel:
    """Tests for Candidate model validation."""

    def test_valid_candidate(self, matching_candidate: Candidate) -> None:
        """Valid candidate should parse without errors."""
        assert matching_candidate.id == "test-001"
        assert matching_candidate.board_certified is True
        assert len(matching_candidate.licenses) == 3

    def test_empty_lists_default(self) -> None:
        """List fields should default to empty lists."""
        candidate = Candidate(
            id="test-empty",
            name="Dr. Minimal",
            specialty="Internal Medicine",
            years_experience=1,
            location="Boston, MA",
            board_certified=False,
        )
        assert candidate.licenses == []
        assert candidate.skills == []
        assert candidate.preferred_employment == []

    def test_candidate_json_round_trip(self, matching_candidate: Candidate) -> None:
        """Candidate should survive JSON serialization."""
        json_str = matching_candidate.model_dump_json()
        restored = Candidate.model_validate_json(json_str)
        assert restored.id == matching_candidate.id
        assert restored.skills == matching_candidate.skills


class TestMatchScoreModel:
    """Tests for match result models."""

    def test_score_bounds(self) -> None:
        """Score must be between 0.0 and 1.0."""
        score = MatchScore(
            category="specialty_match",
            score=0.85,
            explanation="Exact specialty match",
        )
        assert score.score == 0.85

    def test_score_below_zero_fails(self) -> None:
        """Score below 0.0 should fail."""
        with pytest.raises(ValidationError):
            MatchScore(category="test", score=-0.1, explanation="invalid")

    def test_score_above_one_fails(self) -> None:
        """Score above 1.0 should fail."""
        with pytest.raises(ValidationError):
            MatchScore(category="test", score=1.1, explanation="invalid")

    def test_candidate_match_overall_bounds(self) -> None:
        """Overall score must be between 0 and 100."""
        match = CandidateMatch(
            candidate_id="test",
            candidate_name="Dr. Test",
            overall_score=85.5,
            rank=1,
            summary="Good match",
        )
        assert match.overall_score == 85.5

    def test_overall_score_above_100_fails(self) -> None:
        """Overall score above 100 should fail."""
        with pytest.raises(ValidationError):
            CandidateMatch(
                candidate_id="test",
                candidate_name="Dr. Test",
                overall_score=101,
                rank=1,
                summary="Invalid",
            )


class TestFeedbackModel:
    """Tests for RecruiterFeedback model."""

    def test_valid_feedback(self) -> None:
        """Valid feedback should parse."""
        fb = RecruiterFeedback(
            match_id="m001",
            candidate_id="c001",
            feedback_type="good_match",
            notes="Strong candidate, scheduling interview",
        )
        assert fb.feedback_type == "good_match"

    def test_invalid_feedback_type(self) -> None:
        """Invalid feedback type should fail."""
        with pytest.raises(ValidationError):
            RecruiterFeedback(
                match_id="m001",
                candidate_id="c001",
                feedback_type="excellent",  # type: ignore[arg-type]
            )

    def test_notes_optional(self) -> None:
        """Notes field should be optional."""
        fb = RecruiterFeedback(
            match_id="m001",
            candidate_id="c001",
            feedback_type="hired",
        )
        assert fb.notes is None
