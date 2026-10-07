"""Job scheduled at start for hard_end + grace. No-op if the interview already ended;
otherwise auto-submits the Redis draft and resumes the graph with {'type': 'time_up'}."""

from typing import Any


async def hard_stop_job(ctx: dict[str, Any], interview_id: str) -> None:
    raise NotImplementedError  # TODO(spec-001 T-24)
