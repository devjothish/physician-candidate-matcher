# Deployment Guide

Complete setup instructions for local development, staging, and production deployment.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 20+ | Frontend runtime |
| npm | 10+ | Frontend package manager |
| Git | 2.40+ | Version control |
| Supabase account | Free tier | PostgreSQL database |
| Anthropic API key | - | Claude API access |
| Railway account | Optional | Backend hosting |
| Vercel account | Optional | Frontend hosting |

## Local Development Setup

### 1. Clone and Configure

```bash
git clone https://github.com/jothiswaran-arumugam/physician-candidate-matcher
cd physician-candidate-matcher
```

Create environment files:

```bash
# Root .env (used by docker-compose and backend)
cp .env.example .env
```

Edit `.env` with your credentials:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
ENVIRONMENT=development
LOG_LEVEL=INFO
DEFAULT_MODEL=claude-sonnet-4-20250514
FAST_MODEL=claude-haiku-4-5-20251001
RATE_LIMIT_PER_MINUTE=20
MAX_CANDIDATES_PER_REQUEST=50
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Verify installation:

```bash
python -c "import app; print('Backend dependencies OK')"
```

### 3. Frontend Setup

```bash
cd frontend
npm ci
```

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Database Setup (Supabase)

See the Supabase section below.

### 5. Start Development Servers

```bash
# Terminal 1: Backend (from project root)
make dev-backend
# Runs: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend (from project root)
make dev-frontend
# Runs: next dev on port 3000
```

Verify:
- Backend API docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Health check: http://localhost:8000/api/v1/health

### Alternative: Docker Compose

```bash
docker-compose up --build
```

This starts both services with hot-reload. Backend mounts `./backend/app` as a volume for live code changes.

## Supabase Setup

### 1. Create a Project

1. Go to https://supabase.com and create a new project
2. Choose a region close to your target users
3. Save the project URL and anon key from Project Settings > API

### 2. Run the Schema

1. Open the Supabase Dashboard for your project
2. Go to SQL Editor
3. Paste the contents of `docs/schema.sql`
4. Click "Run"

This creates:
- 5 tables: `candidates`, `matches`, `feedback`, `llm_calls`, `api_requests`
- 2 views: `analytics_summary`, `daily_costs`
- Indexes on frequently queried columns
- An `update_updated_at` trigger on candidates

### 3. Seed Candidate Data

```bash
cd backend
source venv/bin/activate
python scripts/seed_candidates.py
```

This inserts 30 physician candidates across 15 specialties. The script is idempotent; re-running it skips existing records.

Verify seeding:

```bash
curl -H "apikey: YOUR_KEY" \
  -H "Authorization: Bearer YOUR_KEY" \
  "https://YOUR_PROJECT.supabase.co/rest/v1/candidates?select=id,name,specialty&limit=5"
```

### 4. Verify Connectivity

```bash
# Start the backend, then:
curl http://localhost:8000/api/v1/health/deep
```

Expected response:

```json
{
  "status": "healthy",
  "checks": {
    "supabase": {"status": "healthy", "latency_ms": 120.3},
    "claude_api": {"status": "healthy", "latency_ms": 890.1, "model": "claude-haiku-4-5-20251001"}
  }
}
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic API key for Claude access |
| `SUPABASE_URL` | Yes | - | Supabase project URL (https://xxx.supabase.co) |
| `SUPABASE_KEY` | Yes | - | Supabase anon key (safe for client-side, RLS applies) |
| `ENVIRONMENT` | No | development | "development" or "production". Controls CORS, log format. |
| `LOG_LEVEL` | No | INFO | Python log level: DEBUG, INFO, WARNING, ERROR |
| `DEFAULT_MODEL` | No | claude-sonnet-4-20250514 | Model for JD parsing and batch assessment |
| `FAST_MODEL` | No | claude-haiku-4-5-20251001 | Model for health check pings |
| `RATE_LIMIT_PER_MINUTE` | No | 20 | Max requests per minute per IP on /match |
| `MAX_CANDIDATES_PER_REQUEST` | No | 50 | Max candidates fetched from DB per request |
| `NEXT_PUBLIC_API_URL` | Frontend | http://localhost:8000 | Backend URL for the frontend to call |

## Backend Deployment to Railway

### 1. Create Railway Project

1. Go to https://railway.app and create a new project
2. Connect your GitHub repository
3. Select the `backend/` directory as the root

### 2. Configure Build

Railway will detect the Dockerfile at `backend/Dockerfile`. The multi-stage build:
- Stage 1 (builder): installs Python dependencies with gcc
- Stage 2 (production): copies installed packages, runs as non-root user

The `railway.toml` at `backend/railway.toml` configures:
- Builder: Dockerfile
- Health check path: `/api/v1/health`
- Health check timeout: 30s
- Replicas: 1
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
- Restart policy: on failure, max 5 retries

### 3. Set Environment Variables

In Railway dashboard, add these variables to the service:

```
ANTHROPIC_API_KEY=sk-ant-your-production-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
ENVIRONMENT=production
LOG_LEVEL=INFO
DEFAULT_MODEL=claude-sonnet-4-20250514
FAST_MODEL=claude-haiku-4-5-20251001
RATE_LIMIT_PER_MINUTE=20
```

### 4. Deploy

```bash
cd backend
railway up
```

Or push to main branch to trigger automatic deployment via GitHub Actions.

### 5. Verify

```bash
curl https://your-service.railway.app/api/v1/health
curl https://your-service.railway.app/api/v1/health/deep
```

## Frontend Deployment to Vercel

### 1. Import Project

1. Go to https://vercel.com and import your GitHub repository
2. Set the root directory to `frontend/`
3. Framework preset: Next.js (auto-detected)

### 2. Environment Variables

Add in Vercel project settings:

```
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

### 3. Deploy

```bash
cd frontend
vercel --prod
```

Or push to main branch for automatic deployment.

### 4. Update CORS

After deploying the frontend, update the backend's CORS configuration. In `backend/app/main.py`, the production allowed origins list includes:

```python
allowed_origins = [
    "https://physician-matcher.vercel.app",
]
```

Replace with your actual Vercel domain.

## CI/CD Pipeline

### GitHub Actions Workflows

**`.github/workflows/ci.yml`** - Runs on every PR and push to main:

Backend job:
1. Setup Python 3.11 with pip cache
2. Install dependencies
3. Lint with ruff
4. Format check with black (line length 120)
5. Type check with mypy
6. Run unit tests with coverage

Frontend job:
1. Setup Node.js 22 with npm cache
2. Install dependencies (`npm ci`)
3. Lint with ESLint
4. Build (with `NEXT_PUBLIC_API_URL=http://localhost:8000`)

**`.github/workflows/deploy.yml`** - Runs on push to main:

- Deploys backend to Railway (if `RAILWAY_TOKEN` secret exists)
- Deploys frontend to Vercel (if `VERCEL_TOKEN` secret exists)

### Required Secrets

| Secret | Where | Purpose |
|--------|-------|---------|
| `RAILWAY_TOKEN` | GitHub repo settings | Railway deploy authentication |
| `VERCEL_TOKEN` | GitHub repo settings | Vercel deploy authentication |
| `VERCEL_ORG_ID` | GitHub repo settings | Vercel organization identifier |
| `VERCEL_PROJECT_ID` | GitHub repo settings | Vercel project identifier |

## Environment-Specific Configuration

### Development

```
ENVIRONMENT=development
```

- CORS allows localhost origins (3000, 5173, 127.0.0.1:3000)
- Logging uses console renderer (human-readable)
- Rate limiting still enforced (test against production behavior)

### Production

```
ENVIRONMENT=production
```

- CORS restricted to production frontend domain only
- Logging uses JSON renderer (machine-parseable)
- Docker runs as non-root user
- Health check configured for Railway auto-restart

## Monitoring and Health Checks

### Endpoints

| Endpoint | Purpose | Downstream Calls |
|----------|---------|-----------------|
| `GET /api/v1/health` | Load balancer ping. Returns 200 immediately. | None |
| `GET /api/v1/health/deep` | Operational monitoring. Tests all dependencies. | Supabase, Claude API |

### What to Monitor

1. **Health check latency** - If `/health/deep` reports Supabase latency > 500ms or Claude API latency > 5000ms, investigate.
2. **LLM cost** - `GET /api/v1/analytics/costs` returns daily spend. Set alerts if daily cost exceeds $10.
3. **Error rate** - Check `llm_calls` table for `success = false` entries. Success rate should be > 95%.
4. **Match quality** - `GET /api/v1/analytics` shows good_match vs bad_match ratio from recruiter feedback.
5. **Guardrail triggers** - Search logs for `alert_guardrails_triggered` events.

### Log Queries

In production, logs are JSON-formatted. Key events to search:

```
# High latency requests
event: "alert_high_latency"

# High cost requests
event: "alert_high_cost"

# Guardrail activations
event: "alert_guardrails_triggered"

# Failed LLM calls
event: "claude_call_failed"

# Failed match persistence
event: "match_persistence_failed"
```

## Troubleshooting

### Backend won't start

**"Settings validation error"** - Missing required env vars. Check that `ANTHROPIC_API_KEY`, `SUPABASE_URL`, and `SUPABASE_KEY` are set.

**"Module not found"** - Virtual environment not activated. Run `source venv/bin/activate`.

### Supabase connection fails

**"401 Unauthorized"** - Wrong `SUPABASE_KEY`. Use the anon key from Project Settings > API, not the service role key.

**"Could not find table"** - Schema not created. Run `docs/schema.sql` in the SQL Editor.

**"Timeout"** - Supabase project may be paused (free tier pauses after 1 week of inactivity). Open the dashboard to wake it up.

### Claude API errors

**"401 authentication_error"** - Invalid `ANTHROPIC_API_KEY`. Regenerate from console.anthropic.com.

**"429 rate_limit_error"** - Too many requests. The tenacity retry handles this automatically with exponential backoff. If persistent, check your Anthropic plan limits.

**"502 ClaudeAPIError"** - Transient outage. Retried automatically 3 times. Check status.anthropic.com if persistent.

### Frontend can't reach backend

**CORS error in browser console** - Backend not running, or `NEXT_PUBLIC_API_URL` points to wrong address. Verify with `curl http://localhost:8000/api/v1/health`.

**"Failed to fetch"** - Backend server is down or unreachable. Check if uvicorn is running.

### Seeding fails

**"Duplicate key"** - Candidates already exist. The seed script is idempotent; this is expected on re-runs.

**"Connection refused"** - Wrong `SUPABASE_URL` or project is paused.

### Tests fail

**Unit tests** - Should run without any external dependencies. If they fail, check that `app/` is importable from the `backend/` directory.

**Eval tests** - Require a seeded database and valid API key. Run `make seed` first, then `make test-eval`.

### Docker issues

**"Permission denied"** - If running on Linux, ensure the app user has read access to the application files. The Dockerfile creates `appuser` and sets ownership.

**Health check failing** - Container may need more startup time. The Docker HEALTHCHECK has a 5s start period. If the app takes longer, increase `--start-period`.
