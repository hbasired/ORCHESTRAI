# AI Embodied Agent — common dev commands.
#
# Stage 1 (2026-05-11) — introduced as a single entry point so operator
# muscle memory works the same on Windows + macOS + Linux. Wherever you
# see `make X`, the underlying command also lives in plain shell so CI
# does not depend on `make` being installed.

SHELL := bash

# ---------------------------------------------------------------------------
# Help (default target)
# ---------------------------------------------------------------------------
.PHONY: help
help:
	@echo "Targets:"
	@echo "  up                — docker compose up -d (full stack, runs Alembic init)"
	@echo "  down              — docker compose down"
	@echo "  logs              — tail backend + simulation logs"
	@echo "  migrate           — alembic upgrade head (host shell, against compose Postgres)"
	@echo "  test-backend      — pytest -q in backend/"
	@echo "  test-frontend     — jest smoke tests in frontend-nextjs/"
	@echo "  test-e2e          — playwright smoke tests"
	@echo "  audit             — scripts/audit.sh (must not regress vs .audit-baseline)"
	@echo "  audit-baseline    — overwrite .audit-baseline (use at stage close)"
	@echo "  lint              — backend ruff + frontend next lint"
	@echo "  fmt               — backend ruff format + frontend prettier"
	@echo "  clean             — remove __pycache__, .pytest_cache, .next, node_modules build artefacts"

# ---------------------------------------------------------------------------
# Stack lifecycle
# ---------------------------------------------------------------------------
.PHONY: up
up:
	@test -f .env.local || (echo "ERROR: copy .env.example to .env.local and fill values first" && exit 1)
	docker compose -f docker/docker-compose.yml --env-file .env.local up -d

.PHONY: down
down:
	docker compose -f docker/docker-compose.yml down

.PHONY: logs
logs:
	docker compose -f docker/docker-compose.yml logs -f backend simulation

# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------
.PHONY: migrate
migrate:
	cd backend && alembic upgrade head

.PHONY: migrate-new
migrate-new:
	@test -n "$(name)" || (echo "Usage: make migrate-new name=<short_slug>" && exit 1)
	cd backend && alembic revision -m "$(name)"

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
.PHONY: test-backend
test-backend:
	cd backend && pytest -q

.PHONY: test-frontend
test-frontend:
	cd frontend-nextjs && npm test

.PHONY: test-e2e
test-e2e:
	cd frontend-nextjs && npx playwright test

.PHONY: test
test: test-backend test-frontend

# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
.PHONY: audit
audit:
	bash scripts/audit.sh

.PHONY: audit-baseline
audit-baseline:
	bash scripts/audit.sh --baseline

# ---------------------------------------------------------------------------
# Lint / format
# ---------------------------------------------------------------------------
.PHONY: lint
lint:
	cd backend && python -m ruff check . || true
	cd frontend-nextjs && npm run lint --if-present

.PHONY: fmt
fmt:
	cd backend && python -m ruff format . || true
	cd frontend-nextjs && npx prettier --write "src/**/*.{ts,tsx,css}" || true

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------
.PHONY: clean
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf backend/.pytest_cache
	rm -rf frontend-nextjs/.next frontend-nextjs/out
