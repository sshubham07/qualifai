# ADR-0003: LangGraph only for the live interview loop

- Status: Accepted
- Date: 2026-10-07

## Context
The live interview is a cyclic state machine that pauses for human input every turn and must survive crashes. Prep and evaluation are DAGs without cycles or human input.

## Options considered
1. LangGraph everywhere.
2. Hand-written loop everywhere.
3. LangGraph for the live loop only; plain async pipelines for prep and eval.

## Decision
Option 3. `interrupt()` waits for answers, Postgres checkpointer persists state per node, conditional edges read the PolicyDecision. No prebuilt agents; nodes call the gateway directly.

## Consequences
Crash recovery and resumability for free; graph is a readable diagram. Must version the graph for in-flight interviews. The orchestrator depends only on the event contract, so LangGraph stays replaceable.
