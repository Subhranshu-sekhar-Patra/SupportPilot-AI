# ============================================================
# SupportPilot AI — Makefile
# Developer shortcuts for common tasks
# ============================================================

.PHONY: help setup dev prod down logs clean test migrate seed

COMPOSE_BASE = docker compose -f docker-compose.yml
COMPOSE_DEV  = $(COMPOSE_BASE) -f docker-compose.dev.yml

## help: Show this help message
help:
	@echo ""
	@echo "  SupportPilot AI — Available Commands"
	@echo "  ====================================="
	@grep -E '^## ' Makefile | sed 's/## /  /'
	@echo ""

## setup: First-time setup (copy .env, build images)
setup:
	@if not exist .env (copy .env.example .env && echo ".env created from .env.example — please fill in your values.")
	$(COMPOSE_DEV) build

## dev: Start all services in development mode
dev:
	$(COMPOSE_DEV) up

## dev-build: Rebuild and start in development mode
dev-build:
	$(COMPOSE_DEV) up --build

## prod: Start all services in production mode
prod:
	$(COMPOSE_BASE) up -d

## down: Stop all services
down:
	$(COMPOSE_DEV) down

## logs: Tail logs for all services
logs:
	$(COMPOSE_DEV) logs -f

## logs-backend: Tail backend logs only
logs-backend:
	$(COMPOSE_DEV) logs -f backend

## logs-frontend: Tail frontend logs only
logs-frontend:
	$(COMPOSE_DEV) logs -f frontend

## migrate: Run Alembic database migrations
migrate:
	$(COMPOSE_DEV) exec backend alembic upgrade head

## migrate-create: Create a new migration (use: make migrate-create MSG="add users table")
migrate-create:
	$(COMPOSE_DEV) exec backend alembic revision --autogenerate -m "$(MSG)"

## seed: Seed the database with sample data
seed:
	$(COMPOSE_DEV) exec backend python -m app.db.seed

## test-backend: Run backend tests
test-backend:
	$(COMPOSE_DEV) exec backend pytest -v --tb=short

## test-frontend: Run frontend tests
test-frontend:
	$(COMPOSE_DEV) exec frontend pnpm test

## clean: Remove containers, volumes, and images
clean:
	$(COMPOSE_DEV) down -v --rmi local

## shell-backend: Open a shell in the backend container
shell-backend:
	$(COMPOSE_DEV) exec backend bash

## shell-db: Open a psql session
shell-db:
	$(COMPOSE_DEV) exec postgres psql -U supportpilot -d supportpilot
