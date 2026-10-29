COMPOSE := docker compose
UV := uv run

.PHONY: up down logs lint typecheck test cov migrate seed

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api

lint:
	$(UV) ruff check .
	$(UV) ruff format --check .

typecheck:
	$(UV) mypy app tests

test:
	$(UV) pytest

cov:
	$(UV) pytest --cov=app/services --cov=app/security --cov-report=term-missing --cov-fail-under=90

migrate:
	$(UV) alembic upgrade head

seed:
	$(UV) python scripts/seed.py
