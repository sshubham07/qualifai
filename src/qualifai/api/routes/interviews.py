"""Interview endpoints. Thin: validate → call application service → map result.

POST /v1/interviews               resume text + JD text + tier + experience → 202 (prep enqueued)
GET  /v1/interviews/{id}          status, prep progress, server time
GET  /v1/interviews/{id}/events   SSE: prep progress, streamed questions
POST /v1/interviews/{id}/start    READY → IN_PROGRESS, returns first question
POST /v1/interviews/{id}/answers  submit answer, returns next question
GET  /v1/interviews/{id}/report   report JSON (HTML via ?format=html)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from qualifai.api.deps import Submit, get_clock, get_submit
from qualifai.api.schemas import (
    AnswerIn,
    InterviewAccepted,
    InterviewIn,
    InterviewStatusOut,
    NextQuestionOut,
)
from qualifai.db.models import Interview, InterviewKit
from qualifai.db.session import get_session
from qualifai.domain.clock import Clock
from qualifai.domain.enums import InterviewStatus

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=InterviewAccepted)
async def create_interview(
    body: InterviewIn, submit: Submit = Depends(get_submit)
) -> InterviewAccepted:
    result = await submit(body.to_request(), body.email)
    return InterviewAccepted(
        interview_id=result.interview_id,
        status=result.status,
        detected_role=result.role_family.value,
        support=result.support.value,
    )


@router.get("/{interview_id}", response_model=InterviewStatusOut)
async def get_interview(
    interview_id: UUID,
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> InterviewStatusOut:
    interview = await session.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    kit = await session.get(InterviewKit, interview_id)
    return InterviewStatusOut(
        interview_id=interview.id,
        status=InterviewStatus(interview.status),
        detected_role=interview.role_family,
        support=interview.support_level,
        progress=kit.prep_progress if kit else [],
        expires_at=interview.expires_at,
        started_at=interview.started_at,
        target_end_at=interview.target_end_at,
        server_now=clock.now(),
    )


@router.post("/{interview_id}/start", response_model=NextQuestionOut)
async def start_interview(interview_id: UUID) -> NextQuestionOut:
    # TODO(spec-001 T-22): check owner + READY + not expired; set TimeWindow; schedule hard-stop
    # job at hard_end + grace; InterviewService.start(); return first question.
    raise NotImplementedError


@router.post("/{interview_id}/answers", response_model=NextQuestionOut)
async def submit_answer(interview_id: UUID, body: AnswerIn) -> NextQuestionOut:
    # TODO(spec-001 T-23): record integrity events (paste, timing), compute answer_seconds,
    # InterviewService.submit_answer(); if ended → enqueue evaluation job.
    raise NotImplementedError


@router.get("/{interview_id}/report")
async def get_report(interview_id: UUID, format: str = "json") -> dict[str, object]:
    raise NotImplementedError  # TODO(spec-001 T-30)
