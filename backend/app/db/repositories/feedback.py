"""Repository for recruiter feedback on match quality.

Uses direct REST calls to avoid Supabase SDK thread-safety issues.
"""

from datetime import UTC, datetime

import httpx

from app.config import get_settings
from app.models.feedback import RecruiterFeedback
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FeedbackRepository:
    TABLE = "feedback"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = f"{settings.supabase_url}/rest/v1"
        self.headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
        }

    def create(self, feedback: RecruiterFeedback) -> dict | None:
        record = {
            "match_id": feedback.match_id,
            "candidate_id": feedback.candidate_id,
            "feedback_type": feedback.feedback_type,
            "notes": feedback.notes,
            "created_at": datetime.now(UTC).isoformat(),
        }

        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.post(
                    f"{self.base_url}/{self.TABLE}",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=record,
                )
                r.raise_for_status()
                data = r.json()
                logger.info(
                    "feedback_saved",
                    match_id=feedback.match_id,
                    feedback_type=feedback.feedback_type,
                )
                return data[0] if data else None
        except Exception:
            logger.exception("feedback_save_failed", match_id=feedback.match_id)
            return None

    def get_by_match(self, match_id: str) -> list[dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(
                    f"{self.base_url}/{self.TABLE}",
                    headers=self.headers,
                    params={
                        "select": "*",
                        "match_id": f"eq.{match_id}",
                        "order": "created_at.desc",
                    },
                )
                r.raise_for_status()
                return r.json()
        except Exception:
            logger.exception("feedback_fetch_failed", match_id=match_id)
            return []
