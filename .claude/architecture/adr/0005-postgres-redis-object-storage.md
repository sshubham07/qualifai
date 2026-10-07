# ADR-0005: PostgreSQL as source of truth, Redis for ephemeral data, S3-compatible storage for files

- Status: Accepted
- Date: 2026-10-07

## Context
Data is relational (user → interviews → turns → analyses → evaluations), small (~100 KB/interview), needs transactions, and has evolving LLM-output shapes.

## Options considered
1. MongoDB for flexible docs.
2. Separate vector DB.
3. Postgres (JSONB, pgvector later) + Redis + object storage.

## Decision
Option 3. Postgres: everything durable incl. LangGraph checkpoints. Redis: drafts, queue, delayed jobs, counters, rate limits. MinIO/S3: PDFs and rendered reports.

## Consequences
One database to operate and reason about. Redis loss costs seconds of drafts. No Kafka/RabbitMQ/Elasticsearch until a real need appears.
