# ADR-0011: Retrieval only as a supporting component (V2), via pgvector

- Status: Accepted
- Date: 2026-10-07

## Context
Resume/JD fit in context — no RAG needed. Seed banks are small YAML. Only the growing real-question corpus needs retrieval.

## Options considered
1. Vector DB + RAG for everything.
2. Metadata filter + pgvector similarity for real questions only.

## Decision
Option 2, from V2. Fallback chain: round+tier+skill → similar tier → seed bank only; topics without anchors are marked 'unanchored' (lower confidence).

## Consequences
No extra infrastructure; the project is honestly described as an orchestrated workflow system, not a RAG app.
