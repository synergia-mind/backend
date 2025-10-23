.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available commands and their descriptions
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install project dependencies
	uv sync --no-dev

install-dev: ## Install development dependencies
	uv sync --dev

dev: ## Run the development server
	uv run fastapi dev app/main.py --no-reload --port 8000 --host 0.0.0.0

test: ## Run tests
	uv run coverage run --source=app --omit='app/tests/*' -m pytest
	uv run coverage report --show-missing

format: ## Format code using ruff
	ruff check app scripts --fix
	ruff format app scripts

# Database Migration Commands
migrate-create: ## Create a new migration (usage: make migrate-create MSG="migration message")
	uv run alembic revision --autogenerate -m "$(MSG)"

migrate-upgrade: ## Apply all pending migrations
	uv run alembic upgrade head

migrate-downgrade: ## Rollback one migration
	uv run alembic downgrade -1

migrate-current: ## Show current migration
	uv run alembic current

migrate-history: ## Show migration history
	uv run alembic history

migrate-reset: ## Reset to base migration (WARNING: destructive)
	uv run alembic downgrade base

