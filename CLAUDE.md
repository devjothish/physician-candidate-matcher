# Physician Candidate Matcher

## About
Production-grade AI-powered physician candidate matching for healthcare recruiters. Built for M3 USA / Medicus Firm use case.

## Philosophy
- Purpose-built, not generic chatbot
- AI recommends, human decides
- Simple architecture wins
- Right-sized, not over-engineered
- Production-grade, not demo

## Tech Stack
| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 + shadcn/ui + Tailwind |
| Backend | FastAPI + Pydantic v2 |
| Database | Supabase (Postgres) |
| LLM | `anthropic` SDK (direct) |
| Logging | `structlog` |
| Retry | `tenacity` |
| CI/CD | GitHub Actions |
| Frontend Deploy | Vercel |
| Backend Deploy | Railway |

## Not Using (By Design)
- LangChain (over-engineered)
- LangFuse/LangSmith (overkill - built simple observability)
- Streamlit (looks like prototype)
- SQLite (not production-grade)

## Architecture
```
Vercel (Next.js + shadcn) -> Railway (FastAPI) -> Supabase (Postgres)
                                    |
                              Claude API
```

## Commands
```bash
# Backend dev
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# Frontend dev
cd frontend && npm run dev

# Tests
cd backend && pytest tests/ -v
cd backend && pytest tests/evaluation/ -v -s

# Lint
cd backend && ruff check . && black --check . && mypy app/
cd frontend && npm run lint

# Seed DB
cd backend && python scripts/seed_candidates.py
```

## Key Design Decisions
- Model routing: Haiku for simple jobs, Sonnet for complex (~40% cost savings)
- Bias-free scoring: Demographics excluded from LLM scoring payload
- Repository pattern for DB access
- Structured logging with structlog for production observability
- Golden set evaluation for accuracy tracking
- Feedback loop for continuous quality improvement

## File Conventions
- Backend: FastAPI app in `backend/app/`, tests in `backend/tests/`
- Frontend: Next.js app in `frontend/src/`, components in `frontend/src/components/`
- API versioned under `/api/v1/`
- Pydantic models in `backend/app/models/`
- Business logic in `backend/app/services/`
- Prompts in `backend/app/core/prompts.py`
