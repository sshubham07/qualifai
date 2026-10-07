"""Job: run eval.pipeline.evaluate_interview, store report JSON, render HTML, notify."""

from typing import Any


async def evaluate_interview_job(ctx: dict[str, Any], interview_id: str) -> None:
    raise NotImplementedError  # TODO(spec-001 T-30..T-33)
