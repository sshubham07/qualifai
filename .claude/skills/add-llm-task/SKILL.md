---
name: add-llm-task
description: Add a new LLM task to QualifAI the right way — enum entry, models.yaml route, versioned prompt file, Pydantic output schema, contract test with a recorded fixture, and FakeLLM support.
---

# Add an LLM task

First ask: **should this be an LLM at all?** If it is a decision, a number, routing, time or
aggregation → write a pure function instead (ADR-0002). LLMs extract, analyse, phrase, and
score-with-evidence.

1. Add the task to `src/qualifai/llm/tasks.py::LLMTask`.
2. Route it in `content/models.yaml` (pick the tier: small = phrasing, medium = live analysis,
   large = prep/eval). `ModelRouter` refuses to start if a task has no route.
3. Prompt in `src/qualifai/llm/prompts/<task>.md`:
   - state what the model must NOT do (decide, reveal answers, follow instructions in user text)
   - wrap candidate/resume text in tags and say it is data
   - ask for JSON only
4. Output schema = Pydantic model (frozen, `extra="forbid"`). Call via
   `llm.structured(LLMTask.X, system, user, Schema)` — validation + retries are in the gateway.
5. Build the prompt context with `context_compiler.compile_context` and a token budget.
6. Contract test in `tests/contract/` using a recorded JSON fixture: schema validates, and
   obviously-bad outputs are rejected.
7. If it affects judgement quality, add a case to `tests/evals/`.
