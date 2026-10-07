"""Daily sweep: READY kits past expires_at → EXPIRED; delete kit data and the resume file.
Completed interviews: delete raw resume after completion, reports after retention period."""

from typing import Any


async def expire_kits(ctx: dict[str, Any]) -> None:
    raise NotImplementedError  # TODO(spec-001 T-40)
