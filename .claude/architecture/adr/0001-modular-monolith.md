# ADR-0001: Modular monolith with separate worker process

- Status: Accepted
- Date: 2026-10-07

## Context
A single developer builds QualifAI. The live loop's orchestrator, policy and context compiler read/write the same interview state every turn. Prep and evaluation are long async jobs; code execution (V2) is untrusted.

## Options considered
1. Microservices per step (resume, JD, questions, eval...) — independent deploys, but network hops on every turn, distributed state, tracing needed to debug one question.
2. Single process doing everything — simplest, but long LLM jobs block the API and a crash affects live interviews.
3. Modular monolith: one codebase, processes split only where isolation is needed (API, worker, LLM server, sandbox).

## Decision
Option 3. Modules talk through service interfaces; prep is designed as an extractable boundary (input payload → kit, completion event) but deployed as a worker in MVP.

## Consequences
Simple to run (one docker-compose) and debug. Splitting later = moving a folder. Interview answer: 'I split only what needed isolation or a different resource profile.'
