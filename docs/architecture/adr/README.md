# Architecture Decision Records

Format: MADR-lite. New ADRs via the `write-adr` skill. Never edit an accepted decision — supersede it.

| # | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith with separate worker process | Accepted |
| [0002](0002-llm-proposes-policy-disposes.md) | LLM proposes, deterministic policy disposes | Accepted |
| [0003](0003-langgraph-only-for-live-loop.md) | LangGraph only for the live interview loop | Accepted |
| [0004](0004-open-weight-models-gateway.md) | Open-weight models behind an OpenAI-compatible gateway with per-task routing | Accepted |
| [0005](0005-postgres-redis-object-storage.md) | PostgreSQL as source of truth, Redis for ephemeral data, S3-compatible storage for files | Accepted |
| [0006](0006-text-first.md) | Text-first interface; voice and avatar deferred | Accepted |
| [0007](0007-async-prep-interview-kit.md) | Asynchronous prep producing an interview kit, with 7-day expiry | Accepted |
| [0008](0008-evidence-based-evaluation.md) | Topic-level, evidence-cited evaluation with a computed verdict | Accepted |
| [0009](0009-round-by-tier-config.md) | Round template × company tier instead of company-specific logic | Accepted |
| [0010](0010-no-mcp.md) | No MCP | Accepted |
| [0011](0011-retrieval-as-supporting-component.md) | Retrieval only as a supporting component (V2), via pgvector | Accepted |
| [0012](0012-flexible-time-window.md) | Flexible time window instead of a hard deadline | Accepted |
| [0013](0013-role-family-gate.md) | Role-family intake gate; Backend SDE only in MVP | Accepted, partly superseded by 0016 |
| [0014](0014-text-intake-and-company-types.md) | Text-only intake; company types are service, startup, product, MAANG | Accepted |
| [0015](0015-react-vite-spa-served-by-api.md) | Frontend is a React + Vite single-page app served by the API | Accepted |
| [0016](0016-intake-gate-in-prep-job.md) | The intake gate runs in the prep job; both documents must be for a software role | Accepted |
| [0017](0017-meet-id-email-deferred.md) | The candidate keeps a meet id; email is optional and deferred | Accepted |
| [0018](0018-resume-jd-match-gate-failed-terminal.md) | A resume–JD match check stops prep; FAILED is terminal | Accepted |
| [0019](0019-interview-focus-is-the-round.md) | The interview focus is the round; a focused round brings its own topics | Accepted |
| [0020](0020-live-room-lock-graph-time-repeatable-writes.md) | The live room locks the interview row, the graph keeps its own time, transcript writes are repeatable | Accepted |
| [0021](0021-every-submission-is-a-new-interview.md) | Every submission is a new interview; kits are not reused | Accepted |
