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
| [0013](0013-role-family-gate.md) | Role-family intake gate; Backend SDE only in MVP | Accepted |
| [0014](0014-text-intake-and-company-types.md) | Text-only intake; company types are service, startup, product, MAANG | Accepted |
| [0015](0015-react-vite-spa-served-by-api.md) | Frontend is a React + Vite single-page app served by the API | Accepted |
