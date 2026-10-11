"""Job: build the interview kit, mark READY (+ expires_at = now + 7d), send 'ready' email."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from qualifai.config.settings import get_settings
from qualifai.db.models import Interview, InterviewKit, User
from qualifai.db.session import SessionFactory
from qualifai.domain.clock import Clock, SystemClock
from qualifai.domain.enums import CompanyTier, InterviewStatus, RoundType
from qualifai.domain.lifecycle import transition
from qualifai.domain.models import InterviewRequest
from qualifai.llm.gateway import LLM
from qualifai.notifications.email import send_kit_ready
from qualifai.prep.pipeline import PreparedKit, prepare_kit

log = structlog.get_logger(__name__)
SendReady = Callable[[str, str, str], Awaitable[None]]  # (to, link, expires_on)


@dataclass(frozen=True, slots=True)
class PrepDeps:
    llm: LLM
    clock: Clock
    send_ready: SendReady
    base_url: str
    kit_ttl_days: int


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _request(interview: Interview) -> InterviewRequest:
    return InterviewRequest(
        resume_text=interview.resume_text or "",
        jd_text=interview.jd_text,
        round_type=RoundType(interview.round_type),
        company_tier=CompanyTier(interview.company_tier),
        experience_min_years=interview.experience_min_years,
        experience_max_years=interview.experience_max_years,
        target_minutes=interview.target_minutes,
        company_name=interview.company_name,
    )


async def _fail(session: AsyncSession, interview: Interview, reason: str) -> None:
    interview.status = transition(InterviewStatus.PREPARING, InterviewStatus.FAILED).value
    await session.commit()
    log.error("prep.failed", interview_id=str(interview.id), reason=reason)


async def prepare_interview(session: AsyncSession, deps: PrepDeps, interview_id: UUID) -> None:
    interview = await session.get(Interview, interview_id)
    if interview is None or interview.status != InterviewStatus.PREPARING:
        return  # duplicate or stale job — nothing to prepare
    user = await session.get_one(User, interview.user_id)

    steps: list[str] = []

    async def progress(step: str) -> None:  # TODO(spec-001 T-15): publish to Redis pub/sub → SSE
        steps.append(step)
        log.info("prep.progress", interview_id=str(interview_id), step=step)

    try:
        kit: PreparedKit = await prepare_kit(deps.llm, _request(interview), progress)
    except Exception as exc:
        await _fail(session, interview, type(exc).__name__)
        raise
    if not kit.plan.topics:
        await _fail(session, interview, "no_known_skills_in_jd")
        return

    token = secrets.token_urlsafe(32)  # magic link; only the hash is stored
    ready_at = deps.clock.now()
    expires_at = ready_at + timedelta(days=deps.kit_ttl_days)
    await session.merge(  # merge: a retried job overwrites its own earlier kit
        InterviewKit(
            interview_id=interview.id,
            profile=kit.model_dump(mode="json", exclude={"plan"}),
            plan=kit.plan.model_dump(mode="json"),
            prep_progress=steps,
        )
    )
    interview.status = transition(InterviewStatus.PREPARING, InterviewStatus.READY).value
    interview.ready_at = ready_at
    interview.expires_at = expires_at
    interview.access_token_hash = hash_token(token)
    await session.commit()

    link = f"{deps.base_url}/interviews/{interview.id}?token={token}"
    await deps.send_ready(user.email, link, expires_at.date().isoformat())


async def prepare_interview_job(ctx: dict[str, Any], interview_id: str) -> None:
    settings = get_settings()
    deps = PrepDeps(
        llm=ctx["llm"],
        clock=SystemClock(),
        send_ready=send_kit_ready,
        base_url=settings.base_url,
        kit_ttl_days=settings.kit_ttl_days,
    )
    async with SessionFactory() as session:
        await prepare_interview(session, deps, UUID(interview_id))
