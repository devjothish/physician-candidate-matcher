"""Repository for match result persistence.

Uses direct REST calls to avoid Supabase SDK thread-safety issues.
"""

import json
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.models.job import JobDescription
from app.models.match import MatchResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)


class MatchRepository:
    TABLE = "matches"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = f"{settings.supabase_url}/rest/v1"
        self.headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    def create(
        self,
        job: JobDescription,
        match_response: MatchResponse,
        model_used: str,
        tokens_used: int,
        cost_usd: float,
        latency_ms: float,
    ) -> None:
        for m in match_response.matches:
            record = {
                "job_title": job.title,
                "job_specialty": job.specialty,
                "job_location": job.location,
                "job_requirements": job.requirements[:2000],
                "candidate_id": m.candidate_id,
                "overall_score": m.overall_score,
                "rank": m.rank,
                "scores": json.loads(json.dumps([s.model_dump() for s in m.scores])),
                "summary": m.summary,
                "strengths": m.strengths,
                "gaps": m.gaps,
                "model_used": model_used,
                "tokens_used": tokens_used // max(len(match_response.matches), 1),
                "cost_usd": round(cost_usd / max(len(match_response.matches), 1), 6),
                "latency_ms": int(latency_ms // max(len(match_response.matches), 1)),
                "request_id": match_response.request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            try:
                with httpx.Client(timeout=5.0) as client:
                    r = client.post(
                        f"{self.base_url}/{self.TABLE}",
                        headers=self.headers,
                        json=record,
                    )
                    r.raise_for_status()
            except Exception:
                logger.exception(
                    "match_save_failed",
                    request_id=match_response.request_id,
                    candidate_id=m.candidate_id,
                )

    def get_recent(self, limit: int = 50) -> list[dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(
                    f"{self.base_url}/{self.TABLE}",
                    headers={**self.headers, "Prefer": ""},
                    params={
                        "select": "*",
                        "order": "created_at.desc",
                        "limit": str(limit),
                    },
                )
                r.raise_for_status()
                return r.json()
        except Exception:
            logger.exception("match_fetch_failed")
            return []
