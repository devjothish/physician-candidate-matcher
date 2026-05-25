"""Match endpoints - the primary API surface for physician-job matching."""

from fastapi import APIRouter, Depends, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_matching_service
from app.models.job import JobDescription
from app.models.match import MatchResponse
from app.services.matcher import MatchingService
from app.utils.exceptions import ValidationError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["matching"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/match", response_model=MatchResponse)
@limiter.limit("20/minute")
def match_candidates(
    request: Request,
    job: JobDescription,
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
    service: MatchingService = Depends(get_matching_service),
) -> MatchResponse:
    """Match physician candidates against a job description.

    Two-phase architecture: deterministic scoring on all candidates,
    then LLM assessment on the shortlist.

    Rate limited to 20 requests per minute per client IP.
    """
    logger.info(
        "match_request_received",
        job_title=job.title,
        specialty=job.specialty,
        limit=limit,
    )
    return service.match(job=job, limit=limit)


@router.post("/batch")
@limiter.limit("5/minute")
def batch_match(
    request: Request,
    jobs: list[JobDescription],
    limit: int = Query(default=10, ge=1, le=50, description="Max results per job"),
    service: MatchingService = Depends(get_matching_service),
) -> list[dict]:
    """Batch match candidates against multiple job descriptions.

    Maximum 5 jobs per batch. Returns per-job status with result or error.
    """
    if len(jobs) > 5:
        raise ValidationError(detail="Maximum 5 jobs per batch request.")
    if not jobs:
        raise ValidationError(detail="At least one job description is required.")

    logger.info("batch_match_request", job_count=len(jobs))

    results: list[dict] = []
    for job in jobs:
        try:
            result = service.match(job=job, limit=limit)
            results.append({"job_title": job.title, "status": "success", "result": result})
        except Exception as e:
            logger.exception("batch_job_failed", job_title=job.title)
            results.append({"job_title": job.title, "status": "failed", "error": str(e)[:200]})

    return results
