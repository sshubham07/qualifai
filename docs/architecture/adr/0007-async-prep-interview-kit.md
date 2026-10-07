# ADR-0007: Asynchronous prep producing an interview kit, with 7-day expiry

- Status: Accepted
- Date: 2026-10-07

## Context
Preparing good questions and rubrics needs a large, slow model. Pre-generating a fixed script would kill adaptivity.

## Options considered
1. Generate everything live.
2. Fixed pre-generated script.
3. Pre-generate a kit (plan, rubrics, follow-up trees); adapt live.

## Decision
Option 3. 202 Accepted → worker builds kit → READY + email → candidate starts within 7 days; daily sweep expires kits and deletes resume files. Progressive readiness allows starting after the first topic packs.

## Consequences
Better rubrics (biggest quality lever for small live models), faster live turns, clear privacy story. Inputs hashed to reuse kits.
