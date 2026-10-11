"""Job: run the intake gate, build the interview kit, mark READY (+ expires_at = now + 7d) and,
if an email was given, send the 'ready' email. Anything that stops prep (not a software role, a
resume that doesn't fit the JD, an error) leaves the interview FAILED with a reason; FAILED is a
dead end (ADR-0018)."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

import structlog
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from qualifai.config.settings import get_settings
from qualifai.db.models import Interview, InterviewEvent, InterviewKit, User
from qualifai.db.session import SessionFactory
from qualifai.domain.clock import Clock, SystemClock
from qualifai.domain.enums import CompanyTier, FailureCode, InterviewStatus, RoundType
from qualifai.domain.errors import LLMOutputError, PrepRejected
from qualifai.domain.failures import FAILURE_REASONS
from qualifai.domain.lifecycle import transition
from qualifai.domain.models import InterviewRequest
from qualifai.llm.gateway import LLM
from qualifai.notifications.email import send_kit_ready
from qualifai.prep.intake_gate import decide, run_intake
from qualifai.prep.pipeline import PreparedKit, prepare_kit

log = structlog.get_logger(__name__)
SendReady = Callable[[str, str, str], Awaitable[None]]  # (to, link, expires_on)
PREP_STEP = "prep_step"  # InterviewEvent type: one row per step, written as the step starts


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


async def _fail(
    session: AsyncSession, interview: Interview, code: FailureCode, reason: str | None = None
) -> None:
    interview.status = transition(InterviewStatus.PREPARING, InterviewStatus.FAILED).value
    interview.failure_code = code.value
    interview.failure_reason = reason or FAILURE_REASONS[code]
    await session.commit()
    log.warning("prep.failed", interview_id=str(interview.id), code=code.value)


async def _passes_gate(
    session: AsyncSession, llm: LLM, interview: Interview, req: InterviewRequest
) -> bool:
    """Both documents must be for a software role; otherwise FAILED with the reason (ADR-0016)."""
    try:
        intake = await run_intake(llm, req)
    except (ValidationError, LLMOutputError):  # no usable classification after the retries
        await _fail(session, interview, FailureCode.UNDECIDED)
        return False
    interview.role_family = intake.jd_role_family.value
    if intake.injection_suspected:  # flagged, not obeyed (spec-001 FR-2)
        session.add(InterviewEvent(interview_id=interview.id, type="injection_suspected"))
    verdict = decide(intake)
    if isinstance(verdict, FailureCode):
        await _fail(session, interview, verdict)
        return False
    interview.support_level = verdict.value
    await session.commit()  # the detected role is visible while the kit is being built
    return True


async def prepare_interview(session: AsyncSession, deps: PrepDeps, interview_id: UUID) -> None:
    interview = await session.get(Interview, interview_id)
    if interview is None or interview.status != InterviewStatus.PREPARING:
        return  # duplicate or stale job — nothing to prepare
    user = await session.get_one(User, interview.user_id) if interview.user_id else None

    steps: list[str] = []

    async def progress(step: str) -> None:  # TODO(spec-001 T-15): publish to Redis pub/sub → SSE
        steps.append(step)
        # Committed straight away so the status page can show which step is running.
        session.add(
            InterviewEvent(interview_id=interview_id, type=PREP_STEP, payload={"step": step})
        )
        await session.commit()
        log.info("prep.progress", interview_id=str(interview_id), step=step)

    req = _request(interview)
    try:
        await progress("Checking resume and job description")
        if not await _passes_gate(session, deps.llm, interview, req):
            return
        kit: PreparedKit = await prepare_kit(deps.llm, req, progress)
    except PrepRejected as stop:  # nothing to ask about, or the resume doesn't fit the JD
        await _fail(session, interview, stop.code, stop.reason)
        return
    except Exception:
        await _fail(session, interview, FailureCode.PREP_ERROR)
        raise

    # Magic link, only when there is an email to send it to; only the hash is stored.
    token = secrets.token_urlsafe(32) if user else None
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
    interview.access_token_hash = hash_token(token) if token else None
    await session.commit()

    if user and token:  # without an email the candidate checks back with the meet id
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
