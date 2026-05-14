.PHONY: setup dev test migrate lint docker-up docker-down clean

# === Development Setup ===
setup:
	cd backend && pip install -e ".[dev]"
	cd frontend/ops-dashboard && npm install
	cd frontend/configurator && npm install

dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-worker:
	cd backend && celery -A app.celery_app worker --loglevel=info --concurrency=4 -Q default,high_priority,low_priority

dev-scheduler:
	cd backend && python -m app.cron.scheduler

dev-frontend:
	cd frontend/ops-dashboard && npm run dev

# === Testing ===
test:
	cd backend && pytest -q

test-cov:
	cd backend && pytest --cov=app --cov-report=html

# === Database ===
migrate:
	cd backend && alembic upgrade head

migrate-new:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# === Code Quality ===
lint:
	cd backend && ruff check . && ruff format --check .

format:
	cd backend && ruff format .

# === Docker ===
docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# === Cleanup ===
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
