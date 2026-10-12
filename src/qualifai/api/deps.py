"""FastAPI dependencies: wire request-scoped infrastructure into application services."""

from collections.abc import Awaitable, Callable
from functools import partial
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from qualifai.container import LiveRuntime
from qualifai.db.session import get_session
from qualifai.domain.clock import Clock, SystemClock
from qualifai.domain.models import InterviewRequest
from qualifai.interview.room import RoomDeps
from qualifai.prep.submission import Submission, submit_interview

Submit = Callable[[InterviewRequest, str | None], Awaitable[Submission]]


def get_clock() -> Clock:
    return SystemClock()


async def get_submit(request: Request, session: AsyncSession = Depends(get_session)) -> Submit:
    async def enqueue(interview_id: UUID) -> None:
        await request.app.state.arq.enqueue_job(
            "prepare_interview_job", str(interview_id), _job_id=f"prepare:{interview_id}"
        )

    return partial(submit_interview, session, enqueue)


def get_live(request: Request) -> LiveRuntime:
    return request.app.state.live  # type: ignore[no-any-return]  # opened in the lifespan


def get_room(
    live: LiveRuntime = Depends(get_live),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> RoomDeps:
    return live.room(session, clock)
