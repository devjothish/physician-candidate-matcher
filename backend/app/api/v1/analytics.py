"""Analytics, eval, and health endpoints."""

from fastapi import APIRouter, Query

from app.core.eval import run_golden_set
from app.core.observability import deep_health_check
from app.db.repositories.matches import MatchRepository
from app.db.repositories.metrics import MetricsRepository
from app.db.repositories.feedback import FeedbackRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
def get_analytics() -> dict:
    """Get aggregate usage analytics.

    Returns total matches, LLM costs, average latency, success rates,
    and feedback breakdown across all matching requests.
    """
    metrics_repo = MetricsRepository()
    match_repo = MatchRepository()

    llm_analytics = metrics_repo.get_analytics()
    recent_matches = match_repo.get_recent(limit=100)

    # Feedback summary
    feedback_repo = FeedbackRepository()
    feedback_summary: dict[str, int] = {
        "good_match": 0,
        "bad_match": 0,
        "hired": 0,
        "interviewed": 0,
    }

    # Aggregate feedback from recent matches
    for match in recent_matches:
        match_id = match.get("id")
        if match_id:
            feedback_entries = feedback_repo.get_by_match(str(match_id))
            for entry in feedback_entries:
                ft = entry.get("feedback_type", "")
                if ft in feedback_summary:
                    feedback_summary[ft] += 1

    return {
        "total_matches": len(recent_matches),
        "unique_candidates": 0,
        "total_tokens": llm_analytics.get("total_input_tokens", 0) + llm_analytics.get("total_output_tokens", 0),
        "total_cost": llm_analytics.get("total_cost_usd", 0.0),
        "avg_latency_ms": llm_analytics.get("avg_latency_ms", 0.0),
        "good_matches": feedback_summary.get("good_match", 0),
        "bad_matches": feedback_summary.get("bad_match", 0),
        "hired": feedback_summary.get("hired", 0),
        "llm_usage": llm_analytics,
        "feedback_summary": feedback_summary,
    }


@router.get("/analytics/costs")
def get_cost_analytics(
    days: int = Query(default=30, ge=1, le=365, description="Days of history"),
) -> list:
    """Get cost-over-time data for budget monitoring.

    Returns per-day cost aggregation from the metrics table.
    """
    metrics_repo = MetricsRepository()

    try:
        import httpx
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                f"{metrics_repo.base_url}/{metrics_repo.TABLE}",
                headers={**metrics_repo.headers, "Prefer": ""},
                params={
                    "select": "created_at,cost_usd,model",
                    "created_at": f"gte.{cutoff}",
                    "order": "created_at.desc",
                    "limit": "500",
                },
            )
            r.raise_for_status()
            rows = r.json()

        daily_costs: dict[str, dict[str, float]] = {}
        for row in rows:
            created = row.get("created_at", "")[:10]
            cost = row.get("cost_usd", 0.0)

            if created not in daily_costs:
                daily_costs[created] = {"total": 0.0, "calls": 0}

            daily_costs[created]["total"] += cost
            daily_costs[created]["calls"] += 1

        return [
            {"date": date, "cost": round(vals["total"], 4), "calls": int(vals["calls"])}
            for date, vals in sorted(daily_costs.items())
        ]
    except Exception:
        logger.exception("cost_analytics_failed")
        return []


@router.get("/eval/golden-set", tags=["eval"])
def run_eval() -> dict:
    """Run golden set evaluation against deterministic scorer.

    Zero LLM calls. Tests 5 cases covering specialty mismatch,
    credential gaps, location misses, and experience shortfalls.
    Returns pass/fail per case with actual vs expected scores.
    """
    return run_golden_set()


@router.get("/health/deep", tags=["system"])
def deep_health() -> dict:
    """Deep health check - tests Supabase and Claude API connectivity.

    Use /api/v1/health for load balancer pings (no downstream calls).
    Use this endpoint for operational monitoring.
    """
    return deep_health_check()
