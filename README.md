# Physician Candidate Matcher

AI-powered physician candidate matching for healthcare recruiters. Purpose-built for surfacing the right candidates, not a generic chatbot.

## What It Does

Healthcare recruiters paste a job description. The system scores every candidate in the database across six dimensions (specialty, experience, location, credentials, skills, availability), ranks them, and explains why - with full cost and latency transparency on every request.

## Architecture

```
Vercel (Next.js 14 + shadcn/ui) --> Railway (FastAPI) --> Supabase (Postgres)
                                          |
                                    Claude API
                                  (Sonnet / Haiku)
```

### Design Decisions

| Decision | Why |
|----------|-----|
| Direct Anthropic SDK | No LangChain abstraction overhead. One dependency, full control. |
| Supabase over SQLite | Real Postgres. Migrations, RLS, views, production-grade. |
| Next.js over Streamlit | Looks like a product, not a prototype. |
| Model routing | Haiku for simple jobs (~$0.001/match), Sonnet for complex (~$0.009/match). ~40% cost savings. |
| Demographics excluded | Candidate name, age, gender never sent to scoring prompts. Bias-free by design. |
| Repository pattern | Clean separation between business logic and data access. Testable. |
| Structured logging | JSON logs with structlog. Every LLM call tracked: tokens, cost, latency, success/failure. |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Supabase account (free tier works)
- Anthropic API key

### Setup

```bash
git clone https://github.com/yourusername/physician-candidate-matcher
cd physician-candidate-matcher
cp .env.example .env
# Edit .env with your keys
```

### Database

Run `docs/schema.sql` in your Supabase SQL editor, then seed:

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/seed_candidates.py
```

### Development

```bash
# Terminal 1: Backend
make dev-backend

# Terminal 2: Frontend
make dev-frontend
```

Backend runs at `http://localhost:8000` (docs at `/docs`).
Frontend runs at `http://localhost:3000`.

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/match` | POST | Match candidates to a job description |
| `/api/v1/batch` | POST | Batch match (max 5 jobs) |
| `/api/v1/feedback` | POST | Submit recruiter feedback |
| `/api/v1/feedback/{match_id}` | GET | Get feedback for a match |
| `/api/v1/analytics` | GET | Usage stats and quality metrics |
| `/api/v1/analytics/costs` | GET | Cost over time |
| `/api/v1/health` | GET | Health check |

## Scoring

Each candidate is scored on six dimensions (0-1 scale each, weighted into 0-100 overall):

| Category | What It Measures |
|----------|-----------------|
| Specialty | Exact match vs. adjacent vs. unrelated |
| Experience | Years relative to requirement (+-2yr = perfect) |
| Location | Same state, licensed in state, relocation needed |
| Credentials | Board certified, eligible, or not |
| Skills | Percentage of required skills matched |
| Availability | Immediate, 30/60/90+ days |

## Testing

```bash
make test          # Unit tests
make test-eval     # Golden set evaluation (requires API key + seeded DB)
make lint          # Ruff + black + mypy + ESLint
```

## Deployment

- **Backend**: Railway (Dockerfile included, `railway.toml` configured)
- **Frontend**: Vercel (zero-config Next.js deployment)
- **CI/CD**: GitHub Actions on PR and merge to main

## Cost

With model routing enabled:
- Simple job match (10 candidates): ~$0.01
- Complex job match (10 candidates): ~$0.09
- Average with 60/40 simple/complex split: ~$0.04

## License

MIT
