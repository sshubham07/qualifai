# QualifAI Web (placeholder)

The MVP frontend is intentionally thin — **no AI runs in the browser** (ADR-0006).

| Screen | Purpose | Talks to |
|---|---|---|
| Setup | Upload resume, paste JD, pick round + company tier, experience, duration | `POST /v1/interviews` |
| Prep status | Live progress ("Parsing resume ✓ · Building plan…") | `GET /v1/interviews/{id}/events` (SSE) |
| Interview | Streamed question, answer box (draft autosave), elapsed `32:10 / ~45 min`, phase indicator | `POST /v1/interviews/{id}/answers`, SSE |
| Report | Scorecard, claims table, evidence, prep plan | `GET /v1/interviews/{id}/report` |

Suggested stack: Next.js + TypeScript + Tailwind, Monaco editor for V2 coding rounds.
Integrity signals captured client-side (sent as events, never blocking): paste events,
time-to-first-keystroke, tab visibility changes.
