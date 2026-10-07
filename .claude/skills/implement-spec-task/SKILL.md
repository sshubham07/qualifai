---
name: implement-spec-task
description: Implement one task from a QualifAI spec (docs/specs/NNN/tasks.md) end to end — read spec and ADRs, write tests first at the right level, implement, run make check, tick the task.
---

# Implement a spec task

1. **Locate** the task ID (e.g. `T-12`) in `docs/specs/<NNN>-*/tasks.md`. Search the code for
   `TODO(spec-<NNN> T-12)` — that is where it plugs in.
2. **Read** `spec.md` (requirement + acceptance criteria it maps to) and `plan.md` (design notes).
   Read every ADR the plan links. If the task conflicts with an ADR, stop and ask.
3. **Classify the logic**:
   - decision / time / scoring / routing → deterministic module, pure function, no LLM imports
   - reading, phrasing, judging text → LLM task via `LLMGateway` + a prompt in `llm/prompts/`
4. **Tests first** (see `tests/README.md` for levels):
   - pure logic → `tests/unit/` (table-driven, plus a Hypothesis property if there's an invariant)
   - LLM output schema → `tests/contract/` with a recorded fixture
   - DB / Redis → `tests/integration/`
5. **Implement** the smallest change that passes. Keep functions small; no new layers or
   patterns unless the plan says so.
6. `make check` must pass (ruff, import-linter, mypy strict, fast tests).
7. **Tick** the task `- [x]` in `tasks.md`; remove the TODO. If you made a design decision that
   others need to know, use the `write-adr` skill.
