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
- [x] T-10 `prepare_interview_job`: load request, call `prepare_kit`, persist kit, READY, email
- [ ] T-11 Contract tests for ResumeExtraction / JDExtraction / TopicPack with recorded fixtures
- [x] T-12 Seed-bank anchors loaded into topic-pack prompts
- [ ] T-13 Progressive readiness (FR-9): mark startable after intro + 2 packs
- [ ] T-14 Log unknown skills / unsupported roles to `demand_log`
- [ ] T-15 Prep progress → Redis pub/sub → SSE

## API & live loop (Phase 2)
- [x] T-20 `POST /v1/interviews` (JSON: resume text + JD text + tier + experience range; intake, dedupe, enqueue)
- [x] T-21 `GET /v1/interviews/{id}` with `server_now`
- [ ] T-22 `POST /start` (auth, window, schedule hard stop, first question)
- [ ] T-23 `POST /answers` (integrity events, resume graph, enqueue eval on end)
- [ ] T-24 `hard_stop_job` (auto-submit draft, resume with time_up)
- [ ] T-25 Postgres checkpointer wiring + graph version in state
- [ ] T-26 TurnSink implementation (turns, turn_analyses, SSE)
- [ ] T-27 E2E test: full interview with FakeLLM and FrozenClock

## Evaluation (Phase 3)
- [ ] T-30 `evaluate_interview_job` → report JSON stored
- [ ] T-31 Contract test for TopicEvaluation (quotes required)
- [ ] T-32 Report HTML render + object storage + `GET /report`
- [ ] T-33 Report-ready email

## Ops
- [ ] T-40 `expire_kits` daily sweep + resume deletion
- [x] T-41 Initial Alembic migration
- [ ] T-42 Evals harness: 3 simulated candidates (strong / weak / bluffer)
