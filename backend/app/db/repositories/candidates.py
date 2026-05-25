"""Repository for physician candidate data access.

Uses direct REST calls instead of the Supabase SDK to avoid
thread-safety issues with the SDK's httpx client in uvicorn's
thread pool.
"""

import httpx

from app.config import get_settings
from app.models.candidate import Candidate
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CandidateRepository:
    TABLE = "candidates"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = f"{settings.supabase_url}/rest/v1"
        self.headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
        }
        self._client = httpx.Client(timeout=10.0, headers=self.headers)

    def _fetch(self, params: dict) -> list[dict]:
        r = self._client.get(
            f"{self.base_url}/{self.TABLE}",
            params=params,
        )
        r.raise_for_status()
        return r.json()

    def get_all(self, limit: int = 50) -> list[Candidate]:
        data = self._fetch({"select": "*", "limit": str(limit)})
        logger.info("fetched_candidates", count=len(data))
        return [Candidate(**row) for row in data]

    def get_by_specialty(self, specialty: str, limit: int = 50) -> list[Candidate]:
        import re
        safe_specialty = re.sub(r"[^a-zA-Z0-9 /\-]", "", specialty)
        data = self._fetch({
            "select": "*",
            "specialty": f"ilike.*{safe_specialty}*",
            "limit": str(limit),
        })
        logger.info(
            "fetched_candidates_by_specialty",
            specialty=specialty,
            count=len(data),
        )
        return [Candidate(**row) for row in data]

    def get_by_id(self, candidate_id: str) -> Candidate | None:
        data = self._fetch({
            "select": "*",
            "id": f"eq.{candidate_id}",
            "limit": "1",
        })
        if not data:
            return None
        return Candidate(**data[0])
