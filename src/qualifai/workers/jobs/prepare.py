"""Job: build the interview kit, mark READY (+ expires_at = now + 7d), send 'ready' email."""

from typing import Any


async def prepare_interview_job(ctx: dict[str, Any], interview_id: str) -> None:
    # TODO(spec-001 T-10..T-15): load request → prep.pipeline.prepare_kit(progress=publish to SSE)
    # → store kit → status READY → notifications.email.send_ready()
    raise NotImplementedError
