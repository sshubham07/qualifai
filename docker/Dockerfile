# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1
RUN pip install --no-cache-dir uv==0.4.*
WORKDIR /app

FROM base AS deps
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

FROM deps AS runtime
COPY src ./src
COPY content ./content
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv pip install --system --no-deps -e .
RUN useradd --create-home --uid 10001 app
USER app
# Command is set per process in docker-compose (api / worker).
