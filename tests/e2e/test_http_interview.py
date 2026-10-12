"""HTTP E2E (spec-001 T-27): a whole interview through the API — submit, prep, start, answers,
end — with FakeLLM, FrozenClock, real Postgres (transcript + LangGraph checkpoints) and real
Redis (job queue, drafts, live events). Skipped automatically without Docker."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from itertools import cycle
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tests.prep_fakes import JD, OPENING, RESUME, prep_llm

from qualifai.api.deps import get_clock, get_live
from qualifai.api.main import create_app
from qualifai.api.routes.interviews import sse_frames
from qualifai.container import LiveRuntime
from qualifai.content.loader import interviewer
from qualifai.db.models import Base, Interview, InterviewEvent, TurnAnalysis, TurnRow
from qualifai.db.session import get_session
from qualifai.domain.clock import FrozenClock, SystemClock
from qualifai.interview import room
from qualifai.interview.checkpoint import open_checkpointer
from qualifai.interview.service import InterviewService
from qualifai.llm.fake import FakeLLM
from qualifai.llm.tasks import LLMTask
from qualifai.storage.live import subscribe
from qualifai.workers.jobs.hard_stop import hard_stop_job
from qualifai.workers.jobs.prepare import PrepDeps, hash_token, prepare_interview

pytestmark = pytest.mark.e2e
# The interviewer introduces himself, then asks the opening question written in prep.
FIRST_WORDS = f"{interviewer().greet(45)} {OPENING}"
GRACE_S = 60
# The hard stop goes into a real queue, which only takes jobs that are due in the future.
T0 = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=1)


def fake_llm(coverages: list[float]) -> FakeLLM:
    cov = cycle(coverages)
    live = {
        LLMTask.TURN_ANALYZER: lambda _s, _u: {
            "intent": "answer",
            "coverage_ratio": next(cov),
            "specificity": "high",
            "consistency": "consistent",
        },
        LLMTask.QUESTION_GEN: lambda _s, _u: "Generated interviewer question?",
    }
    return FakeLLM({**prep_llm()._responders, **live})


class Stack:
    """The API wired the way the lifespan wires it, on test infrastructure."""

    def __init__(self, sessions, redis, checkpointer, coverages: list[float]) -> None:
        self.sessions, self.redis, self.checkpointer = sessions, redis, checkpointer
        self.clock, self.llm = FrozenClock(T0), fake_llm(coverages)
        self.live = self.runtime()
        self.app = create_app(Path("/nonexistent"))
        self.app.state.arq = redis
        self.app.dependency_overrides[get_session] = self._session
        self.app.dependency_overrides[get_clock] = lambda: self.clock
        self.app.dependency_overrides[get_live] = lambda: self.live
        self.http = AsyncClient(transport=ASGITransport(self.app), base_url="http://t")

    def runtime(self) -> LiveRuntime:
        service = InterviewService(self.checkpointer)
        return LiveRuntime(service, self.llm, self.redis, self.sessions, "fake-model", GRACE_S)

    async def _session(self):
        async with self.sessions() as s:
            yield s

    async def ready_interview(self, email: str | None = None) -> tuple[str, str | None]:
        """POST the interview, then run the prep job the way the worker would."""
        body = {
            "resume_text": RESUME,
            "jd_text": JD,
            "company_tier": "product",
            "experience_min_years": 3,
            "experience_max_years": 5,
            "email": email,
        }
        accepted = (await self.http.post("/v1/interviews", json=body)).json()
        links: list[str] = []

        async def send(_to: str, link: str, _expires: str) -> None:
            links.append(link)

        deps = PrepDeps(self.llm, self.clock, send, "http://app", kit_ttl_days=7)
        async with self.sessions() as s:
            await prepare_interview(s, deps, UUID(accepted["meet_id"]))
        return accepted["meet_id"], links[0].split("token=")[1] if links else None

    async def answer(self, meet_id: str, seq: int, text: str = "A detailed answer", **extra):
        body = {"question_seq": seq, "text": text, **extra}
        return await self.http.post(f"/v1/interviews/{meet_id}/answers", json=body)

    async def interview(self, meet_id: str) -> Interview:
        async with self.sessions() as s:
            return await s.get_one(Interview, UUID(meet_id))

    async def turns(self, meet_id: str) -> list[TurnRow]:
        async with self.sessions() as s:
            rows = await s.scalars(
                select(TurnRow).where(TurnRow.interview_id == UUID(meet_id)).order_by(TurnRow.seq)
            )
            return list(rows)

    async def events(self, meet_id: str, type_: str) -> list[dict]:
        async with self.sessions() as s:
            rows = await s.scalars(
                select(InterviewEvent.payload)
                .where(InterviewEvent.interview_id == UUID(meet_id), InterviewEvent.type == type_)
                .order_by(InterviewEvent.id)
            )
            return list(rows)

    async def hard_stop(self, meet_id: str) -> None:
        async with self.sessions() as s:
            await room.hard_stop(self.live.room(s, self.clock), UUID(meet_id))


@pytest.fixture
async def stack(pg_url, redis_url):
    engine = create_async_engine(pg_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    redis = await create_pool(RedisSettings.from_dsn(redis_url))
    await redis.flushdb()
    async with open_checkpointer(pg_url) as checkpointer:

        def build(coverages: list[float] | None = None) -> Stack:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            return Stack(sessions, redis, checkpointer, coverages or [0.9])

        yield build
    await redis.aclose()
    await engine.dispose()


async def test_a_full_interview_through_the_api(stack):
    s: Stack = stack()
    meet_id, _ = await s.ready_interview()
    status = (await s.http.get(f"/v1/interviews/{meet_id}")).json()
    assert status["status"] == "ready" and "opening_question" not in status

    first = (await s.http.post(f"/v1/interviews/{meet_id}/start")).json()
    assert (first["question"], first["seq"], first["ended"]) == (FIRST_WORDS, 1, False)
    assert first["started_at"] == first["server_now"]
    row = await s.interview(meet_id)
    assert (row.status, row.started_at, row.hard_end_at) == (
        "in_progress",
        T0,
        T0 + timedelta(minutes=50),
    )
    # the hard stop is waiting in the queue for hard_end + grace
    [stop_job] = [j for j in await s.redis.queued_jobs() if j.function == "hard_stop_job"]
    assert stop_job.args == (meet_id,)
    due_ms = await s.redis.zscore("arq:queue", stop_job.job_id)
    assert due_ms == (T0 + timedelta(minutes=50, seconds=GRACE_S)).timestamp() * 1000

    # first answer: carries integrity signals from the page
    s.clock.advance(150)
    second = await s.answer(
        meet_id,
        1,
        "We ran Kubernetes with HPA",
        first_keystroke_ms=4000,
        idle_ms=21000,
        pastes=[{"at_ms": 9000, "chars": 420}],
    )
    turn = second.json()
    assert second.status_code == 200 and turn["seq"] == 3 and not turn["ended"]
    assert (await s.answer(meet_id, 1)).status_code == 409  # a double submit is refused

    phases = [turn["phase"]]
    for _ in range(40):
        s.clock.advance(150)
        turn = (await s.answer(meet_id, turn["seq"], "A detailed answer")).json()
        if turn["ended"]:
            break
        phases.append(turn["phase"])
    assert turn["ended"] and turn["question"] is None
    assert phases[-1] == "closing" and set(phases[:-1]) == {"core"}  # ends on "any questions?"

    row = await s.interview(meet_id)
    assert (row.status, row.end_reason, row.ended_at) == ("completed", "natural", s.clock.now())
    turns = await s.turns(meet_id)
    assert [t.seq for t in turns] == list(range(1, len(turns) + 1))  # append-only, no gaps
    assert turns[0].text == FIRST_WORDS and turns[0].shown_at == T0
    assert turns[0].action_type == "next_topic" and turns[0].difficulty is not None
    answer = turns[1]
    assert (answer.role, answer.text, answer.cut_off) == (
        "candidate",
        "We ran Kubernetes with HPA",
        False,
    )
    assert (answer.shown_at, answer.first_keystroke_at, answer.submitted_at) == (
        T0,
        T0 + timedelta(seconds=4),
        T0 + timedelta(seconds=150),
    )
    assert turns[-1].role == "interviewer" and "thank you" in turns[-1].text.lower()
    # question, answer, question, answer, …, goodbye
    assert [t.role for t in turns] == ["interviewer", "candidate"] * (len(turns) // 2) + [
        "interviewer"
    ]
    on_topic = [t for t in turns if t.role == "candidate" and t.topic_id]
    assert {t.topic_id for t in on_topic} == {t.topic_id for t in turns if t.topic_id}
    assert len(on_topic) == len(turns) // 2 - 1  # every answer but the closing "my question"
    assert await s.events(meet_id, "paste") == [{"seq": 2, "at_ms": 9000, "chars": 420}]
    assert (await s.events(meet_id, "answer_timing"))[0] == {
        "seq": 2,
        "first_keystroke_ms": 4000,
        "idle_ms": 21000,
    }
    async with s.sessions() as db:
        analyses = (
            await db.execute(
                select(TurnAnalysis.model, TurnAnalysis.signals)
                .join(TurnRow, TurnRow.id == TurnAnalysis.turn_id)
                .where(TurnRow.interview_id == UUID(meet_id))
            )
        ).all()
    assert len(analyses) == len(on_topic) and {m for m, _ in analyses} == {"fake-model"}
    assert analyses[0].signals["coverage_ratio"] == 0.9
    # evaluation is enqueued once the interview is over
    assert "evaluate_interview_job" in [j.function for j in await s.redis.queued_jobs()]

    # one attempt per kit, and nothing more to answer
    assert (await s.http.post(f"/v1/interviews/{meet_id}/start")).status_code == 409
    assert (await s.answer(meet_id, turn["seq"] or 1)).status_code == 409
    over = (await s.http.get(f"/v1/interviews/{meet_id}/room")).json()
    assert over["ended"] and over["question"] is None


async def test_ac3_hard_stop_submits_the_draft_and_completes_the_interview(stack):
    s: Stack = stack()
    meet_id, _ = await s.ready_interview()
    await s.http.post(f"/v1/interviews/{meet_id}/start")
    draft = {"question_seq": 1, "text": "I was halfway through expl"}
    assert (await s.http.put(f"/v1/interviews/{meet_id}/draft", json=draft)).status_code == 204

    # a reloaded page gets the question and the draft back
    back = (await s.http.get(f"/v1/interviews/{meet_id}/room")).json()
    assert (back["question"], back["seq"], back["draft"]) == (FIRST_WORDS, 1, draft["text"])

    s.clock.advance(49 * 60)  # too early: the job puts itself back and changes nothing
    await s.hard_stop(meet_id)
    assert (await s.interview(meet_id)).status == "in_progress"
    assert len([j for j in await s.redis.queued_jobs() if j.function == "hard_stop_job"]) == 1

    heard: list[dict[str, str]] = []

    async def listen() -> None:  # an open page hears the end without asking; the stream closes
        heard.extend([f async for f in sse_frames(subscribe(s.redis, UUID(meet_id)))])

    listener = asyncio.create_task(listen())
    await asyncio.sleep(0.3)  # let the subscription reach Redis
    s.clock.advance(2 * 60 + 1)  # past hard_end + grace, and no answer came
    await s.hard_stop(meet_id)
    await asyncio.wait_for(listener, timeout=5)
    row = await s.interview(meet_id)
    assert (row.status, row.end_reason, row.ended_at) == ("completed", "hard_stop", s.clock.now())
    turns = await s.turns(meet_id)
    assert [(t.role, t.cut_off) for t in turns] == [
        ("interviewer", False),
        ("candidate", True),
        ("interviewer", False),
    ]
    assert turns[1].text == draft["text"] and turns[1].submitted_at == s.clock.now()
    assert "evaluate_interview_job" in [j.function for j in await s.redis.queued_jobs()]
    assert await s.redis.get(f"qualifai:draft:{meet_id}") is None
    assert [f["event"] for f in heard] == ["token", "question", "ended"]  # the goodbye
    assert json.loads(heard[-1]["data"]) == {"reason": "hard_stop"}

    await s.hard_stop(meet_id)  # a redelivered job finds nothing to do
    assert len(await s.turns(meet_id)) == 3
    assert (await s.answer(meet_id, 1)).status_code == 409  # too late to answer


async def test_hard_stop_job_leaves_a_running_interview_alone(stack):
    """The job as the worker runs it (real clock): hard_end is ~50 minutes away."""
    s: Stack = stack()
    s.clock = FrozenClock(SystemClock().now())
    meet_id, _ = await s.ready_interview()
    await s.http.post(f"/v1/interviews/{meet_id}/start")
    await hard_stop_job({"live": s.live}, meet_id)
    assert (await s.interview(meet_id)).status == "in_progress"
    await hard_stop_job({"live": s.live}, str(uuid4()))  # unknown interview: nothing happens


async def test_questions_are_streamed_and_the_draft_is_cleared_on_submit(stack):
    s: Stack = stack()
    meet_id, _ = await s.ready_interview()
    first = (await s.http.post(f"/v1/interviews/{meet_id}/start")).json()
    await s.http.put(f"/v1/interviews/{meet_id}/draft", json={"question_seq": 1, "text": "dra"})

    heard: list[dict] = []
    listening = asyncio.Event()

    async def listen() -> None:  # what GET /events sends, frame by frame
        frames = sse_frames(subscribe(s.redis, UUID(meet_id)))
        listening.set()
        async for frame in frames:
            heard.append({"event": frame["event"], **json.loads(frame["data"])})
            if frame["event"] == "question":
                return

    listener = asyncio.create_task(listen())
    await listening.wait()
    await asyncio.sleep(0.2)  # let the subscription reach Redis
    s.clock.advance(60)
    turn = (await s.answer(meet_id, first["seq"])).json()
    await asyncio.wait_for(listener, timeout=5)

    tokens = [e for e in heard if e["event"] == "token"]
    assert len(tokens) == 3 and {e["seq"] for e in tokens} == {turn["seq"]}
    assert "".join(e["text"] for e in tokens).strip() == turn["question"]
    assert heard[-1] == {"event": "question", "seq": turn["seq"], "text": turn["question"]}
    assert await s.redis.get(f"qualifai:draft:{meet_id}") is None
    refused = await s.http.put(
        f"/v1/interviews/{uuid4()}/draft", json={"question_seq": 1, "text": "x"}
    )
    assert refused.status_code == 404


async def test_a_restart_mid_interview_resumes_from_the_postgres_checkpoint(stack, pg_url):
    s: Stack = stack()
    meet_id, _ = await s.ready_interview()
    first = (await s.http.post(f"/v1/interviews/{meet_id}/start")).json()
    s.clock.advance(120)
    second = (await s.answer(meet_id, first["seq"])).json()

    # "redeploy": a new process has a new checkpointer and a new graph, and only Postgres
    async with open_checkpointer(pg_url) as fresh:
        s.checkpointer = fresh
        s.live = s.runtime()
        s.clock.advance(120)
        third = await s.answer(meet_id, second["seq"])
        assert third.status_code == 200 and third.json()["seq"] == second["seq"] + 2
    row = await s.interview(meet_id)
    assert row.status == "in_progress" and row.started_at == T0  # the clock never paused
    async with s.sessions() as db:
        checkpoints = await db.scalar(
            text("select count(*) from checkpoints where thread_id = :id"), {"id": meet_id}
        )
    assert checkpoints and checkpoints > 3  # one per node, all in Postgres


async def test_slow_turns_become_latency_credit_and_move_the_hard_stop(stack):
    s: Stack = stack()
    meet_id, _ = await s.ready_interview()
    first = (await s.http.post(f"/v1/interviews/{meet_id}/start")).json()
    generate = s.llm._responders[LLMTask.QUESTION_GEN]

    def slow(system: str, user: str) -> str:  # the candidate waits 42 s for the next question
        s.clock.advance(42)
        return generate(system, user)

    s.llm._responders[LLMTask.QUESTION_GEN] = slow
    s.clock.advance(60)
    turn = (await s.answer(meet_id, first["seq"])).json()
    row = await s.interview(meet_id)
    assert row.latency_credit_s == 40  # 42 s waited, less the 2 s that is simply normal
    assert turn["target_end_at"] == (T0 + timedelta(minutes=45, seconds=40)).isoformat().replace(
        "+00:00", "Z"
    )

    # at the original hard_end + grace the interview is not over yet: 40 s were ours
    s.clock = FrozenClock(T0 + timedelta(minutes=50, seconds=GRACE_S + 10))
    await s.hard_stop(meet_id)
    assert (await s.interview(meet_id)).status == "in_progress"
    s.clock.advance(31)
    await s.hard_stop(meet_id)
    assert (await s.interview(meet_id)).end_reason == "hard_stop"


async def test_a_question_can_be_fetched_as_audio_and_only_the_interviewers_own_words(stack):
    s: Stack = stack()
    meet_id, _ = await s.ready_interview()
    await s.http.post(f"/v1/interviews/{meet_id}/start")
    audio = f"/v1/interviews/{meet_id}/turns/1/audio"

    # no speech model: the page is told, and falls back to the browser's voice
    silent = await s.http.get(audio)
    assert (silent.status_code, silent.json()["error"]) == (503, "speech_unavailable")

    s.llm._responders[LLMTask.SPEECH] = lambda _s, text: f"WAV:{text}"
    spoken = await s.http.get(audio)
    assert spoken.status_code == 200 and spoken.headers["content-type"] == "audio/wav"
    assert spoken.content == f"WAV:{FIRST_WORDS}".encode()  # the stored turn, word for word
    assert "max-age" in spoken.headers["cache-control"]

    await s.answer(meet_id, 1)
    assert (await s.http.get(f"/v1/interviews/{meet_id}/turns/2/audio")).status_code == 404  # ours
    assert (await s.http.get(f"/v1/interviews/{meet_id}/turns/99/audio")).status_code == 404


async def test_start_checks_the_owner_the_state_and_the_expiry(stack):
    s: Stack = stack()
    assert (await s.http.post(f"/v1/interviews/{uuid4()}/start")).status_code == 404

    # sent to an email address: only the link's token opens it
    meet_id, token = await s.ready_interview(email=f"{uuid4().hex}@example.com")
    assert token and (await s.interview(meet_id)).access_token_hash == hash_token(token)
    start = f"/v1/interviews/{meet_id}/start"
    assert (await s.http.post(start)).status_code == 403
    assert (await s.http.post(start, json={"token": "wrong"})).status_code == 403
    assert (await s.interview(meet_id)).status == "ready"  # a refused start changes nothing
    assert (await s.http.get(f"/v1/interviews/{meet_id}/room")).status_code == 409
    assert (await s.answer(meet_id, 1)).status_code == 409
    opened = await s.http.post(start, json={"token": token})
    assert opened.status_code == 200 and opened.json()["question"] == FIRST_WORDS

    # ready for more than seven days: too late (spec-001 FR-8)
    stale, _ = await s.ready_interview()
    s.clock.advance(7 * 24 * 3600)
    late = await s.http.post(f"/v1/interviews/{stale}/start")
    assert late.status_code == 409 and "expired" in late.json()["message"]
    assert (await s.interview(stale)).started_at is None
