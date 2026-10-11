# ADR-0017: The candidate keeps a meet id; email is optional and deferred

- Status: Accepted
- Date: 2026-10-11

## Context
ADR-0007 has the candidate submit, leave, and come back through an emailed link once the kit is READY. Email only reaches Mailpit locally: there is no real provider, no SMTP auth or TLS settings, and no retry. Asking for an address and promising a mail we cannot deliver is worse than not asking. The candidate still needs a handle to come back with and see whether the interview is preparing or ready.

## Options considered
1. Keep the required email and wire a real provider now. Honest promise, but it means choosing a provider and handling bounces and retries before the interview itself exists.
2. Drop email from the form and hand back the interview id as a `meet_id`; keep the email path in the backend for when an address is supplied.
3. Generate a separate short code. Easier to type, but needs a new unique column, a lookup route and collision handling for no gain while the link is what people keep.

## Decision
Option 2. `POST /v1/interviews` returns `meet_id` (the interview's UUIDv7) and `GET /v1/interviews/{meet_id}` reports its status; the web app shows the meet id on the status page and the page link is the way back. `email` is optional in the API: without it no user row is created (`interviews.user_id` is nullable), no magic-link token is generated and nothing is sent. With it, the READY email works as before. Same-input reuse still applies: per user when there is one, across anonymous submissions otherwise.

## Consequences
The form is shorter and makes no promise we cannot keep. Whoever holds the meet id can see the interview's status, and until accounts or email return it is also the only thing `POST /start` (T-22) can check; a UUIDv7 is not guessable in practice, but it is a bearer handle and ends up in browser history. Two anonymous people submitting identical resume, JD, company type and range would share one kit, which we accept as vanishingly unlikely. The report-ready email (T-33) is deferred with the rest. Revisit when a mail provider or sign-in is chosen. Amends the "READY + email" part of ADR-0007.
