# High-Level Design

## 1. Context
```mermaid
flowchart LR
  C([Candidate]) -->|resume, JD, round, tier| W[Web app]
  W <-->|REST + SSE| API[QualifAI API]
  API --> Q[(Redis queue)]
  Q --> WK[Worker]
  API & WK --> PG[(PostgreSQL)]
  API & WK --> OBJ[(Object storage)]
  API & WK --> GW[LLM Gateway]
  GW --> OL[Ollama · local]
  GW --> GQ[Free hosted open-weight · Groq-style]
  GW --> VL[vLLM · rented GPU]
  WK --> MAIL[SMTP]
```

## 2. Components
| Component | Responsibility | Tech |
|---|---|---|
| Web | Thin single-page app: setup, prep status, interview, report; no AI in the browser | React + Vite, static build served by the API |
| API | Validation, auth, intake gate (sync), start/answer endpoints, SSE, serves the built web app | FastAPI |
| Worker | Prep pipeline, evaluation pipeline, hard-stop jobs, daily expiry | arq on Redis |
| Interview engine | LangGraph loop + Policy + Context Compiler + TimeWindow | LangGraph, pure Python |
| LLM Gateway | Task routing, structured output + validation + retries, streaming, telemetry | openai SDK (OpenAI-compatible) |
| Content | Rounds, tiers, role families, skills, problems, model routes | YAML + Pydantic |
| Persistence | Source of truth; checkpoints; JSONB for LLM outputs; pgvector (V2) | PostgreSQL 16 |
| Ephemeral | Drafts, queue, delayed jobs, counters, rate limits | Redis 7 |
| Files | Rendered reports | S3-compatible (MinIO) |
| Sandbox (V2) | Untrusted code execution | Judge0 / Docker + gVisor |

## 3. Lifecycle
```mermaid
stateDiagram-v2
  [*] --> SUBMITTED
  SUBMITTED --> PREPARING: intake gate passed
  SUBMITTED --> [*]: unsupported role (422, demand logged)
  PREPARING --> READY: kit built (email)
  PREPARING --> FAILED
  READY --> IN_PROGRESS: start (token/session)
  READY --> EXPIRED: 7 days untaken (kit + resume deleted)
  IN_PROGRESS --> COMPLETED: natural end / hard stop
  COMPLETED --> EVALUATING
  EVALUATING --> REPORT_READY: report (email)
  EVALUATING --> FAILED
  FAILED --> PREPARING: retry
```

## 4. Live turn (sequence)
```mermaid
sequenceDiagram
  participant UI
  participant API
  participant G as LangGraph
  participant TA as Turn Analyzer (LLM)
  participant P as Policy (code)
  participant QG as Question Gen (LLM)
  participant DB as Postgres
  UI->>API: POST /answers (text, timings, paste flag)
  API->>G: resume(answer)
  G->>DB: append candidate turn (commit)
  G->>TA: bounded context + answer
  TA-->>G: TurnSignals (JSON)
  G->>P: signals + time window + budgets
  P-->>G: action (e.g. CHALLENGE_CLAIM)
  G->>QG: phrase action
  QG-->>UI: streamed question (SSE)
  G->>DB: append interviewer turn + checkpoint
```

## 5. Data model (core)
```mermaid
erDiagram
  USERS ||--o{ INTERVIEWS : owns
  INTERVIEWS ||--|| INTERVIEW_KITS : has
  INTERVIEWS ||--o{ TURNS : "append-only"
  TURNS ||--o| TURN_ANALYSES : analysed_by
  INTERVIEWS ||--o{ INTERVIEW_EVENTS : logs
  INTERVIEWS ||--o{ TOPIC_SUMMARIES : closes
  INTERVIEWS ||--o{ EVALUATIONS : "per topic"
  INTERVIEWS ||--o| REPORTS : produces
```

## 6. Non-functional requirements
| NFR | Target (MVP, text mode) |
|---|---|
| Next question latency | p50 < 4 s, p95 < 8 s (two LLM calls; streaming starts earlier) |
| Prep time | ≤ 10 min local, ≤ 3 min hosted; "ready to start" after first 2 topic packs |
| Durability | Submitted answer committed before next question; crash → resume from checkpoint |
| Privacy | Resume deleted after completion/expiry; reports kept 90 days; no answers in logs |
| Cost | ₹0 model cost on free tiers (≈ 1 full interview/day/model on free quotas) |
| Concurrency | 1–3 live interviews per local machine; scale by moving live models to hosted/vLLM |

## 7. Capacity estimate
~30 turns × ~5k tokens (2 calls) ≈ 150k tokens live; prep ≈ 30–40k; eval ≈ 40–60k.
Transcript ≈ 50–150 KB per interview → Postgres is trivially sufficient.

## 8. Failure modes
| Failure | Behaviour |
|---|---|
| LLM timeout / invalid JSON | Gateway retries ×3 with backoff; live loop falls back to a pre-generated opening question; END uses a fixed template |
| Provider rate-limited | Router can switch provider per task via config; prep/eval jobs retry later |
| Redis lost | Rebuild from Postgres checkpoint; lose ≤ a few seconds of draft text |
| Worker crash mid-prep | Job retried; prep steps idempotent on (interview_id, step) |
| Candidate disconnects | Clock continues server-side; rejoin via session; hard-stop job ends it |
| Evidence quotes not found | Dimension dropped; topic may become low-confidence; never invented |

## 9. Security
Candidate/resume text is always data (tagged in prompts; injection markers flagged).
Magic-link tokens stored hashed, swapped for a session cookie at start; one attempt per kit.
Sandbox isolated from API and DB (V2). Secrets only via env; hooks block editing `.env`.
