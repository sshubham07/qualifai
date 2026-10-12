"""Job scheduled at start for hard_end + grace (spec-001 T-24). No-op if the interview already
ended; otherwise auto-submits the Redis draft and resumes the graph with {'type': 'time_up'}."""

from typing import Any
from uuid import UUID

from qualifai.container import LiveRuntime
from qualifai.domain.clock import SystemClock
from qualifai.interview.room import hard_stop


async def hard_stop_job(ctx: dict[str, Any], interview_id: str) -> None:
    live: LiveRuntime = ctx["live"]
    async with live.sessions() as session:
        await hard_stop(live.room(session, SystemClock()), UUID(interview_id))
