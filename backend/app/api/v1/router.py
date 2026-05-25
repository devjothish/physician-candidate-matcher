"""Main API router - assembles all v1 endpoint groups."""

from fastapi import APIRouter

from app.api.v1 import analytics, feedback, match

api_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_router.include_router(match.router)
api_router.include_router(feedback.router)
api_router.include_router(analytics.router)


@api_router.get("/health", tags=["system"])
def health_check() -> dict:
    """Health check endpoint for load balancers and uptime monitors.

    Returns a simple status indicator. Does not check downstream
    dependencies (database, Claude API) to keep response time minimal.
    For deep health checks, use /analytics instead.
    """
    return {"status": "healthy", "service": "physician-candidate-matcher"}
