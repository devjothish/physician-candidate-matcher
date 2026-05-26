# Architecture

Technical architecture reference for the Physician Candidate Matcher. Covers the matching pipeline, scoring engine, LLM integration, guardrails, observability, eval framework, and data model.

## System Overview

```
frontend/                          backend/
  src/                               app/
    app/match/page.tsx                 main.py              <- FastAPI entry, middleware, CORS
    components/                        config.py            <- Settings from env vars
      candidate-card.tsx               api/v1/
      job-form.tsx                       match.py           <- POST /match, POST /batch
      match-results.tsx                  feedback.py        <- POST /feedback, GET /feedback/{id}
    hooks/use-match.ts                   analytics.py       <- GET /analytics, /eval, /health
    lib/api.ts                         services/
                                         matcher.py         <- Orchestrates the 3-phase pipeline
                                         scorer.py          <- Deterministic scoring engine
                                         claude.py          <- Claude API client with retry + cost
                                       core/
                                         guardrails.py      <- Input, output, cost, bias checks
                                         observability.py   <- RequestTrace, PhaseMetrics, health
                                         eval.py            <- Golden set, feedback loop analysis
                                         prompts.py         <- JD_PARSE_PROMPT, BATCH_ASSESSMENT_PROMPT
                                       models/
                                         candidate.py       <- Candidate Pydantic model
                                         job.py             <- JobDescription Pydantic model
                                         match.py           <- MatchResponse, CandidateMatch, MatchScore
                                         feedback.py        <- RecruiterFeedback model
                                       db/repositories/
                                         candidates.py      <- Candidate CRUD via PostgREST
                                         matches.py         <- Match result persistence
                                         feedback.py        <- Feedback CRUD
                                         metrics.py         <- LLM call logging + analytics
                                       utils/
                                         tokens.py          <- Cost calculation per model
                                         logging.py         <- structlog JSON config
                                         exceptions.py      <- MatchingError, ClaudeAPIError, etc.
```

## Two-Phase Matching Pipeline

### Request Flow

```
POST /api/v1/match (JobDescription)
  |
  v
Input Guardrails
  - Prompt injection scan (8 regex patterns)
  - PII redaction (SSN, phone, passport)
  - Length cap (10,000 chars)
  - Minimum length check (20 chars)
  |
  v
Phase 1: JD Parse (1 LLM call)
  Input:  Free-text requirements + title + specialty + location
  Output: ParsedRequirements dataclass
  |
  v
Output Guardrail on ParsedRequirements
  - Validate required_specialty exists
  - Clamp min_years_experience to [0, 50]
  - Verify required_skills is a list
  |
  v
Fetch Candidates from Supabase
  - Filter by specialty (ilike match)
  - Fallback to all candidates if no specialty match
  - Cap at max_candidates_per_request (default 50)
  |
  v
Phase 2: Deterministic Scoring (0 LLM calls, <1ms)
  Input:  list[Candidate] + ParsedRequirements
  Output: list[DeterministicScore], sorted by composite, filtered > 0.25
  |
  v
Phase 3: Batch LLM Assessment (1 LLM call)
  Input:  Top 8 DeterministicScore entries (no candidate names)
  Output: Per-candidate skills_score, summary, strengths, gaps
  |
  v
Output Guardrails on Batch Assessment
  - Reject unknown candidate IDs
  - Clamp skills_score to [0.0, 1.0]
  - Validate strengths/gaps are lists
  - Default empty summary
  |
  v
Merge Results
  - Final score = (deterministic * 0.70) + (LLM skills * 0.30) * 100
  - Sort by overall_score descending
  - Assign ranks 1..N
  |
  v
Post-Merge Guardrails
  - Score bounds: clamp overall_score to [0, 100], per-dimension to [0, 1]
  - Bias detection: flag if avg > 90, avg < 20, or range < 5
  |
  v
Persist to Supabase (matches table)
Emit RequestTrace (structured log)
Return MatchResponse
```

### Data Shapes at Each Phase

**Phase 1 Input** (sent to Claude):
```json
{
  "jd_text": "Seeking a board-certified interventional cardiologist...",
  "title": "Interventional Cardiologist",
  "specialty": "Cardiology",
  "location": "Boston, MA",
  "experience_years": 3,
  "employment_type": "full-time"
}
```

**Phase 1 Output** (`ParsedRequirements` dataclass):
```python
ParsedRequirements(
    required_specialty="Cardiology",
    adjacent_specialties=["Internal Medicine"],
    min_years_experience=3,
    max_years_experience=None,
    required_state_licenses=["MA"],
    preferred_state_licenses=[],
    board_certification_required=True,
    required_skills=["Interventional Cardiology", "Cardiac Catheterization"],
    preferred_skills=["Echocardiography"],
    employment_types=["full-time"],
    max_start_days=None,
    special_requirements=[]
)
```

**Phase 2 Output** (`DeterministicScore` dataclass):
```python
DeterministicScore(
    candidate=<Candidate>,
    specialty_score=1.0,       # exact match
    experience_score=1.0,      # 8 years >= 3 required
    location_score=1.0,        # MA license held
    credentials_score=1.0,     # board certified
    availability_score=0.9,    # 30 days
    employment_score=1.0,      # full-time match
    composite=0.985            # weighted sum after dealbreakers
)
```

**Phase 3 Input** (sent to Claude, no names):
```json
[
  {
    "candidate_id": "c001",
    "specialty": "Cardiology",
    "years_experience": 8,
    "location": "Boston, MA",
    "board_certified": true,
    "licenses": ["MA", "NY", "CT"],
    "education": "Harvard Medical School...",
    "skills": ["Interventional Cardiology", "Cardiac Catheterization"],
    "availability": "30 days",
    "deterministic_score": 99
  }
]
```

**Phase 3 Output** (from Claude):
```json
[
  {
    "candidate_id": "c001",
    "skills_score": 0.92,
    "summary": "Board-certified interventional cardiologist with 8 years...",
    "strengths": ["Fellowship-trained in interventional procedures", "Active MA license"],
    "gaps": []
  }
]
```

## Deterministic Scoring Engine

Location: `backend/app/services/scorer.py`

### Six Dimensions

| Dimension | Weight | Function | Scoring Logic |
|-----------|--------|----------|---------------|
| Specialty Alignment | 35% | `_score_specialty()` | 1.0 = exact match, 0.6 = adjacent specialty, 0.1 = unrelated |
| Experience Fit | 20% | `_score_experience()` | 1.0 = meets minimum, 0.7 = within 2 years, 0.4 = within 5 years, 0.2 = 5+ years short |
| Location & Licensure | 15% | `_score_location()` | 1.0 = holds required license, 0.9 = holds any target, 0.5 = adjacent state, 0.2 = no overlap |
| Board Certification | 15% | `_score_credentials()` | 1.0 = certified (or not required), 0.7 = not certified but not required, 0.3 = not certified when required |
| Availability | 10% | `_score_availability()` | 1.0 = immediate, 0.9 = 30 days, 0.7 = 60 days, 0.5 = 90 days, 0.3 = 90+ days |
| Employment Fit | 5% | `_score_employment()` | 1.0 = preference overlap, 0.4 = no overlap, 0.8 = no requirement specified |

### Composite Score

```
composite = (specialty * 0.35) + (experience * 0.20) + (location * 0.15) 
          + (credentials * 0.15) + (availability * 0.10) + (employment * 0.05)
```

### Dealbreaker Penalties

Applied after the weighted sum via `_apply_dealbreakers()`:

| Condition | Penalty |
|-----------|---------|
| Specialty score <= 0.3 (unrelated specialty) | composite *= 0.4 |
| Credentials score <= 0.4 (not certified when required) | composite *= 0.7 |
| Experience score <= 0.3 (5+ years short) | composite *= 0.75 |
| Location score <= 0.3 (no license overlap) | composite *= 0.75 |

Penalties stack multiplicatively. A candidate with wrong specialty AND missing credentials would get: `composite * 0.4 * 0.7 = composite * 0.28`.

### Location Intelligence

The scorer includes a US state adjacency map (`ADJACENT_STATES` in `scorer.py`) covering 21 states. When a candidate lacks the required state license but holds a license in an adjacent state, they receive a 0.5 location score instead of 0.2. This reflects the reality that physicians often obtain licenses in neighboring states.

### Threshold Filtering

Candidates with `composite < 0.25` are filtered out before Phase 3. This constant (`DETERMINISTIC_THRESHOLD` in `matcher.py`) prevents wasting LLM tokens on clearly unqualified candidates.

## LLM Integration

Location: `backend/app/services/claude.py`

### Client Architecture

`ClaudeService` wraps the Anthropic SDK with:

- **Retry logic** via tenacity: 3 attempts, exponential backoff (2-30s), retry only on transient errors (429, 500, 502, 503, 529)
- **Cost tracking** per call using `calculate_cost()` from `utils/tokens.py`
- **JSON extraction** from Claude responses, handling markdown code fences
- **Metrics persistence** to `llm_calls` table via `MetricsRepository`
- **Structured logging** of every call with request_id, model, prompt_type, tokens, cost, latency, success

### Prompt Design

Two prompts defined in `backend/app/core/prompts.py`:

**`JD_PARSE_PROMPT`** - System: "You extract structured data from job descriptions. Return JSON only." User prompt includes the full JD text plus metadata (title, specialty, location, experience years, employment type). Output is a JSON object matching the `ParsedRequirements` dataclass fields.

**`BATCH_ASSESSMENT_PROMPT`** - System: `MATCHING_SYSTEM_PROMPT` with 5 rules including "NEVER use candidate name, age, gender, race, or demographics in scoring." User prompt includes requirements JSON and candidates JSON (no names). Output is a JSON array with one assessment per candidate.

### Model Configuration

Defined in `backend/app/config.py`:

- `default_model`: `claude-sonnet-4-20250514` (used for both phases)
- `fast_model`: `claude-haiku-4-5-20251001` (used for health checks)

### Cost Per 1K Tokens

| Model | Input | Output |
|-------|-------|--------|
| Claude Sonnet 4 | $0.003 | $0.015 |
| Claude Haiku 4.5 | $0.001 | $0.005 |

## Guardrails Architecture

Location: `backend/app/core/guardrails.py`

Four layers of protection:

### 1. Input Guardrails

`validate_jd_input(text)` runs before the LLM sees any user input.

**Prompt injection detection** - 8 regex patterns including "ignore previous instructions", "you are now a", "ADMIN OVERRIDE", "system:" tags. Matched patterns are replaced with `[REDACTED]`.

**PII redaction** - Detects SSNs (xxx-xx-xxxx), passport numbers (letter + 8 digits), and phone numbers (xxx-xxx-xxxx variants). Replaced with `[REDACTED]`.

**Length enforcement** - Truncates input at 10,000 characters. Rejects input shorter than 20 characters.

### 2. Output Guardrails

**`validate_parsed_requirements(data)`** - Checks Phase 1 LLM output:
- Required specialty must be non-empty
- `min_years_experience` must be an integer in [0, 50]
- `required_skills` must be a list

**`validate_batch_assessment(assessments, shortlist_ids)`** - Checks Phase 3 LLM output:
- Rejects candidate IDs not in the shortlist (prevents hallucinated candidates)
- Clamps `skills_score` to [0.0, 1.0]
- Ensures `strengths` and `gaps` are lists
- Defaults empty summaries
- Warns if fewer assessments returned than expected

**`validate_match_scores(matches)`** - Post-merge validation:
- Clamps `overall_score` to [0, 100]
- Clamps per-dimension scores to [0, 1]

### 3. Cost Guardrails

- `MAX_COST_PER_REQUEST_USD = 0.50` - circuit breaker on single request spend
- `MAX_DAILY_COST_USD = 25.00` - daily spend cap
- `check_request_cost()` runs pre-flight before LLM calls

### 4. Bias Guardrails

`check_scoring_bias(candidates, matches)` flags:
- Average score > 90 (suspiciously high, likely insufficient differentiation)
- Average score < 20 (suspiciously low, likely scoring bug)
- Score range < 5 with 3+ candidates (insufficient differentiation)

All warnings are attached to the `RequestTrace` and logged as structured events.

## Observability Architecture

Location: `backend/app/core/observability.py`

### RequestTrace

Every match request creates a `RequestTrace(request_id, job_title)` that accumulates:

- **PhaseMetrics** per phase: name, latency_ms, llm_calls, input_tokens, output_tokens, cost_usd, items_in, items_out
- **Guardrail warnings**: list of string identifiers
- **Computed properties**: total_latency_ms, total_llm_calls, total_cost_usd, total_tokens

### Trace Emission

`trace.emit()` writes a structured log with:

```json
{
  "event": "request_trace",
  "request_id": "uuid",
  "job_title": "Interventional Cardiologist",
  "total_latency_ms": 4532.1,
  "total_llm_calls": 2,
  "total_cost_usd": 0.00312,
  "total_tokens": 3847,
  "phases": {
    "jd_parse": {"latency_ms": 1200.3, "llm_calls": 1, "cost_usd": 0.00180, "tokens": 1024, "funnel": "1->1"},
    "deterministic_score": {"latency_ms": 0.8, "llm_calls": 0, "cost_usd": 0.0, "tokens": 0, "funnel": "30->12"},
    "llm_assessment": {"latency_ms": 3100.5, "llm_calls": 1, "cost_usd": 0.00132, "tokens": 2823, "funnel": "8->8"}
  },
  "guardrail_warnings": null
}
```

### Automatic Alerts

After trace emission, the system logs warnings for:
- Latency > 30,000ms
- Cost > $0.10 per request
- Any guardrail warning triggered

### Deep Health Check

`deep_health_check()` tests downstream dependencies:
- **Supabase**: fetches 1 row from candidates table, reports latency
- **Claude API**: sends a "ping" message to the fast model, reports latency

Returns per-dependency status (healthy/unhealthy) with error details on failure.

### HTTP Request Logging

Middleware in `main.py` logs every request with method, path, status_code, latency_ms, and client_ip. PII-safe: does not log request bodies, headers, or query parameters.

### Structured Logging

`structlog` configured in `backend/app/utils/logging.py`:
- JSON rendering in production
- Console rendering in development
- Noisy libraries (httpx, httpcore, uvicorn.access) set to WARNING

## Eval Framework

Location: `backend/app/core/eval.py`

### Design Principles

1. No LLM calls required to run evals
2. Deterministic and repeatable
3. Fast (runs in <10ms)

### Golden Set

5 test cases defined in `GOLDEN_SET`, each with:
- `case_id` and `description`
- Full `requirements` dict matching `ParsedRequirements`
- Full `candidate` dict matching `Candidate`
- `expected_outcome`: strong_match, weak_match, or no_match
- `expected_score_min` and `expected_score_max`: acceptable composite range
- `critical_dimensions`: which dimensions should be high or low

**Cases:**

| Case | Tests | Expected |
|------|-------|----------|
| GS001 | Perfect match on all dimensions | strong_match, score 0.75-1.0 |
| GS002 | Wrong specialty (Pediatrics vs Cardiology) | no_match, score 0.0-0.45 |
| GS003 | Not board certified when required | weak_match, score 0.40-0.70 |
| GS004 | Wrong state license (PA/NJ vs AZ required) | weak_match, score 0.45-0.75 |
| GS005 | Insufficient experience (3 years vs 10 required) | weak_match, score 0.40-0.70 |

### Eval Execution

`run_golden_set()` iterates all cases, runs `score_candidate()`, checks:
1. Composite score falls within expected range
2. Critical dimensions match expected levels (high >= 0.7, low <= 0.6)

Returns a summary with pass/fail counts, per-case details, and failure reasons.

### Feedback Loop Analysis

`analyze_feedback(feedback_data)` processes recruiter feedback to detect quality drift:
- Tracks good/bad/hired ratios
- Alerts if good_match_rate < 50% after 10+ feedback entries
- Alerts if good_match_rate < 60% after 20+ feedback entries

## Database Schema

5 tables, 2 views. Full schema in `docs/schema.sql`.

### Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `candidates` | Physician talent pool | id, specialty, years_experience, board_certified, licenses[], skills[] |
| `matches` | Scoring history per candidate per job | overall_score, rank, scores (JSONB), model_used, cost_usd, request_id |
| `feedback` | Recruiter quality signals | match_id FK, feedback_type (good_match/bad_match/hired/interviewed) |
| `llm_calls` | LLM usage metrics | model, prompt_type, input_tokens, output_tokens, cost_usd, success |
| `api_requests` | HTTP request logging | method, path, status_code, latency_ms |

### Views

- `analytics_summary` - Aggregates total matches, unique candidates, total cost, feedback breakdown
- `daily_costs` - Per-day cost aggregation from llm_calls

### Indexes

Covering indexes on: `candidates.specialty`, `candidates.location`, `matches.created_at DESC`, `matches.request_id`, `matches.candidate_id`, `feedback.match_id`, `llm_calls.created_at DESC`, `llm_calls.request_id`.

### Constraints

- `CHECK (years_experience >= 0)` on candidates
- `CHECK (overall_score >= 0 AND overall_score <= 100)` on matches
- `CHECK (feedback_type IN ('good_match', 'bad_match', 'hired', 'interviewed'))` on feedback
- `CHECK (input_tokens >= 0)` and `CHECK (cost_usd >= 0)` on llm_calls
- Foreign keys with `ON DELETE CASCADE` from matches/feedback to candidates

## Error Handling Strategy

### Exception Hierarchy

```
HTTPException (FastAPI)
  MatchingError     -> 500  "Matching service error"
  ClaudeAPIError    -> 502  "LLM service unavailable"
  ValidationError   -> 400  "Validation error"
  RateLimitError    -> 429  "Rate limit exceeded"
```

### Retry Policy

Only transient Claude API errors trigger retry:
- Status codes: 429 (rate limit), 500, 502, 503, 529
- Strategy: exponential backoff, multiplier=1, min=2s, max=30s
- Max attempts: 3

Non-retryable errors (400, 401, 403) raise immediately.

### Global Exception Handler

Unhandled exceptions in `main.py` return a generic 500 response with `{"detail": "Internal server error"}`. The actual exception is logged with full traceback via `logger.exception()`.

### Match Persistence Failure

If saving match results to Supabase fails, the error is logged but the response is still returned to the client. Match data is transient; losing persistence is acceptable compared to failing the entire request.

## Security Considerations

### Prompt Injection

8 regex patterns in `guardrails.py` detect common injection attempts. Matched text is replaced with `[REDACTED]` before reaching the LLM. The patterns cover instruction override, role reassignment, and system prompt extraction attempts.

### PII Protection

- SSNs, passport numbers, and phone numbers are redacted from JD input before LLM processing
- Candidate names are excluded from the LLM scoring payload (`_batch_assess()` builds a dict without the `name` field)
- HTTP request logging middleware does not log request bodies, headers, or query parameters

### PostgREST Injection

`CandidateRepository.get_by_specialty()` sanitizes the specialty parameter with `re.sub(r"[^a-zA-Z0-9 /\-]", "", specialty)` before passing it as an `ilike` filter to PostgREST.

### CORS

Production: only `https://physician-matcher.vercel.app` is allowed.
Development: `localhost:3000`, `localhost:5173`, `127.0.0.1:3000`.

### Rate Limiting

- `/api/v1/match`: 20 requests/minute per IP
- `/api/v1/batch`: 5 requests/minute per IP

### Docker Security

Multi-stage build runs as non-root `appuser`. No build tools in production image.

### Row Level Security

RLS policies are defined but commented out in `schema.sql`. Ready to enable for multi-tenant production use.
