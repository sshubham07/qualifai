# QualifAI Web

Thin single-page app — **no model runs in the browser** (ADR-0006); the interview room uses the
browser's own speech recognition for spoken answers (ADR-0022) and plays each question from the
server's speech model, with the browser's voice as the fallback (ADR-0024). React + Vite, TypeScript,
Tailwind, React Router (ADR-0015).

```bash
make web          # dev server with hot reload on http://localhost:3000; proxies /v1 to the API
make web-build    # writes frontend/dist; `make api` then serves the app at http://localhost:8000
```

The dev server expects the API on `http://localhost:8000` (override with `QUALIFAI_API_URL`) and
needs `make api` and `make worker` running. The form asks for no email (ADR-0017); the
status page shows a Meet ID and its link is the way back.

| Screen | Route | File | Purpose | Talks to | Status |
|---|---|---|---|---|---|
| Home | `/` | `src/pages/Home.tsx` | Explains the flow: share the role → kit prepared → interview → report | — | built |
| Setup | `/start` | `src/pages/Start.tsx` | Resume text, JD text, company type, experience range | `POST /v1/interviews` | built |
| Prep status | `/interviews/{id}` | `src/pages/Interview.tsx` | Submitted → Preparing → Ready, with the Meet ID to copy (polls every 3 s; SSE comes with T-15) | `GET /v1/interviews/{id}` | built |
| Interview | `/interviews/{id}` (in progress) | `src/pages/Room.tsx`, `src/lib/voice.ts` | Question streamed and read aloud, answer written as it is spoken and sent after a silence (draft autosave; text box where the browser cannot listen), elapsed time, phase indicator | `POST /v1/interviews/{id}/answers`, SSE | built |
| Report | — | — | Scorecard, claims table, evidence, prep plan | `GET /v1/interviews/{id}/report` | Phase 3 |

`src/lib/api.ts` is the only place that calls the API; its input limits mirror `InterviewRequest`
in `src/qualifai/domain/models.py`. Monaco arrives with the V2 coding round. Integrity signals
(paste events, time-to-first-keystroke, tab visibility) are captured client-side in Phase 2 and
sent as events, never blocking.
