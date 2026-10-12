"""Postgres implementation of interview.graph.TurnSink: the append-only transcript.

Every write commits in its own short transaction, so an answer is durable before the next
question exists (spec-001 NFR-3), and is safe to repeat: a graph node that runs again after a
crash finds its row already there and changes nothing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid6 import uuid7

from qualifai.db.models import InterviewEvent, TurnAnalysis, TurnRow
from qualifai.domain.clock import Clock
from qualifai.domain.enums import EndReason, PolicyAction
from qualifai.domain.models import TurnSignals

Publish = Callable[[str, dict[str, Any]], Awaitable[None]]  # (interview_id, event) → live page
PASTE, ANSWER_TIMING = "paste", "answer_timing"  # InterviewEvent types (integrity signals)


def _at(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class PostgresTurnSink:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        clock: Clock,
        publish: Publish,
        analyzer_model: str,
    ) -> None:
        self._sessions, self._clock, self._publish = sessions, clock, publish
        self._analyzer_model = analyzer_model

    async def _append(self, session: AsyncSession, **row: Any) -> bool:
        """Insert one turn; False when this (interview, seq) was already written."""
        stmt = (
            insert(TurnRow)
            .values(id=uuid7(), **row)
            .on_conflict_do_nothing(index_elements=["interview_id", "seq"])
            .returning(TurnRow.id)
        )
        return (await session.execute(stmt)).scalar_one_or_none() is not None

    async def token(self, interview_id: str, seq: int, text: str) -> None:
        await self._publish(interview_id, {"event": "token", "seq": seq, "text": text})

    async def interviewer_said(
        self,
        interview_id: str,
        seq: int,
        topic_id: str | None,
        text: str,
        action: PolicyAction,
        difficulty: int | None,
    ) -> None:
        async with self._sessions() as session:
            await self._append(
                session,
                interview_id=UUID(interview_id),
                seq=seq,
                topic_id=topic_id,
                role="interviewer",
                text=text,
                action_type=action.value,
                difficulty=difficulty,
                shown_at=self._clock.now(),
            )
            await session.commit()
        await self._publish(interview_id, {"event": "question", "seq": seq, "text": text})

    async def candidate_said(
        self, interview_id: str, seq: int, topic_id: str | None, payload: dict[str, Any]
    ) -> None:
        """The answer and the integrity signals seen while it was typed, in one transaction."""
        iid = UUID(interview_id)
        async with self._sessions() as session:
            new = await self._append(
                session,
                interview_id=iid,
                seq=seq,
                topic_id=topic_id,
                role="candidate",
                text=payload["text"],
                shown_at=_at(payload.get("shown_at")),
                first_keystroke_at=_at(payload.get("first_keystroke_at")),
                submitted_at=_at(payload.get("submitted_at")),
                cut_off=bool(payload.get("cut_off", False)),
            )
            if new:
                session.add_all(
                    InterviewEvent(interview_id=iid, type=PASTE, payload={"seq": seq, **paste})
                    for paste in payload.get("pastes", [])
                )
                if "idle_ms" in payload:
                    timing = {k: payload.get(k) for k in ("first_keystroke_ms", "idle_ms")}
                    session.add(
                        InterviewEvent(
                            interview_id=iid, type=ANSWER_TIMING, payload={"seq": seq, **timing}
                        )
                    )
            await session.commit()

    async def analysed(
        self, interview_id: str, seq: int, signals: TurnSignals, latency_ms: int
    ) -> None:
        async with self._sessions() as session:
            turn_id = await session.scalar(
                select(TurnRow.id).where(
                    TurnRow.interview_id == UUID(interview_id), TurnRow.seq == seq
                )
            )
            await session.execute(
                insert(TurnAnalysis)
                .values(
                    turn_id=turn_id,
                    signals=signals.model_dump(mode="json"),
                    model=self._analyzer_model,
                    latency_ms=latency_ms,
                )
                .on_conflict_do_nothing(index_elements=["turn_id"])
            )
            await session.commit()

    async def completed(self, interview_id: str, end_reason: EndReason) -> None:
        # The `interviews` row is closed by interview/room.py, which holds its lock.
        await self._publish(interview_id, {"event": "ended", "reason": end_reason.value})
