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

- [x] T-36 Fundamentals topics (ADR-0023): each skill whose claim is verified also gets a topic about the skill itself; taxonomy gains nosql, cloud, ci_cd, testing; the closing line no longer says "out of time"

## API & live loop (Phase 2)
- [x] T-20 `POST /v1/interviews` (JSON: resume text + JD text + tier + experience range; always a new interview, enqueue; returns `meet_id`)
- [x] T-21 `GET /v1/interviews/{id}` with `server_now`
- [x] T-22 `POST /start` (owner token if the interview was emailed, READY + not expired, window, hard stop scheduled at hard_end + 60 s, first question = the kit's opening question; the status endpoint no longer returns it)
- [x] T-23 `POST /answers` (integrity events: pastes, time to first keystroke, idle time; graph resumed; latency credit stored; eval enqueued on end)
- [x] T-24 `hard_stop_job` (auto-submits the draft as a cut-off answer, resumes with time_up; puts itself back if latency credit moved hard_end)
- [x] T-25 Postgres checkpointer wiring + graph version in state
- [x] T-26 TurnSink implementation (turns, turn_analyses, integrity events, SSE tokens over Redis pub/sub)
- [x] T-27 E2E test: full interview over HTTP with FakeLLM, FrozenClock, Postgres and Redis
- [x] T-28 Draft autosave (`PUT /draft` → Redis, cleared on submit) and `GET /room` for a reloaded page
- [x] T-29 Interview room in the web app (streamed question, autosave, integrity signals, elapsed / ~target)
- [x] T-34 Voice in the interview room (ADR-0022): the question is read aloud, the microphone opens by itself, the answer is written as it is spoken and sent after a silence (no send button); a text box only where the browser cannot listen (`frontend/src/lib/voice.ts`)
- [x] T-35 The interviewer introduces himself and asks for an introduction before the opening question: name and greeting in `content/interviewer.yaml`, put in front of the first question at `POST /start` without a model call; the room prefers an Indian English voice and recogniser
- [x] T-37 Interviewer voice from a speech model (ADR-0024): `speech` task in `models.yaml`, `LLMGateway.speak` (sentence pieces joined into one WAV), `GET /turns/{seq}/audio` for stored interviewer turns only, room plays it and falls back to the browser voice
- [x] T-38 Room follow-ups: question text appears in step with the voice; a question the candidate asks at the wrap-up is answered from the job description before the goodbye (shown and spoken on the end screen); R1 always poses one problem-solving topic (`always:` in the round template)
## Evaluation (Phase 3)
- [ ] T-30 `evaluate_interview_job` → report JSON stored
- [ ] T-31 Contract test for TopicEvaluation (quotes required)
- [ ] T-32 Report HTML render + object storage + `GET /report`
- [ ] T-33 Report-ready email (deferred with email delivery, ADR-0017)

## Ops
- [ ] T-40 `expire_kits` daily sweep + resume deletion
- [x] T-41 Initial Alembic migration
- [ ] T-42 Evals harness: 3 simulated candidates (strong / weak / bluffer)
