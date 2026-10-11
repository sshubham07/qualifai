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
                input_hash="h",
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
