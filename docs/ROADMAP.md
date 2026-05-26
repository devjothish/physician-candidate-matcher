# Production Roadmap

What it takes to move from proof-of-architecture to production deployment at scale. Organized by priority, not timeline.

## Phase 1: Data Integration (Week 1-2)

### Salesforce CRM Connector
The current system uses a seeded Postgres table. A production deployment would pull candidates from the recruiting team's Salesforce instance.

| Component | Implementation |
|-----------|---------------|
| Auth | OAuth 2.0 with Salesforce Connected App |
| Sync | Bulk API 2.0 for initial load, Streaming API for incremental updates |
| Mapping | Salesforce Contact/Candidate fields mapped to our Candidate model |
| Refresh | Delta sync every 15 minutes, full sync nightly |

### Candidate Data Pipeline
- Parse unstructured resume text into structured fields (specialty, skills, licenses)
- Normalize specialty names through NPI taxonomy on ingestion
- Validate state license data against NPPES NPI Registry API
- Deduplicate candidates across data sources (Salesforce + job boards + referrals)

## Phase 2: Skills Ontology (Week 2-3)

### Replace Token Matching with SNOMED CT
The current skills scoring uses token-level keyword overlap. Production needs a medical skills ontology.

| Current | Production |
|---------|-----------|
| "Cardiac Catheterization" matches "catheterization" token | "Cardiac Catheterization" is-a "Interventional Procedure" is-a "Cardiology Skill" |
| "TAVR" does not match "Transcatheter Aortic Valve Replacement" | "TAVR" maps to SNOMED concept 427127001 with synonyms and parent concepts |
| No hierarchy awareness | Hierarchical distance scoring between concepts |

Implementation:
- Download SNOMED CT International Edition (free for US use via UMLS)
- Build a lookup table of medical procedure concepts with parent-child relationships
- Score skills by computing shortest path in the concept graph
- Fall back to token matching for skills not in SNOMED

### O*NET Integration for Non-Clinical Skills
Clinical skills map to SNOMED. Non-clinical skills (teaching, research, leadership, quality improvement) map to O*NET skill taxonomy codes.

## Phase 3: HIPAA Compliance (Week 3-4)

### What HIPAA Requires for This System

This system processes physician professional data (credentials, work history, skills), not patient data. Under HIPAA, physician professional data is not PHI. However, if the system ever processes:
- Physician personal contact information (home address, personal phone, SSN)
- Patient panel data or clinical outcomes tied to physicians
- Any data from EHR systems

Then HIPAA applies. The production architecture should assume HIPAA applies from day one.

### Technical Controls

| Control | Implementation |
|---------|---------------|
| Encryption at rest | Supabase encrypts at rest by default (AES-256). Verify with BAA. |
| Encryption in transit | TLS 1.2+ on all endpoints (Railway and Vercel enforce this). |
| Access logging | Every API request logged with user identity, timestamp, action, and resource. Current request logging middleware covers method/path/status. Add user identity from auth token. |
| Audit trail | Immutable append-only audit log table. No DELETE operations on audit records. Current match and LLM call tables are append-only already. |
| Access controls | Role-based access: Recruiter (read matches, submit feedback), Admin (read analytics, manage candidates), System (write matches, log metrics). Currently no auth. |
| Data retention | Define retention policy per table. Matches and feedback retained for 7 years (standard for employment records). LLM call logs retained for 1 year. |
| BAA | Execute Business Associate Agreement with Supabase and Anthropic before processing any data that could be considered PHI. |
| Minimum necessary | LLM prompts already exclude demographics. Extend to exclude any field not needed for matching. |

### Authentication and Authorization
- Add Supabase Auth or Auth0 for user authentication
- JWT-based API authentication with role claims
- Row Level Security (RLS) on Supabase tables scoped to organization
- API rate limiting per authenticated user (currently per IP)

## Phase 4: Multi-Tenancy (Week 4-5)

### Architecture

Each recruiting client (hospital system, medical group) is a tenant. Tenants share the application but have isolated data.

```
Request -> Auth Middleware -> Extract tenant_id from JWT
                                    |
                          +---------+---------+
                          |                   |
                   Tenant A data       Tenant B data
                   (RLS enforced)      (RLS enforced)
```

| Component | Single-Tenant (current) | Multi-Tenant |
|-----------|------------------------|--------------|
| Database | One Supabase project | One project, RLS per tenant_id column |
| Candidates | Shared pool | Per-tenant candidate pools |
| Matches | No isolation | tenant_id on every row, RLS enforced |
| Scoring weights | Hardcoded | Per-tenant configuration table |
| Dealbreakers | Hardcoded | Per-tenant rules engine |
| API keys | Single Anthropic key | Per-tenant key or shared with cost allocation |

### Data Model Changes
Add `tenant_id UUID NOT NULL` to: candidates, matches, feedback, llm_calls.
Enable RLS on all tables. Policy: `USING (tenant_id = auth.jwt() -> 'tenant_id')`.

### Configurable Scoring
Move scoring weights and dealbreaker thresholds to a `tenant_config` table:

```sql
CREATE TABLE tenant_config (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
    scoring_weights JSONB NOT NULL DEFAULT '{
        "specialty": 0.30,
        "experience": 0.18,
        "location": 0.15,
        "credentials": 0.12,
        "skills_keyword": 0.12,
        "availability": 0.08,
        "employment": 0.05
    }',
    dealbreakers JSONB NOT NULL DEFAULT '{
        "specialty_threshold": 0.3,
        "credentials_threshold": 0.4,
        "experience_threshold": 0.3,
        "location_threshold": 0.3
    }',
    shortlist_size INTEGER NOT NULL DEFAULT 8,
    deterministic_threshold REAL NOT NULL DEFAULT 0.25
);
```

## Phase 5: Learning and Optimization (Week 5-8)

### Feedback-Driven Weight Tuning
The system currently stores recruiter feedback (good_match, bad_match, hired, interviewed) but doesn't use it to improve scoring. Production would:

1. Collect 100+ feedback signals per tenant
2. Run weekly batch analysis comparing scores vs feedback outcomes
3. Adjust scoring weights to maximize correlation between high scores and "good_match" / "hired" feedback
4. A/B test weight changes on 10% of traffic before full rollout

### Scoring Accuracy Metrics
Track per-tenant:
- Precision@5: what percentage of top-5 candidates get "good_match" feedback
- Recall: what percentage of "hired" candidates were in the top-10 results
- NDCG: normalized discounted cumulative gain of ranking quality

### Prompt Optimization
- Track which JD phrasings produce the best LLM assessments
- A/B test prompt variations and measure downstream feedback quality
- Cache JD parse results for similar job descriptions (embedding similarity > 0.95)

## Phase 6: Scale (Week 8+)

### 10K+ Candidates
At 10K candidates, fetching all for deterministic scoring takes ~50ms (still fine). At 100K+:
- Add pgvector embeddings for initial candidate retrieval (top 500 by embedding similarity)
- Then run deterministic scorer on the retrieved set
- This is where RAG becomes relevant, not before

### Caching
- Cache JD parse results (same JD text produces same structured requirements)
- Cache deterministic scores per candidate-requirement pair (invalidate on candidate update)
- Estimated cache hit rate: 60-70% for repeat searches

### Cost Projection

| Scale | Matches/day | LLM calls/day | Daily cost | Monthly cost |
|-------|-------------|---------------|------------|-------------|
| Pilot (1 recruiter) | 10 | 20 | $0.03 | $0.90 |
| Team (5 recruiters) | 50 | 100 | $0.15 | $4.50 |
| Department (20 recruiters) | 200 | 400 | $0.60 | $18.00 |
| Enterprise (100 recruiters) | 1000 | 2000 | $3.00 | $90.00 |

Cost scales with matches, not candidates. Adding 10x more candidates to the pool costs $0.00 more per match.
