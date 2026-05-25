-- Physician Candidate Matcher - Supabase Schema
-- Run this in Supabase SQL Editor to set up the database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Candidates table
CREATE TABLE candidates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    specialty TEXT NOT NULL,
    years_experience INTEGER NOT NULL CHECK (years_experience >= 0),
    location TEXT NOT NULL,
    board_certified BOOLEAN NOT NULL DEFAULT false,
    licenses TEXT[] NOT NULL DEFAULT '{}',
    education TEXT,
    skills TEXT[] NOT NULL DEFAULT '{}',
    availability TEXT,
    preferred_employment TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_candidates_specialty ON candidates(specialty);
CREATE INDEX idx_candidates_location ON candidates(location);
CREATE INDEX idx_candidates_board_certified ON candidates(board_certified);

-- Matches table (scoring history)
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_title TEXT NOT NULL,
    job_specialty TEXT NOT NULL,
    job_location TEXT NOT NULL,
    job_requirements TEXT NOT NULL,
    candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    overall_score REAL NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    rank INTEGER NOT NULL CHECK (rank >= 1),
    scores JSONB NOT NULL,
    summary TEXT,
    strengths TEXT[] NOT NULL DEFAULT '{}',
    gaps TEXT[] NOT NULL DEFAULT '{}',
    model_used TEXT NOT NULL,
    tokens_used INTEGER NOT NULL CHECK (tokens_used >= 0),
    cost_usd REAL NOT NULL CHECK (cost_usd >= 0),
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    request_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_matches_created_at ON matches(created_at DESC);
CREATE INDEX idx_matches_job_specialty ON matches(job_specialty);
CREATE INDEX idx_matches_request_id ON matches(request_id);
CREATE INDEX idx_matches_candidate_id ON matches(candidate_id);

-- Feedback table (recruiter quality signals)
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('good_match', 'bad_match', 'hired', 'interviewed')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_match_id ON feedback(match_id);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);

-- LLM calls table (observability / cost tracking)
CREATE TABLE llm_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_type TEXT NOT NULL,
    input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
    output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    cost_usd REAL NOT NULL CHECK (cost_usd >= 0),
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_llm_calls_created_at ON llm_calls(created_at DESC);
CREATE INDEX idx_llm_calls_model ON llm_calls(model);
CREATE INDEX idx_llm_calls_request_id ON llm_calls(request_id);

-- API requests table (request-level logging)
CREATE TABLE api_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_requests_created_at ON api_requests(created_at DESC);

-- Analytics summary view
CREATE OR REPLACE VIEW analytics_summary AS
SELECT
    COUNT(DISTINCT m.id) AS total_matches,
    COUNT(DISTINCT m.candidate_id) AS unique_candidates,
    COALESCE(SUM(m.tokens_used), 0) AS total_tokens,
    COALESCE(SUM(m.cost_usd), 0) AS total_cost,
    COALESCE(AVG(m.latency_ms), 0) AS avg_latency_ms,
    COUNT(CASE WHEN f.feedback_type = 'good_match' THEN 1 END) AS good_matches,
    COUNT(CASE WHEN f.feedback_type = 'bad_match' THEN 1 END) AS bad_matches,
    COUNT(CASE WHEN f.feedback_type = 'hired' THEN 1 END) AS hired
FROM matches m
LEFT JOIN feedback f ON m.id = f.match_id;

-- Daily cost aggregation view
CREATE OR REPLACE VIEW daily_costs AS
SELECT
    DATE(created_at) AS date,
    SUM(cost_usd) AS total_cost,
    COUNT(*) AS total_calls,
    SUM(input_tokens + output_tokens) AS total_tokens,
    AVG(latency_ms) AS avg_latency_ms
FROM llm_calls
WHERE success = true
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Row Level Security (RLS) - enable for production
-- ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE llm_calls ENABLE ROW LEVEL SECURITY;

-- Updated_at trigger for candidates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
