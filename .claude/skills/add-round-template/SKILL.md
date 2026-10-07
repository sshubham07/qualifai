---
name: add-round-template
description: Add or change an interview round (R1 Technical, R2 LLD, R3 HLD, R4 Managerial, HR) or a company-tier preset as configuration in content/, with schema validation and tests — no engine code changes.
---

# Add / change a round template or tier preset

Rounds and tiers are **config**, not code (ADR-0009). The engine reads them.

## Round template — `content/rounds/<round_id>.yaml`
Required keys (validated by `content/loader.py::RoundTemplate`):
- `id` (must exist in `domain/enums.py::RoundType` — add it there first if new)
- `name`, `default_minutes`
- `phases`: list of `{name, weight, reserved?}`; must include a `core` phase (planner puts topics
  there) and a reserved `closing` phase
- `rubric_dimensions`: what topic evaluation scores (3–5 dimensions)
- `rules`: 2–4 lines of interviewer behaviour for prompts
- optional `needs_editor`, `needs_sandbox`, `scored`

## Tier preset — `content/tiers/<tier>.yaml`
`difficulty_offset`, `max_depth`, `challenge_threshold`, `must_have_floor`, `bands`
(`strong_hire > hire > lean_hire > lean_no_hire`, all on /10), `guidance`.

## Checklist
1. Write the YAML. Keep rules short and interview-realistic.
2. `python scripts/seed_content.py` — must load without errors.
3. Add a unit test in `tests/unit/test_planner.py` that `allocate_phases` sums to the duration
   for the new round, and (for tiers) a verdict test in `tests/unit/test_verdict.py`.
4. Update the round/tier tables in `README.md` if user-visible.
