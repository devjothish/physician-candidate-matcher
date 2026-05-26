# System Design: Physician Candidate Matcher

An interview-style system design document covering requirements, architecture decisions, trade-offs, and scaling considerations.

## Problem Statement

Design a system that matches physician candidates to healthcare job openings. A recruiter pastes a job description, and the system returns a ranked list of candidates with scores, explanations, strengths, and gaps.

### Functional Requirements

1. Accept a free-text job description and return ranked candidate matches
2. Score candidates on specialty, experience, location/licensure, credentials, availability, and employment fit
3. Provide natural-language summaries a recruiter can forward to a hiring manager
4. Identify specific strengths and gaps for each candidate
5. Collect recruiter feedback (good match, bad match, hired, interviewed) for quality tracking
6. Batch matching: process up to 5 job descriptions in a single request
7. Track usage analytics: total matches, LLM costs, latency, feedback breakdown

### Non-Functional Requirements

1. **Latency**: < 10 seconds for a single match request
2. **Cost**: < $0.01 per match request at steady state
3. **Accuracy**: golden set eval passes 5/5 test cases
4. **Availability**: standard web app SLA, no real-time requirements
5. **Security**: no PII sent to LLM scoring, prompt injection protection, input sanitization
6. **Observability**: per-request tracing with phase-level metrics
7. **Bias**: demographic information excluded from scoring pipeline

## Capacity Estimation

### Target Scale

For a healthcare staffing firm like M3 USA:

| Metric | Estimate |
|--------|----------|
| Active job openings | 50-200 at any time |
| Candidate pool | 30-500 physicians in database |
| Match requests/day | 50-100 |
| Match requests/month | 1,500-3,000 |

### Cost Projection

At $0.003 per match (two-phase architecture):

| Volume | Monthly Cost | Annual Cost |
|--------|-------------|-------------|
| 1,000 matches/month | $3.00 | $36.00 |
| 3,000 matches/month | $9.00 | $108.00 |
| 10,000 matches/month | $30.00 | $360.00 |

Compare to V1 (per-candidate LLM) at $0.27 per match:

| Volume | Monthly Cost | Annual Cost |
|--------|-------------|-------------|
| 1,000 matches/month | $270.00 | $3,240.00 |
| 3,000 matches/month | $810.00 | $9,720.00 |

The two-phase approach saves 90% on LLM costs.

### Latency Budget

| Phase | Target | Actual |
|-------|--------|--------|
| Input guardrails | < 5ms | ~1ms |
| Phase 1: JD parse (LLM) | < 3s | ~1.5s |
| Phase 2: Deterministic scoring | < 10ms | < 1ms |
| Phase 3: Batch assessment (LLM) | < 5s | ~3s |
| Output guardrails + merge | < 10ms | ~2ms |
| DB persistence | < 500ms | ~200ms |
| **Total** | **< 10s** | **~5s** |

LLM calls dominate. Everything else is negligible.

## High-Level Design

```
Client (Browser)
    |
    v
Next.js Frontend (Vercel)
    |  POST /api/v1/match
    v
FastAPI Backend (Railway)
    |
    +-- Input Guardrails
    |       Sanitize JD text, detect injection, redact PII
    |
    +-- Phase 1: JD Parser
    |       1 Claude API call: free text -> ParsedRequirements
    |
    +-- Phase 2: Deterministic Scorer
    |       Pure Python, 6 dimensions, weighted composite, dealbreakers
    |       Filter candidates below 0.25 threshold
    |
    +-- Phase 3: Batch Assessor
    |       1 Claude API call: shortlist -> skills scores + narratives
    |
    +-- Output Guardrails
    |       Validate scores, detect bias, clamp bounds
    |
    +-- Persist Results
    |       Save matches + metrics to Supabase
    |
    v
Response: MatchResponse (ranked candidates with scores, summaries, strengths, gaps)
```

## Detailed Component Design

### Deterministic Scorer

The scorer is the core architectural insight. By handling structured comparisons deterministically, we avoid:

1. **Cost scaling**: LLM calls per candidate make cost proportional to pool size
2. **Hallucination risk**: LLM might say a candidate has a license they don't hold
3. **Latency**: each LLM call adds 1-3 seconds
4. **Non-determinism**: the same candidate might get different scores on repeat calls

The six dimensions in `scorer.py` cover everything that can be evaluated as structured data comparison:

**Specialty** (35% weight) - The highest weight because specialty mismatch is a fundamental disqualifier. A pediatrician cannot fill a cardiology position regardless of other qualifications. The scorer checks exact match, substring containment (e.g., "Interventional Cardiology" contains "Cardiology"), and adjacency (configurable list from the LLM's Phase 1 output).

**Experience** (20%) - Simple numeric comparison with graduated penalties. Meeting the minimum gets 1.0. Being 1-2 years short gets 0.7 (close enough to warrant LLM review). Being 5+ years short gets 0.2.

**Location/Licensure** (15%) - State medical license matching with an adjacency map. Physicians often hold licenses in neighboring states and can obtain new ones. A PA-licensed doctor applying for an NJ position scores 0.5 (adjacent) rather than 0.2 (no overlap). The `ADJACENT_STATES` map covers 21 states.

**Credentials** (15%) - Binary check for board certification against the job requirement. When certification is required and missing, the candidate scores 0.3, which also triggers a dealbreaker penalty.

**Availability** (10%) - Parses free-text availability ("30 days", "Immediately", "90 days") into numeric days and scores against the job's start date requirement.

**Employment** (5%) - Low weight because employment type preferences are negotiable. Checks overlap between candidate preferences (full-time, part-time, locum tenens) and job requirements.

### Dealbreaker Logic

After computing the weighted sum, `_apply_dealbreakers()` applies multiplicative penalties for critical mismatches:

- Wrong specialty (score <= 0.3): multiply by 0.4
- Missing required certification (score <= 0.4): multiply by 0.7
- Severely underqualified (experience score <= 0.3): multiply by 0.75
- No license overlap (location score <= 0.3): multiply by 0.75

These penalties stack. A candidate with wrong specialty AND no certification gets their composite multiplied by 0.4 * 0.7 = 0.28. This pushes clear mismatches below the 0.25 threshold, filtering them from the shortlist before the LLM phase.

### LLM Integration Points

The LLM handles two tasks that structured data comparison cannot:

**JD Parsing** - Job descriptions are free text with implicit requirements. "Board-certified interventional cardiologist with structural heart experience" contains a specialty, a sub-specialty, a certification requirement, and a skills requirement, none of which are tagged or structured. The LLM extracts these into a typed `ParsedRequirements` object.

**Skills Assessment** - Clinical skills matching requires domain knowledge. "Cardiac Catheterization" and "Interventional Cardiology" are related, but a keyword matcher treats them as independent strings. The LLM assesses skills alignment in context and generates recruiter-ready narratives.

### Final Score Composition

```
final_score = (deterministic_composite * 0.70 + llm_skills_score * 0.30) * 100
```

The 70/30 split reflects the design principle: structured data comparison is reliable and should dominate, while the LLM provides a meaningful but minority contribution for skills nuance.

### Guardrails Design

Four layers, each addressing a different failure mode:

| Layer | Failure Mode | Protection |
|-------|-------------|------------|
| Input | Prompt injection, PII exposure | Regex pattern matching, text redaction, length caps |
| Output (JD parse) | LLM returns invalid structure | Type checking, range clamping, default values |
| Output (batch assess) | LLM hallucinates candidate IDs | Whitelist check against shortlist set |
| Post-merge | Score arithmetic error, scoring bias | Bounds clamping, statistical bias detection |

This defense-in-depth approach means any single layer can fail without compromising the system. If the input guardrails miss an injection, the LLM might return garbage, but the output guardrails clamp it to valid ranges.

## Why Not RAG?

RAG (Retrieval-Augmented Generation) with vector embeddings is a common approach for matching systems. Here is why it is not used here:

**Structured vs unstructured data.** Candidate profiles are structured: specialty is a string, years_experience is an integer, licenses is an array, board_certified is a boolean. Embedding these fields into vectors and doing cosine similarity adds indirection without value. Direct comparison (is specialty == required_specialty?) is faster, cheaper, and deterministic.

**Scale threshold.** RAG adds value when you have:
- 10,000+ candidates with unstructured notes, research papers, or free-text bios
- Semantic similarity queries ("find someone who does work similar to X")
- Fuzzy skill matching across a large taxonomy

At 30-500 candidates with structured profiles, RAG adds infrastructure complexity (vector database, embedding pipeline, index maintenance) without proportional benefit.

**When to add it.** If the candidate pool grows past 10,000 with unstructured data (clinical notes, patient volumes, peer reviews), add pgvector to Supabase and build an embedding pipeline. The two-phase architecture accommodates this: Phase 2 could use vector similarity as a pre-filter before deterministic scoring.

## Why Not LangChain?

LangChain is the standard framework for LLM applications. Here is why this project uses the Anthropic SDK directly:

**Abstraction overhead.** This application makes exactly 2 LLM calls per request. Both calls follow the same pattern: send a system prompt and a user prompt, parse JSON from the response. LangChain's chain/agent abstractions add value for complex multi-step reasoning, tool use, and retrieval pipelines. For two structured prompts, the abstraction layer adds complexity without reducing code.

**Dependency weight.** The Anthropic SDK is one dependency. LangChain pulls in ~15 transitive dependencies. Each dependency is a security surface, a version conflict risk, and a potential breaking change on upgrade.

**Debugging.** When an LLM call fails, the debugging path is: check the prompt, check the response, check the API status. With LangChain, the path includes: check the chain configuration, check the output parser, check the callback handler, check the memory, then check the underlying API call. For a two-prompt application, this indirection slows down incident response.

**Full control.** Direct SDK usage gives full control over retry logic, cost tracking, response parsing, and error handling. The `ClaudeService` class in `claude.py` is 179 lines covering all of these concerns. A LangChain equivalent would distribute this logic across chain callbacks, output parsers, and retry wrappers.

## Cost Optimization Strategy

### The Two-Phase Insight

The fundamental cost optimization is recognizing that most of the matching decision can be made without an LLM. Of the six scoring dimensions, five (specialty, experience, location, credentials, availability) are structured data comparisons. Only skills assessment benefits from LLM intelligence.

### Cost Breakdown by Phase

| Phase | LLM Calls | Tokens (typical) | Cost |
|-------|-----------|-------------------|------|
| Phase 1: JD parse | 1 | ~1,000 | ~$0.0018 |
| Phase 2: Deterministic | 0 | 0 | $0.00 |
| Phase 3: Batch assess | 1 | ~2,800 | ~$0.0012 |
| **Total** | **2** | **~3,800** | **~$0.003** |

### How the Architecture Prevents Cost Scaling

In a naive implementation, matching N candidates requires N LLM calls. Cost grows linearly with candidate pool size.

In this architecture:
- Phase 1 is always 1 call (parse the JD once)
- Phase 2 scores all N candidates with zero LLM calls
- Phase 3 assesses only the top 8 in a single batch call

Cost is fixed at 2 calls regardless of N. Going from 30 to 300 candidates adds <1ms to Phase 2 and zero additional API cost.

### Dealbreaker Filtering

The `DETERMINISTIC_THRESHOLD = 0.25` filter and dealbreaker penalties ensure that obviously unqualified candidates never reach Phase 3. Without this, the batch assessment prompt would include candidates with wrong specialties, inflating token usage without value.

### Cost Guardrails

`check_request_cost()` caps single-request spend at $0.50 and daily spend at $25.00. These prevent runaway costs from malformed prompts that produce excessive output tokens.

## Scaling Considerations

### Current Architecture Limits

The current design handles 30-500 candidates per request with <1ms scoring time. Here is what changes at higher scales:

### 1,000 Candidates

**Phase 2 impact**: Scoring 1,000 candidates in pure Python takes ~10ms. No architecture change needed.

**Phase 1 impact**: None. JD parsing is independent of candidate count.

**Phase 3 impact**: Still limited to top 8 candidates. No change.

**Database impact**: Fetching 1,000 candidate rows from Supabase adds ~200ms. Add pagination or pre-filtering by specialty at the database level.

**Change required**: Increase `MAX_CANDIDATES_PER_REQUEST` from 50. Add database-level specialty filtering (already implemented via `get_by_specialty()`).

### 10,000 Candidates

**Phase 2 impact**: Scoring 10,000 candidates takes ~100ms. Still fast, but consider caching `ParsedRequirements` for identical or similar JDs.

**Database impact**: Fetching 10,000 rows is slow. Move to cursor-based pagination. Pre-filter by specialty and required license states in the database query.

**Change required**: 
- Add database-level filtering: `WHERE specialty ILIKE '%cardiology%' AND 'MA' = ANY(licenses)`
- Cache parsed requirements for repeat JDs
- Consider background workers for batch matching

### 100,000 Candidates

**Phase 2 impact**: Scoring 100,000 candidates in Python takes ~1 second. If latency matters, move to numpy vectorized operations or Rust.

**Database impact**: Full table scans are not viable. Add composite indexes on (specialty, board_certified, years_experience). Consider materialized views for common specialty filters.

**Architectural change**: 
- Introduce a pre-filter layer between the database and the scorer. Use database queries to reduce the candidate pool to ~1,000 before scoring.
- Consider adding pgvector for hybrid search if candidates have unstructured data.
- Move scoring to a worker pool for batch requests.

### 1,000,000+ Candidates

At this scale, the architecture changes fundamentally:
- Replace PostgREST with a dedicated search index (Elasticsearch or Meilisearch) for candidate retrieval
- Add pgvector embeddings for semantic pre-filtering
- Move Phase 2 to a compiled language (Rust or Go)
- Introduce caching at the JD-parse level (identical JDs should hit a cache)
- Consider pre-computing candidate profiles as feature vectors for fast similarity search

The two-phase architecture still holds at this scale. The insight that LLM calls should not scale with candidate count becomes more valuable as N grows.

## Trade-offs and Limitations

### Accepted Trade-offs

| Trade-off | Chosen | Alternative | Why |
|-----------|--------|-------------|-----|
| Deterministic scoring accuracy | Slightly lower accuracy on edge cases | LLM for every dimension | 90% cost reduction, deterministic behavior, <1ms latency |
| Single-model | Claude Sonnet for both phases | Haiku for Phase 1, Sonnet for Phase 3 | Simpler config, small cost difference (~$0.001/match) |
| Batch assessment | 8 candidates in one prompt | Individual assessment per candidate | 1 API call vs 8, minimal quality difference at this shortlist size |
| PostgREST data access | Direct HTTP calls to Supabase REST API | Supabase Python SDK or SQLAlchemy ORM | Thread-safe in uvicorn's thread pool, avoids SDK's httpx client issues |
| No caching | Repeat JDs parsed again | Redis/Memcached for ParsedRequirements | Complexity not justified at current request volume |

### Known Limitations

1. **Specialty taxonomy** - The scorer uses string matching with an adjacency list from the LLM. There is no formal medical specialty taxonomy. "Sports Medicine" and "Orthopedic Surgery" require the LLM to identify them as adjacent in Phase 1.

2. **Skills matching depth** - Phase 2 does not evaluate clinical skills. A candidate could pass all deterministic checks with a perfect composite but lack critical skills. Phase 3's LLM assessment catches this, but only for the top 8 candidates.

3. **State adjacency coverage** - The `ADJACENT_STATES` map covers 21 states. Candidates in uncovered states (e.g., HI, AK) default to the 0.2 penalty if their license does not match.

4. **Availability parsing** - Relies on regex extraction of "N days" from free text. Formats like "available Q3 2026" or "after completing fellowship" are not parsed correctly and default to 0.5 score.

5. **Single-tenant** - No multi-user authentication. RLS policies exist but are not enabled. The application is designed for a single recruiting team.

6. **No candidate profile updates** - Candidate data is static after seeding. In production, candidates change availability, gain new licenses, and complete certifications. This requires an ingestion pipeline that is out of scope.

## Future Improvements

### Near-term (Would Implement Next)

1. **JD parse caching** - Hash the JD text and cache `ParsedRequirements` in Supabase. Repeat JDs skip Phase 1 entirely, cutting latency by 1.5s and cost by 60%.

2. **Model routing** - Use Haiku for straightforward JDs (single specialty, clear requirements) and Sonnet for complex JDs (multiple specialties, ambiguous requirements). Route based on JD complexity scoring.

3. **Eval expansion** - Add 20+ golden set cases covering edge cases: adjacent specialties, locum tenens matching, multi-state license requirements, overqualified candidates.

4. **Feedback-driven weight tuning** - Use recruiter feedback data to adjust dimension weights. If recruiters consistently mark high-availability candidates as "good match" but the current weight is only 10%, increase it.

### Medium-term

5. **Skills taxonomy** - Build a structured medical skills taxonomy mapping related skills (e.g., "Cardiac Catheterization" -> "Interventional Cardiology"). Move skills matching from Phase 3 (LLM) to Phase 2 (deterministic) for candidates with structured skills data.

6. **Candidate ingestion API** - Accept candidate profile updates via API. Track license expirations, availability changes, and new certifications.

7. **Multi-tenant support** - Enable RLS, add Supabase Auth, scope candidate pools per organization.

8. **Webhook notifications** - Alert recruiters when a new candidate matches an open position above a configurable threshold.

### Long-term

9. **Embedding search** - Add pgvector to Supabase for semantic similarity on unstructured candidate notes, research publications, and clinical experience descriptions.

10. **Prediction model** - Train a lightweight classifier on feedback data to predict match quality without LLM calls. Replace Phase 3 with a local model for the majority of matches, using LLM only for borderline cases.
