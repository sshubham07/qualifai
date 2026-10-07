# Spec 002 — Coding round (DSA in R1) and R2 LLD — DRAFT

- Curated problem bank (`content/coding_problems/`) with visible, hidden and performance tests.
- Monaco editor; Run (visible tests) vs Submit (hidden + performance).
- Event-driven controller: idle → hint ladder; repeated failures → edge-case nudge.
- Sandbox: Judge0 self-hosted on a separate Linux host; network disabled; CPU/mem/time limits.
- Complexity: performance tests are ground truth; LLM labels/explains Big-O; disagreement →
  trust tests, mark label low-confidence; compare with the candidate's stated complexity.
- R2 LLD: candidate writes classes/interfaces; rubric = entity modeling, responsibilities,
  extensibility, code clarity; follow-ups like "add EV charging spots".
- Simulated-candidate evals extended to code.
