# Tasks 001

Legend: `[x]` done in scaffold · `[ ]` open. Code TODOs reference these IDs.

## Domain & deterministic core
- [x] T-01 Domain enums, models, lifecycle state machine
- [x] T-02 TimeWindow (soft/target/hard, latency credit) + unit tests
- [x] T-03 Coverage guard + topic selector + unit tests
- [x] T-04 Policy engine + unit tests (incl. AC-2)
- [x] T-05 Context compiler with token budget + unit tests
- [x] T-06 Gap matrix + planner (phase allocation, must/should/bonus) + unit tests
- [x] T-07 Evidence check, aggregation, verdict + unit tests (incl. AC-5)
- [x] T-08 Architecture tests (import rules) + import-linter contracts

## Prep (Phase 1)
- [x] T-10 `prepare_interview_job`: load request, call `prepare_kit`, persist kit, READY, email (only if an email was given, ADR-0017)
- [ ] T-11 Contract tests for ResumeExtraction / JDExtraction / TopicPack with recorded fixtures
- [x] T-12 Seed-bank anchors loaded into topic-pack prompts
- [ ] T-13 Progressive readiness (FR-9): mark startable after intro + 2 packs
- [ ] T-14 Log unknown skills / unsupported roles to `demand_log`
- [ ] T-15 Prep progress → Redis pub/sub → SSE (interim, done: each step is stored as a `prep_step` event when it starts, and the status page polls it to show done / running / pending)
- [x] T-16 Intake gate as the first prep step (ADR-0016): resume and JD must both be software roles; FAILED with `failure_code` + reason shown on the status page
- [x] T-17 Resume–JD match check after extraction (ADR-0018): FAILED with `resume_jd_no_match` and a reason naming the skills only when nothing overlaps; FAILED is terminal
- [x] T-18 Opening question written in prep (`opening_question` task), stored in the kit and returned by the status endpoint when READY
- [x] T-19 Interview focus (ADR-0019): the form sends `round_type` (general, DSA, LLD, HLD, managerial); a focused round plans its own `skills`, topic packs get the round rules, length defaults to the round's `default_minutes`

## API & live loop (Phase 2)
- [x] T-20 `POST /v1/interviews` (JSON: resume text + JD text + tier + experience range; intake, dedupe, enqueue; returns `meet_id`)
- [x] T-21 `GET /v1/interviews/{id}` with `server_now`
- [ ] T-22 `POST /start` (auth, window, schedule hard stop, first question = the kit's opening question; stop returning it from the status endpoint)
- [ ] T-23 `POST /answers` (integrity events, resume graph, enqueue eval on end)
- [ ] T-24 `hard_stop_job` (auto-submit draft, resume with time_up)
- [ ] T-25 Postgres checkpointer wiring + graph version in state
- [ ] T-26 TurnSink implementation (turns, turn_analyses, SSE)
- [ ] T-27 E2E test: full interview with FakeLLM and FrozenClock

## Evaluation (Phase 3)
- [ ] T-30 `evaluate_interview_job` → report JSON stored
- [ ] T-31 Contract test for TopicEvaluation (quotes required)
- [ ] T-32 Report HTML render + object storage + `GET /report`
- [ ] T-33 Report-ready email (deferred with email delivery, ADR-0017)

## Ops
- [ ] T-40 `expire_kits` daily sweep + resume deletion
- [x] T-41 Initial Alembic migration
- [ ] T-42 Evals harness: 3 simulated candidates (strong / weak / bluffer)
