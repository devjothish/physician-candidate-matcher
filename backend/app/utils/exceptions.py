"""Custom exception hierarchy for structured error responses.

All exceptions inherit from FastAPI's HTTPException so they are
automatically rendered as proper HTTP error responses by the framework.
"""

from fastapi import HTTPException


class MatchingError(HTTPException):
    """Raised when the matching service encounters an unrecoverable error."""

    def __init__(self, detail: str = "Matching service error") -> None:
        super().__init__(status_code=500, detail=detail)


class ValidationError(HTTPException):
    """Raised when request validation fails beyond Pydantic checks."""

    def __init__(self, detail: str = "Validation error") -> None:
        super().__init__(status_code=400, detail=detail)


class RateLimitError(HTTPException):
    """Raised when a client exceeds the configured rate limit."""

    def __init__(self, detail: str = "Rate limit exceeded. Please try again later.") -> None:
        super().__init__(status_code=429, detail=detail)


class ClaudeAPIError(HTTPException):
    """Raised when the Claude API returns an error or is unreachable."""

    def __init__(self, detail: str = "LLM service unavailable") -> None:
        super().__init__(status_code=502, detail=detail)
