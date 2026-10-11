"""Interview submission — the application service behind POST /v1/interviews (spec-001 T-20).

Dedupe by input hash, persist as PREPARING and enqueue the prep job. No model call here: the
intake gate is the job's first step (ADR-0016), so a rejection is a FAILED interview with a reason.
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from qualifai.db.models import Interview, User
from qualifai.domain.clock import Clock
from qualifai.domain.enums import InterviewStatus, RoleFamily
from qualifai.domain.lifecycle import transition
from qualifai.domain.models import Frozen, InterviewRequest

Enqueue = Callable[[UUID], Awaitable[None]]
REUSABLE = (InterviewStatus.SUBMITTED, InterviewStatus.PREPARING, InterviewStatus.READY)


class Submission(Frozen):
    interview_id: UUID
    status: InterviewStatus
    reused: bool = False


def input_hash(req: InterviewRequest) -> str:
    """Same inputs → same hash, so a resubmission reuses the kit instead of preparing again."""
    return hashlib.sha256(req.model_dump_json().encode()).hexdigest()


async def _get_or_create_user(session: AsyncSession, email: str) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(id=uuid7(), email=email)
        session.add(user)
        await session.flush()  # no ORM relationship → make sure the user row exists first
    return user


async def _reusable(
    session: AsyncSession, user_id: UUID | None, digest: str, clock: Clock
) -> Interview | None:
    owner = Interview.user_id.is_(None) if user_id is None else Interview.user_id == user_id
    return await session.scalar(
        select(Interview)
        .where(
            owner,
            Interview.input_hash == digest,
            Interview.status.in_(REUSABLE),
            or_(Interview.expires_at.is_(None), Interview.expires_at > clock.now()),
        )
        .order_by(Interview.created_at.desc())
        .limit(1)
    )


async def submit_interview(
    session: AsyncSession,
    enqueue: Enqueue,
    clock: Clock,
    req: InterviewRequest,
    email: str | None,
) -> Submission:
    user = await _get_or_create_user(session, email) if email else None  # no email → no user
    user_id = user.id if user else None
    digest = input_hash(req)
    existing = await _reusable(session, user_id, digest, clock)
    if existing is not None:
        return Submission(
            interview_id=existing.id,
            status=InterviewStatus(existing.status),
            reused=True,
        )

    interview = Interview(
        id=uuid7(),
        user_id=user_id,
        status=transition(InterviewStatus.SUBMITTED, InterviewStatus.PREPARING).value,
        round_type=req.round_type.value,
        company_tier=req.company_tier.value,
        role_family=RoleFamily.UNKNOWN.value,  # the intake gate fills these in
        support_level=None,
        target_minutes=req.target_minutes,
        input_hash=digest,
        resume_text=req.resume_text,
        jd_text=req.jd_text,
        experience_min_years=req.experience_min_years,
        experience_max_years=req.experience_max_years,
        company_name=req.company_name,
    )
    session.add(interview)
    await session.commit()

    try:
        await enqueue(interview.id)
    except Exception:
        interview.status = transition(InterviewStatus.PREPARING, InterviewStatus.FAILED).value
        await session.commit()
        raise
    return Submission(interview_id=interview.id, status=InterviewStatus.PREPARING)
