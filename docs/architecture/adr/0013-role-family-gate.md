# ADR-0013: Role-family intake gate; Backend SDE only in MVP

- Status: Accepted; where and how the gate runs is superseded by ADR-0016
- Date: 2026-10-07

## Context
Without a gate the system would run DSA rounds for MBA candidates and improvise rubrics it can't evaluate.

## Options considered
1. Accept everything.
2. Classify role from JD (+resume) and decide support from config.

## Decision
Option 2. Full: backend SDE. Partial ('limited mode', no coding): nearby technical roles. Unsupported: declined politely before prep; demand logged. Career-switch mismatches allowed with a warning.

## Consequences
Evaluation quality stays credible; demand data decides which role pack to build next.
