# ADR-0021: Every submission is a new interview; kits are not reused

- Status: Accepted
- Date: 2026-10-12

## Context
ADR-0007 hashed the inputs so a resubmission of the same resume, JD and settings got the existing kit back instead of a new prep, and ADR-0017 kept that for submissions without an email, matching across all anonymous users. In use this was confusing: pasting the same documents returned an older interview at once, with no sign that nothing had been prepared, and questions already seen. Without accounts it also meant two people with identical inputs would share one interview, and since a kit allows one attempt, the first to start would take it.

## Options considered
1. Keep the reuse and tell the candidate on the page that this is an earlier interview.
2. Keep the reuse but add a "prepare again" switch to the form.
3. Remove the reuse: every submission creates its own interview and runs its own prep.

## Decision
Option 3. `POST /v1/interviews` always inserts a new interview, returns a new meet id and enqueues prep. The `input_hash` column and its index are dropped.

## Consequences
What you submit is what gets prepared, and one meet id belongs to one submission. A repeated submission costs a full prep again (model calls and a few minutes), and a double-clicked submit creates two interviews; the form disables its button while sending, and unstarted interviews expire after seven days. Supersedes the "inputs hashed to reuse kits" part of ADR-0007 and the same-input reuse described in ADR-0017.
