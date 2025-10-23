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

