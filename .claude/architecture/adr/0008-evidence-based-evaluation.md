# ADR-0008: Topic-level, evidence-cited evaluation with a computed verdict

- Status: Accepted
- Date: 2026-10-07

## Context
LLM judges are inconsistent on 1–10 scales, biased toward verbosity, and may cite things never said. One-shot whole-transcript evaluation is too long for small models.

## Options considered
1. Whole transcript → LLM → HTML report.
2. Per-question scoring.
3. Per-topic anchored scoring with quotes → evidence check → code aggregation and gates → LLM explains.

## Decision
Option 3. Anchored levels 1–4 (shown as /10), quotes verified against the transcript, skill scores weighted by evidence, gates (coverage, must-have, claim, coding), tier thresholds → band. Jinja renders HTML; report JSON is the source of truth.

## Consequences
Reproducible, explainable verdicts; honest 'insufficient evidence'. Coding correctness/performance always from tests, never LLM opinion.
