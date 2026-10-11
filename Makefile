.DEFAULT_GOAL := help
PY ?= uv run

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

install: ## Install deps (uv)
	uv sync --all-extras

up: ## Start infra (postgres, redis, minio, mailpit)
	docker compose up -d postgres redis minio mailpit

up-llm: ## Start local Ollama too
	docker compose --profile llm up -d

down: ## Stop everything
	docker compose down

api: ## Run API with reload
	$(PY) uvicorn qualifai.api.main:app --reload --port 8000

worker: ## Run background worker (prep / evaluation / cleanup)
	$(PY) arq qualifai.workers.worker.WorkerSettings

web: ## Run the web app with hot reload (http://localhost:3000, proxies /v1 to the API)
	cd frontend && npm install && npm run dev

web-build: ## Build the web app into frontend/dist (the API then serves it)
	cd frontend && npm ci && npm run build

migrate: ## Apply DB migrations
	$(PY) alembic upgrade head

migration: ## New migration: make migration m="message"
	$(PY) alembic revision --autogenerate -m "$(m)"

seed: ## Load content/ YAML into the database
	$(PY) python scripts/seed_content.py

lint: ## Ruff + import-linter
	$(PY) ruff check src tests
	$(PY) ruff format --check src tests
	$(PY) lint-imports

typecheck: ## mypy strict
	$(PY) mypy src

test: ## Unit + architecture tests (fast, no infra)
	$(PY) pytest -m "unit or architecture or contract" -q

test-integration: ## Needs Docker
	$(PY) pytest -m integration -q

test-e2e: ## Full flow with fake LLM, needs Docker
	$(PY) pytest -m e2e -q

evals: ## Judgment-quality evals (needs a configured model)
	$(PY) python -m tests.evals.run_evals

load: ## Load test against a running API
	$(PY) locust -f tests/load/locustfile.py

check: lint typecheck test ## Everything CI runs on every push
