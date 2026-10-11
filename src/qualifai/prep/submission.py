"""Interview submission — the application service behind POST /v1/interviews (spec-001 T-20).

Intake gate first (nothing is stored or enqueued for an unsupported role), then dedupe by input
hash, then persist as PREPARING and enqueue the prep job.
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from qualifai.db.models import Interview, InterviewEvent, User
from qualifai.domain.clock import Clock
from qualifai.domain.enums import InterviewStatus, RoleFamily, SupportLevel
from qualifai.domain.lifecycle import transition
from qualifai.domain.models import Frozen, InterviewRequest
from qualifai.llm.gateway import LLM
from qualifai.prep.intake_gate import run_intake

Enqueue = Callable[[UUID], Awaitable[None]]
REUSABLE = (InterviewStatus.SUBMITTED, InterviewStatus.PREPARING, InterviewStatus.READY)


class Submission(Frozen):
    interview_id: UUID
    status: InterviewStatus
    role_family: RoleFamily
    support: SupportLevel
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
    session: AsyncSession, user: User, digest: str, clock: Clock
) -> Interview | None:
    return await session.scalar(
        select(Interview)
        .where(
            Interview.user_id == user.id,
            Interview.input_hash == digest,
            Interview.status.in_(REUSABLE),
            or_(Interview.expires_at.is_(None), Interview.expires_at > clock.now()),
        )
        .order_by(Interview.created_at.desc())
        .limit(1)
    )


async def submit_interview(
    session: AsyncSession,
    llm: LLM,
    enqueue: Enqueue,
    clock: Clock,
    req: InterviewRequest,
    email: str,
) -> Submission:
    intake, support = await run_intake(llm, req)  # raises for unsupported roles / invalid docs

    user = await _get_or_create_user(session, email)
    digest = input_hash(req)
    existing = await _reusable(session, user, digest, clock)
    if existing is not None:
        return Submission(
            interview_id=existing.id,
            status=InterviewStatus(existing.status),
            role_family=RoleFamily(existing.role_family),
            support=SupportLevel(existing.support_level),
            reused=True,
        )

    interview = Interview(
        id=uuid7(),
        user_id=user.id,
        status=transition(InterviewStatus.SUBMITTED, InterviewStatus.PREPARING).value,
        round_type=req.round_type.value,
        company_tier=req.company_tier.value,
        role_family=intake.role_family.value,
        support_level=support.value,
        target_minutes=req.target_minutes,
        input_hash=digest,
        resume_text=req.resume_text,
        jd_text=req.jd_text,
        experience_min_years=req.experience_min_years,
        experience_max_years=req.experience_max_years,
        company_name=req.company_name,
    )
    session.add(interview)
    await session.flush()
    if intake.injection_suspected:  # flagged, not obeyed (spec-001 FR-2)
        session.add(InterviewEvent(interview_id=interview.id, type="injection_suspected"))
    await session.commit()

    try:
        await enqueue(interview.id)
    except Exception:
        interview.status = transition(InterviewStatus.PREPARING, InterviewStatus.FAILED).value
        await session.commit()
        raise
    return Submission(
        interview_id=interview.id,
        status=InterviewStatus.PREPARING,
        role_family=intake.role_family,
        support=support,
    )
