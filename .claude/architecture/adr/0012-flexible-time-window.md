# ADR-0012: Flexible time window instead of a hard deadline

- Status: Accepted
- Date: 2026-10-07

## Context
Real interviews end at a natural point around the target, not mid-sentence when a timer hits zero.

## Options considered
1. Single hard deadline.
2. soft_start / target_end / hard_end window with fit checks.

## Decision
Option 2 (45 → 40/45/50). Policy only starts items that fit before hard_end, ends at topic boundaries, reserves closing time; scheduled hard-stop job at hard_end + grace. Window shifts by system-latency credit (≤ 3 min). UI shows elapsed / ~target, not a countdown.

## Consequences
Natural endings and fairness on slow hardware; end_reason recorded.
