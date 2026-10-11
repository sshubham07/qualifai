# ADR-0015: Frontend is a React + Vite single-page app served by the API

- Status: Accepted
- Date: 2026-10-11

## Context
The web client is thin (ADR-0006): all data comes from the FastAPI service and no AI runs in the browser. Phase 1 needs three screens (home, setup, prep status). Phase 2 adds a stateful interview screen (streamed question, timer, draft autosave, integrity signals) and V2 adds the Monaco editor. The scaffold suggested Next.js.

## Options considered
1. Next.js — server rendering and a Node server we would not use; adds a third process and a proxy to the API.
2. Plain HTML + JavaScript served by the API — simplest today, but the interview screen's state gets hard to manage without components.
3. React + Vite single-page app, built to static files and served by the API.

## Decision
Option 3. `frontend/` is a React + Vite app (TypeScript, Tailwind, React Router). `npm run build` writes `frontend/dist`, which the API serves with a fallback to `index.html` for client-side routes; `/v1/*` and `/healthz` stay API routes. In development the Vite server on port 3000 proxies `/v1` to the API.

## Consequences
Production stays at two processes (api + worker, ADR-0001) on one origin, so no CORS or proxy. Components are available for the Phase 2 and V2 screens. Node is needed to build the web app, and the API image must include the built files to serve the UI. No server-side rendering, which is acceptable because only the home page is public content.
