---
name: add-coding-problem
description: Add a curated coding problem (V2 coding round) with statement, hint ladder, expected complexity, visible/hidden/performance tests, and verify it against reference solutions.
---

# Add a coding problem

Coding problems are **always curated with verified tests** — never LLM-generated live (ADR-0008).

1. Create `content/coding_problems/<id>.yaml` (see `lru_cache.yaml`): `difficulty`, `tags`,
   `role_families`, `tiers`, `statement` (own words), `complexity` (optimal/acceptable/brute),
   `hints` (3 levels, none giving the full answer), `tests` (visible + hidden + performance),
   `follow_ups`.
2. Write **two reference solutions** under `tests/fixtures/solutions/<id>/`: optimal and brute.
3. Verify in the sandbox: optimal passes all tests including performance; brute passes
   correctness but **times out** on performance. If brute passes, raise `ops` or lower
   `time_limit_s` — the performance test is what makes complexity judgement objective.
4. Add the problem to `tests/security/` smoke list (runs in the sandbox with network disabled).
