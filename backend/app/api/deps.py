"""Dependency injection functions for FastAPI route handlers.

Centralizes service and repository instantiation so routes stay thin
and testable (swap deps in tests via dependency_overrides).
"""

from app.db.repositories.feedback import FeedbackRepository
from app.services.matcher import MatchingService


def get_matching_service() -> MatchingService:
    """Provide a MatchingService instance.

    Returns:
        A configured MatchingService ready for use.
    """
    return MatchingService()


def get_feedback_repo() -> FeedbackRepository:
    """Provide a FeedbackRepository instance.

    Returns:
        A configured FeedbackRepository ready for use.
    """
    return FeedbackRepository()
