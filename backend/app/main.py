"""FastAPI application entry point.

Configures middleware, rate limiting, CORS, and request logging.
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.config import get_settings
from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    setup_logging()
    settings = get_settings()
    logger.info(
        "application_starting",
        environment=settings.environment,
        default_model=settings.default_model,
        fast_model=settings.fast_model,
        rate_limit=settings.rate_limit_per_minute,
    )
    yield
    logger.info("application_shutting_down")


# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Physician Candidate Matcher",
    description=(
        "AI-powered physician candidate matching for healthcare recruiters. "
        "Uses Claude to evaluate and rank physician candidates against "
        "job descriptions with detailed scoring breakdowns."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """Log every HTTP request with method, path, status, and latency.

    PII-safe: does not log request bodies, headers, or query parameters
    that might contain patient or candidate information.
    """
    start_time = time.time()
    response: Response = await call_next(request)
    latency_ms = (time.time() - start_time) * 1000

    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=round(latency_ms, 1),
        client_ip=request.client.host if request.client else "unknown",
    )

    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include API router
app.include_router(api_router)


@app.get("/", tags=["system"])
def root() -> dict:
    """Root endpoint with service info and documentation links."""
    return {
        "name": "Physician Candidate Matcher",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
