"""Feedback endpoints for recruiter match quality tracking."""

from fastapi import APIRouter, Depends

from app.api.deps import get_feedback_repo
from app.db.repositories.feedback import FeedbackRepository
from app.models.feedback import RecruiterFeedback
from app.utils.exceptions import MatchingError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["feedback"])


@router.post("/feedback")
def submit_feedback(
    feedback: RecruiterFeedback,
    repo: FeedbackRepository = Depends(get_feedback_repo),
) -> dict:
    """Submit recruiter feedback on a candidate match.

    Feedback is used to track match quality over time and identify
    scoring calibration issues.
    """
    logger.info(
        "feedback_submitted",
        match_id=feedback.match_id,
        feedback_type=feedback.feedback_type,
    )
    result = repo.create(feedback)
    if result is None:
        raise MatchingError(detail="Failed to save feedback")
    return {"status": "saved", "feedback": result}


@router.get("/feedback/{match_id}")
def get_feedback(
    match_id: str,
    repo: FeedbackRepository = Depends(get_feedback_repo),
) -> dict:
    """Get all feedback for a specific match.

    Returns all recruiter feedback entries associated with the given match ID.
    """
    feedback_list = repo.get_by_match(match_id)
    return {
        "match_id": match_id,
        "feedback_count": len(feedback_list),
        "feedback": feedback_list,
    }
