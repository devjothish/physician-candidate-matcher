"""Repository for LLM usage metrics and analytics.

Uses direct REST calls to avoid Supabase SDK thread-safety issues.
"""

from datetime import UTC, datetime

import httpx

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class MetricsRepository:
    TABLE = "llm_calls"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = f"{settings.supabase_url}/rest/v1"
        self.headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    def log_llm_call(
        self,
        request_id: str,
        model: str,
        prompt_type: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        cost_usd: float,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        record = {
            "request_id": request_id,
            "model": model,
            "prompt_type": prompt_type,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": int(latency_ms),
            "cost_usd": cost_usd,
            "success": success,
            "error_message": error_message,
            "created_at": datetime.now(UTC).isoformat(),
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
                "metrics_log_failed",
                request_id=request_id,
                model=model,
            )

    def get_analytics(self) -> dict:
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(
                    f"{self.base_url}/{self.TABLE}",
                    headers={**self.headers, "Prefer": ""},
                    params={"select": "*", "order": "created_at.desc", "limit": "500"},
                )
                r.raise_for_status()
                rows = r.json()

            if not rows:
                return {
                    "total_calls": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_cost_usd": 0.0,
                    "avg_latency_ms": 0.0,
                    "success_rate": 0.0,
                    "by_model": {},
                }

            total_calls = len(rows)
            total_input = sum(r.get("input_tokens", 0) for r in rows)
            total_output = sum(r.get("output_tokens", 0) for r in rows)
            total_cost = sum(r.get("cost_usd", 0.0) for r in rows)
            avg_latency = sum(r.get("latency_ms", 0.0) for r in rows) / total_calls
            successes = sum(1 for r in rows if r.get("success"))
            success_rate = successes / total_calls if total_calls > 0 else 0.0

            by_model: dict[str, dict] = {}
            for row in rows:
                model = row.get("model", "unknown")
                if model not in by_model:
                    by_model[model] = {"calls": 0, "total_cost_usd": 0.0, "total_tokens": 0}
                by_model[model]["calls"] += 1
                by_model[model]["total_cost_usd"] += row.get("cost_usd", 0.0)
                by_model[model]["total_tokens"] += row.get("input_tokens", 0) + row.get("output_tokens", 0)

            return {
                "total_calls": total_calls,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_cost_usd": round(total_cost, 4),
                "avg_latency_ms": round(avg_latency, 1),
                "success_rate": round(success_rate, 3),
                "by_model": by_model,
            }
        except Exception:
            logger.exception("analytics_query_failed")
            return {
                "total_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
                "success_rate": 0.0,
                "by_model": {},
            }
