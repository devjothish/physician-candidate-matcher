.PHONY: dev-backend dev-frontend test test-eval lint format seed deploy-backend deploy-frontend

dev-backend:
	cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && source venv/bin/activate && pytest tests/ -v --cov=app --cov-report=term-missing

test-unit:
	cd backend && source venv/bin/activate && pytest tests/unit/ -v

test-eval:
	cd backend && source venv/bin/activate && pytest tests/evaluation/ -v -s

lint:
	cd backend && source venv/bin/activate && ruff check . && black --check . && mypy app/
	cd frontend && npm run lint

format:
	cd backend && source venv/bin/activate && ruff check --fix . && black .
	cd frontend && npm run lint -- --fix

seed:
	cd backend && source venv/bin/activate && python scripts/seed_candidates.py

deploy-backend:
	cd backend && railway up

deploy-frontend:
	cd frontend && vercel --prod
