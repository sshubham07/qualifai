# ADR-0009: Round template × company tier instead of company-specific logic

- Status: Accepted
- Date: 2026-10-07

## Context
Per-company interview logic is messy, sparse and unmaintainable; interview formats cluster by round type and company tier.

## Options considered
1. Per-company profiles drive the interview.
2. Round templates × tier presets as config; company name optional flavour.

## Decision
Option 2. 5 rounds × 4 tiers from YAML; full loops compose rounds with shared findings.

## Consequences
Small, well-curated config space; real-question corpus tagged by round × tier fills faster than per-company buckets.
