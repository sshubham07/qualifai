# Spec 001 — MVP: adaptive text interview (R1 Technical, R4 Managerial)

## Summary
A backend candidate submits resume + JD + round + company tier; QualifAI prepares a kit, runs a
~45-minute adaptive text interview, and delivers an evidence-backed report.

## User stories
- **US-1** As a candidate, I submit my resume (text), a JD (text), round, company tier (service, startup, product, MAANG), experience range and duration
  and immediately learn whether my role is supported.
- **US-2** As a candidate, I'm told when my interview is ready and can start it within 7 days.
- **US-3** As a candidate, I'm asked questions about *my* claims and the JD's priorities, with
  follow-ups that react to what I say.
- **US-4** As a candidate, the interview ends naturally around the target time.
- **US-5** As a candidate, I receive a report with scores, evidence, a verdict for my tier, and a
  prep plan.

## Functional requirements
| ID | Requirement |
|---|---|
| FR-1 | Intake gate classifies role family from JD (+resume); unsupported roles get 422 with a clear message before any prep; demand is logged |
| FR-2 | Non-resume / non-JD uploads rejected; size limits enforced; injection markers flagged, not obeyed |
| FR-3 | Prep extracts a claims ledger and weighted JD skills, normalised via the taxonomy |
| FR-4 | Gap matrix classifies each JD skill: verify claim / test gap / light |
| FR-5 | Planner allocates phase budgets from the round template and a must/should/bonus topic pool |
| FR-6 | Topic packs (opening questions, rubric, follow-up hooks) are generated per topic, grounded in seed banks |
| FR-7 | Kit READY → email with link; `expires_at = ready_at + 7d`; daily sweep expires kits and deletes resume text |
| FR-8 | Start requires owner auth, READY, not expired, not started; one attempt per kit |
| FR-9 | Progressive readiness: "ready to start" once intro + first 2 topic packs exist |
| FR-10 | Each answer is analysed into signals; the policy picks the next action; the LLM phrases it |
| FR-11 | Coverage guard: follow-ups never consume time reserved for unvisited must-cover topics |
| FR-12 | Time window soft/target/hard (45 → 40/45/50); natural end at topic boundaries; hard-stop job |
| FR-13 | Latency credit: slow-system time shifts the window (cap 3 min) |
| FR-14 | Drafts autosave; paste events and timing recorded as integrity signals |
| FR-15 | Evaluation per topic with anchored levels + quotes; unverifiable quotes dropped |
| FR-16 | Verdict computed by code: weighted by JD, gates, tier thresholds; "insufficient evidence" when must coverage < 75% |
| FR-17 | Report shows coverage, confidence, claims verification table, topic breakdown, deciding gap, prep plan |

## Non-functional requirements
| ID | Requirement |
|---|---|
| NFR-1 | Next-question p95 < 8 s on hosted models (text mode) |
| NFR-2 | Live LLM prompts ≤ 2k tokens regardless of interview length |
| NFR-3 | Submitted answers committed before the next question is shown |
| NFR-4 | Crash or redeploy mid-interview resumes from checkpoint; clock never pauses |
| NFR-5 | No answer text in application logs; resume deleted after completion/expiry |
| NFR-6 | Runs at ₹0 model cost on local / free hosted open-weight models |

## Acceptance criteria (examples)
- **AC-1** Given an MBA JD, when submitted, then 422 `unsupported_role` and nothing is enqueued.
- **AC-2** Given 6 min remaining and two unvisited must topics needing 3 min each plus 2 min
  closing, when a strong answer arrives, then the policy does **not** follow up.
- **AC-3** Given the clock passes hard_end with no answer, then the interview completes with
  `end_reason = hard_stop` and evaluation is enqueued.
- **AC-4** Given an evaluation citing a quote the candidate never said, then that dimension is
  dropped and the report confidence reflects it.
- **AC-5** Given skills K 8.1 (w3, must), P 4.6 (w3, must), F 7.5 (w2), C 6.0 (w2), B 7.0 (w1)
  on the **service** tier, then overall = 6.55, raw band = hire, must-have gate caps to
  **lean_hire** ("Almost ready").
