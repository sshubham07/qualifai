"""Interview endpoints. Thin: validate → call application service → map result.

POST /v1/interviews               resume text + JD text + tier + experience → 202 + meet_id
GET  /v1/interviews/{id}          status, failure reason, prep progress, server time (id = meet_id)
POST /v1/interviews/{id}/start    READY → IN_PROGRESS, returns first question
POST /v1/interviews/{id}/answers  submit answer, returns next question
PUT  /v1/interviews/{id}/draft    autosave the answer being typed
GET  /v1/interviews/{id}/room     pending question + draft, for a reloaded page
GET  /v1/interviews/{id}/events   SSE: the next question token by token, then `ended`
GET  /v1/interviews/{id}/report   report JSON (HTML via ?format=html)
"""

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from qualifai.api.deps import Submit, get_clock, get_live, get_room, get_submit
from qualifai.api.schemas import (
    AnswerIn,
    DraftIn,
    InterviewAccepted,
    InterviewIn,
    InterviewStatusOut,
    NextQuestionOut,
    StartIn,
)
from qualifai.container import LiveRuntime
from qualifai.db.models import Interview, InterviewEvent, InterviewKit
from qualifai.db.session import get_session
from qualifai.domain.clock import Clock
from qualifai.domain.enums import InterviewStatus, RoleFamily, RoundType
from qualifai.interview import room
from qualifai.storage.live import subscribe

router = APIRouter(prefix="/interviews", tags=["interviews"])


async def _prep_steps(session: AsyncSession, interview_id: UUID) -> list[str]:
    """Steps the prep job has started, in order; the last one is running (or where it stopped)."""
    payloads = await session.scalars(
        select(InterviewEvent.payload)
        .where(InterviewEvent.interview_id == interview_id, InterviewEvent.type == "prep_step")
        .order_by(InterviewEvent.id)
    )
    return list(dict.fromkeys(p["step"] for p in payloads))  # a redelivered job repeats steps


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=InterviewAccepted)
async def create_interview(
    body: InterviewIn, submit: Submit = Depends(get_submit)
) -> InterviewAccepted:
    result = await submit(body.to_request(), body.email)
    return InterviewAccepted(meet_id=result.interview_id, status=result.status)


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
    status_ = InterviewStatus(interview.status)
    return InterviewStatusOut(
        meet_id=interview.id,
        status=status_,
        round_type=RoundType(interview.round_type),
        target_minutes=interview.target_minutes,
        detected_role=None
        if interview.role_family == RoleFamily.UNKNOWN
        else interview.role_family,
        support=interview.support_level,
        failure_code=interview.failure_code,
        failure_reason=interview.failure_reason,
        progress=await _prep_steps(session, interview_id) or (kit.prep_progress if kit else []),
        expires_at=interview.expires_at,
        started_at=interview.started_at,
        target_end_at=interview.target_end_at,
        server_now=clock.now(),
    )


def _next(turn: room.RoomTurn, clock: Clock) -> NextQuestionOut:
    return NextQuestionOut(**turn.model_dump(), server_now=clock.now())


@router.post("/{interview_id}/start", response_model=NextQuestionOut)
async def start_interview(
    interview_id: UUID,
    body: StartIn | None = None,
    deps: room.RoomDeps = Depends(get_room),
) -> NextQuestionOut:
    turn = await room.start_interview(deps, interview_id, body.token if body else None)
    return _next(turn, deps.clock)


@router.post("/{interview_id}/answers", response_model=NextQuestionOut)
async def submit_answer(
    interview_id: UUID, body: AnswerIn, deps: room.RoomDeps = Depends(get_room)
) -> NextQuestionOut:
    return _next(await room.submit_answer(deps, interview_id, body), deps.clock)


@router.put("/{interview_id}/draft", status_code=status.HTTP_204_NO_CONTENT)
async def save_draft(
    interview_id: UUID, body: DraftIn, deps: room.RoomDeps = Depends(get_room)
) -> None:
    await room.save_draft(deps, interview_id, body)


@router.get("/{interview_id}/room", response_model=NextQuestionOut)
async def rejoin_room(
    interview_id: UUID, deps: room.RoomDeps = Depends(get_room)
) -> NextQuestionOut:
    return _next(await room.rejoin(deps, interview_id), deps.clock)


async def sse_frames(events: AsyncIterator[dict[str, Any]]) -> AsyncIterator[dict[str, str]]:
    """Live events → SSE frames: the event's name, and the rest of it as JSON data."""
    async for event in events:
        data = {k: v for k, v in event.items() if k != "event"}
        yield {"event": event["event"], "data": json.dumps(data)}


@router.get("/{interview_id}/events")
async def interview_events(
    interview_id: UUID, live: LiveRuntime = Depends(get_live)
) -> EventSourceResponse:
    """`token` events while a question is being phrased, `question` once it is committed,
    `ended` at the end. Only a nicety: POST /answers returns the same question."""
    return EventSourceResponse(sse_frames(subscribe(live.redis, interview_id)))


@router.get("/{interview_id}/report")
async def get_report(interview_id: UUID, format: str = "json") -> dict[str, object]:
    raise NotImplementedError  # TODO(spec-001 T-30)
