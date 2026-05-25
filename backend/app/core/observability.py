"""Observability: request tracing, phase metrics, cost tracking, and alerting.

Every match request gets a RequestTrace that tracks:
  - Per-phase latency (JD parse, deterministic scoring, LLM assessment)
  - Per-phase token usage and cost
  - Candidate funnel (total → shortlisted → returned)
  - Guardrail triggers
  - Final quality signals
"""

import time
from dataclasses import dataclass, field

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PhaseMetrics:
    name: str
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    llm_calls: int = 0
    items_in: int = 0
    items_out: int = 0


@dataclass
class RequestTrace:
    """End-to-end trace for a single match request."""

    request_id: str
    job_title: str = ""
    start_time: float = field(default_factory=time.time)
    phases: list[PhaseMetrics] = field(default_factory=list)
    guardrail_warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def add_phase(self, phase: PhaseMetrics) -> None:
        self.phases.append(phase)

    def add_warning(self, warning: str) -> None:
        self.guardrail_warnings.append(warning)

    @property
    def total_latency_ms(self) -> float:
        return (time.time() - self.start_time) * 1000

    @property
    def total_llm_calls(self) -> int:
        return sum(p.llm_calls for p in self.phases)

    @property
    def total_cost_usd(self) -> float:
        return sum(p.cost_usd for p in self.phases)

    @property
    def total_tokens(self) -> int:
        return sum(p.input_tokens + p.output_tokens for p in self.phases)

    def emit(self) -> None:
        """Emit the full trace as a structured log event."""
        phase_summary = {
            p.name: {
                "latency_ms": round(p.latency_ms, 1),
                "llm_calls": p.llm_calls,
                "cost_usd": round(p.cost_usd, 5),
                "tokens": p.input_tokens + p.output_tokens,
                "funnel": f"{p.items_in}→{p.items_out}",
            }
            for p in self.phases
        }

        logger.info(
            "request_trace",
            request_id=self.request_id,
            job_title=self.job_title,
            total_latency_ms=round(self.total_latency_ms, 1),
            total_llm_calls=self.total_llm_calls,
            total_cost_usd=round(self.total_cost_usd, 5),
            total_tokens=self.total_tokens,
            phases=phase_summary,
            guardrail_warnings=self.guardrail_warnings or None,
            error=self.error,
        )

        if self.total_latency_ms > 30000:
            logger.warning(
                "alert_high_latency",
                request_id=self.request_id,
                latency_ms=round(self.total_latency_ms),
            )

        if self.total_cost_usd > 0.10:
            logger.warning(
                "alert_high_cost",
                request_id=self.request_id,
                cost_usd=round(self.total_cost_usd, 4),
            )

        if self.guardrail_warnings:
            logger.warning(
                "alert_guardrails_triggered",
                request_id=self.request_id,
                warnings=self.guardrail_warnings,
            )


# ── Deep Health Check ─────────────────────────────────────────────────


def deep_health_check() -> dict:
    """Check connectivity to all downstream dependencies."""
    results: dict[str, dict] = {}

    # Supabase
    try:
        import httpx

        from app.config import get_settings as _get_settings

        s = _get_settings()
        start = time.time()
        r = httpx.get(
            f"{s.supabase_url}/rest/v1/candidates",
            headers={"apikey": s.supabase_key, "Authorization": f"Bearer {s.supabase_key}"},
            params={"select": "id", "limit": "1"},
            timeout=5.0,
        )
        r.raise_for_status()
        latency = (time.time() - start) * 1000
        results["supabase"] = {
            "status": "healthy",
            "latency_ms": round(latency, 1),
        }
    except Exception as e:
        results["supabase"] = {"status": "unhealthy", "error": str(e)[:200]}

    # Claude API
    try:
        import anthropic

        from app.config import get_settings

        settings = get_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        start = time.time()
        r = client.messages.create(
            model=settings.fast_model,
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        latency = (time.time() - start) * 1000
        results["claude_api"] = {
            "status": "healthy",
            "latency_ms": round(latency, 1),
            "model": settings.fast_model,
        }
    except Exception as e:
        results["claude_api"] = {"status": "unhealthy", "error": str(e)[:200]}

    overall = all(v["status"] == "healthy" for v in results.values())
    return {"status": "healthy" if overall else "degraded", "checks": results}
