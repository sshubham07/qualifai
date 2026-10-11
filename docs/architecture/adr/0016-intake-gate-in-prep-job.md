# ADR-0016: The intake gate runs in the prep job; both documents must be for a software role

- Status: Accepted
- Date: 2026-10-11

## Context
ADR-0013 ran the gate synchronously inside `POST /v1/interviews` and answered an unsupported role with a 422, storing nothing. The gate model is now a small local model (Ollama), whose first call can take many seconds, and a rejected candidate had no interview page to come back to. ADR-0013 also let a mismatched resume through with a warning; we now want prep to stop unless the resume **and** the JD are both for a software role, and to stop when the model cannot tell.

## Options considered
1. Keep the gate synchronous in the API and return 422 (ADR-0013). Fails fast, but the request waits on a local model and the reason is lost once the form is closed.
2. Keep it synchronous but store a FAILED interview. Keeps the reason, still blocks the request on the model.
3. Run the gate as the first step of the prep job and record the outcome on the interview.

## Decision
Option 3. `POST /v1/interviews` validates, dedupes, stores the interview as PREPARING and enqueues the job; it makes no model call. The job classifies both documents first (`intake_gate` task), and `prep/intake_gate.py::decide` returns a support level or a `FailureCode`: not a resume, not a JD, resume not software, JD not software, or undecided (unknown family, low confidence on a software pair, or no usable model output). On a failure the interview becomes FAILED with `failure_code` and `failure_reason`, and no extraction or question writing runs. Which families count as software stays in `content/role_families/*.yaml` (ADR-0013): a family with no file, or marked `unsupported`, is rejected.

## Consequences
The candidate always gets a status page that says preparing, ready, or failed with the reason. The API no longer depends on the LLM gateway. A rejection now costs a stored row and a queued job instead of nothing, and the resume text of a rejected submission stays in Postgres until the retention sweep (T-40). Career switchers with a non-software resume are turned away; revisit if that proves too strict. Supersedes the sync / 422 and mismatch-warning parts of ADR-0013.
