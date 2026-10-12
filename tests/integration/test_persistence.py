"""Integration: real Postgres via testcontainers. Skipped automatically without Docker."""

import pytest

pytestmark = pytest.mark.integration


async def test_schema_creates_and_turns_are_unique_per_seq(pg_url):
    from uuid import uuid4

    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from qualifai.db.models import Base, Interview, TurnRow, User

    engine = create_async_engine(pg_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    uid, iid = uuid4(), uuid4()
    async with Session() as s:
        s.add(User(id=uid, email=f"{uid}@example.com"))
        await s.flush()  # no ORM relationship → flush order is not FK-aware
        s.add(
            Interview(
                id=iid,
                user_id=uid,
                status="ready",
                round_type="r1_technical",
                company_tier="product",
                role_family="backend_sde",
                support_level="full",
                target_minutes=45,
                jd_text="jd",
                experience_min_years=3,
                experience_max_years=5,
            )
        )
        s.add(TurnRow(id=uuid4(), interview_id=iid, seq=1, role="interviewer", text="Q1"))
        await s.commit()
        s.add(TurnRow(id=uuid4(), interview_id=iid, seq=1, role="candidate", text="dup"))
        with pytest.raises(IntegrityError):
            await s.commit()
    await engine.dispose()


async def test_turn_sink_writes_are_safe_to_repeat(pg_url):
    """A graph node can run twice after a crash: the transcript must not change or duplicate."""
    from uuid import uuid4

    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from tests.conftest import T0, signals

    from qualifai.db.models import Base, Interview, InterviewEvent, TurnAnalysis, TurnRow
    from qualifai.db.repositories.turns import PostgresTurnSink
    from qualifai.domain.clock import FrozenClock
    from qualifai.domain.enums import EndReason, PolicyAction

    engine = create_async_engine(pg_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    iid = uuid4()
    async with sessions() as s:
        s.add(
            Interview(
                id=iid,
                status="in_progress",
                round_type="r1_technical",
                company_tier="product",
                role_family="backend_sde",
                target_minutes=45,
                jd_text="jd",
                experience_min_years=3,
                experience_max_years=5,
            )
        )
        await s.commit()

    published: list[dict] = []

    async def publish(_interview_id: str, event: dict) -> None:
        published.append(event)

    sink = PostgresTurnSink(sessions, FrozenClock(T0), publish, "some-model")
    answer = {"text": "first", "idle_ms": 900, "pastes": [{"at_ms": 5, "chars": 80}]}
    for text in ("Q1?", "Q1, phrased differently?"):
        await sink.interviewer_said(str(iid), 1, "t1", text, PolicyAction.NEXT_TOPIC, 2)
    for payload in (answer, {**answer, "text": "second"}):
        await sink.candidate_said(str(iid), 2, "t1", payload)
    for latency in (120, 999):
        await sink.analysed(str(iid), 2, signals(), latency)
    await sink.token(str(iid), 3, "Next")
    await sink.completed(str(iid), EndReason.NATURAL)

    async with sessions() as s:
        turns = (
            await s.scalars(
                select(TurnRow).where(TurnRow.interview_id == iid).order_by(TurnRow.seq)
            )
        ).all()
        events = await s.scalar(
            select(func.count())
            .select_from(InterviewEvent)
            .where(InterviewEvent.interview_id == iid)
        )
        analysis = await s.get_one(TurnAnalysis, turns[1].id)
    assert [(t.seq, t.role, t.text) for t in turns] == [
        (1, "interviewer", "Q1?"),
        (2, "candidate", "first"),
    ]
    assert events == 2  # one paste + one timing row, not four
    assert (analysis.model, analysis.latency_ms) == ("some-model", 120)
    assert [e["event"] for e in published] == ["question", "question", "token", "ended"]
    await engine.dispose()
