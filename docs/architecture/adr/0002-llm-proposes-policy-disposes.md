# ADR-0002: LLM proposes, deterministic policy disposes

- Status: Accepted
- Date: 2026-10-07

## Context
Letting an LLM run the interview makes behaviour inconsistent, untestable, and blind to time; small open-weight models ignore time hints and drift into generic follow-ups.

## Options considered
1. LLM agent decides next step from the transcript.
2. LLM outputs signals; a pure-Python policy decides the action; LLM phrases it.

## Decision
Option 2. Turn Analyzer returns TurnSignals; `interview/policy.py` (pure, unit-tested) returns a PolicyDecision; Question Generator only phrases it. Deterministic modules may not import LLM/DB code (import-linter + hook).

## Consequences
Every routing decision is explainable and testable (`decide(input) → action`). The LLM's job is narrower, which suits small models. Cost: more upfront design of signals and rules.
