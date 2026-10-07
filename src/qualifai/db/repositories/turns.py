"""Turn repository — implements interview.graph.TurnSink against Postgres + Redis pub/sub."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from qualifai.db.models import TurnRow


class TurnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def append(
        self, interview_id: UUID, seq: int, topic_id: str | None, role: str, text: str, **extra: Any
    ) -> UUID:
        row = TurnRow(
            id=uuid7(),
            interview_id=interview_id,
            seq=seq,
            topic_id=topic_id,
            role=role,
            text=text,
            **extra,
        )
        self._s.add(row)
        await self._s.commit()  # commit BEFORE the next question is shown (spec-001 NFR-3)
        return row.id
