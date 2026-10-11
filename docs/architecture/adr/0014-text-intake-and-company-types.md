# ADR-0014: Text-only intake; company types are service, startup, product, MAANG

- Status: Accepted
- Date: 2026-10-11

## Context
Phase 1 takes four inputs: resume, JD, experience range and type of company. The scaffold took the resume as a PDF upload (stored in object storage, parsed with pymupdf) and named the tiers service / midscale / product / faang, which is not how candidates describe companies.

## Options considered
1. PDF upload → text, PDF kept in object storage (ADR-0005).
2. Resume submitted as text in a JSON body, stored on the interview row.
3. Accept both.

## Decision
Option 2. `POST /v1/interviews` takes JSON with `resume_text` and `jd_text`; the resume text lives in `interviews.resume_text` and is nulled after completion/expiry. Tier ids are renamed `midscale → startup` and `faang → maang` (presets unchanged); ADR-0009's round × tier model stands. Object storage now holds rendered reports only.

## Consequences
No PDF parsing or upload path in prep, and the worker reads everything it needs from Postgres. Candidates must paste text, so layout-dependent resumes lose structure. Resume text sits in the primary database until the retention sweep (T-40) removes it. `pymupdf` and `python-multipart` are no longer used and can be dropped from the dependencies.
