"""Match result models returned by the matching service."""

from pydantic import BaseModel, Field


class MatchScore(BaseModel):
    """Individual scoring category result."""

    category: str = Field(..., description="Scoring dimension, e.g. 'specialty'")
    score: float = Field(..., ge=0.0, le=1.0, description="Score from 0.0 to 1.0")
    explanation: str = Field(..., description="Factual explanation for the score")


class CandidateMatch(BaseModel):
    """A single candidate's match result against a job description."""

    match_id: str = Field(default="", description="Database row ID for feedback reference")
    candidate_id: str
    candidate_name: str
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Weighted overall score 0-100")
    rank: int = Field(default=0, ge=0, description="Rank among matched candidates")
    scores: list[MatchScore] = Field(default_factory=list, description="Per-category score breakdown")
    summary: str = Field(..., description="Brief match summary")
    strengths: list[str] = Field(default_factory=list, description="Key strengths for this role")
    gaps: list[str] = Field(default_factory=list, description="Gaps or concerns")


class MatchResponse(BaseModel):
    """Full response from a matching request, including metrics."""

    model_config = {"protected_namespaces": ()}

    job_title: str
    total_candidates: int = Field(..., description="Number of candidates evaluated")
    matches: list[CandidateMatch] = Field(default_factory=list, description="Ranked candidate matches")
    processing_time_ms: float = Field(..., description="Total wall-clock time in milliseconds")
    model_used: str = Field(..., description="Claude model used for matching")
    tokens_used: int = Field(..., description="Total tokens consumed")
    estimated_cost_usd: float = Field(..., description="Estimated API cost in USD")
    request_id: str = Field(..., description="Unique request identifier for tracing")
