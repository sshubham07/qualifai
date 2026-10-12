"""Composition root shared by the two processes (api + worker, ADR-0001): builds the one LLM
gateway and the live-interview runtime, so neither the API layer nor job code constructs provider
clients, checkpointers or Redis helpers itself."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from uuid import UUID

from arq.connections import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from qualifai.config.settings import get_settings
from qualifai.db.repositories.turns import PostgresTurnSink
from qualifai.domain.clock import Clock
from qualifai.interview.checkpoint import open_checkpointer
from qualifai.interview.room import RoomDeps
from qualifai.interview.service import InterviewService
from qualifai.llm.factory import build_gateway
from qualifai.llm.gateway import LLM
from qualifai.llm.router import ModelRouter
from qualifai.llm.tasks import LLMTask
from qualifai.storage.live import RedisDrafts, RedisPublisher


@cache
def get_llm() -> LLM:
    return build_gateway(get_settings())


@dataclass(frozen=True, slots=True)
class LiveRuntime:
    """What a process needs to run live interviews; opened once at startup."""

    service: InterviewService
    llm: LLM
    redis: ArqRedis  # the arq pool: job queue, drafts and the live event channel
    sessions: async_sessionmaker[AsyncSession]
    analyzer_model: str
    hard_stop_grace_s: int

    async def schedule_hard_stop(self, interview_id: UUID, at: datetime) -> None:
        # The due time is part of the job id: a hard stop moved by latency credit is a new job.
        await self.redis.enqueue_job(
            "hard_stop_job",
            str(interview_id),
            _defer_until=at,
            _job_id=f"hard_stop:{interview_id}:{int(at.timestamp())}",
        )

    async def enqueue_evaluation(self, interview_id: UUID) -> None:
        await self.redis.enqueue_job(
            "evaluate_interview_job", str(interview_id), _job_id=f"evaluate:{interview_id}"
        )

    def room(self, session: AsyncSession, clock: Clock) -> RoomDeps:
        sink = PostgresTurnSink(
            self.sessions, clock, RedisPublisher(self.redis), self.analyzer_model
        )
        return RoomDeps(
            session=session,
            service=self.service,
            llm=self.llm,
            sink=sink,
            clock=clock,
            drafts=RedisDrafts(self.redis),
            schedule_hard_stop=self.schedule_hard_stop,
            enqueue_evaluation=self.enqueue_evaluation,
            hard_stop_grace_s=self.hard_stop_grace_s,
        )


@asynccontextmanager
async def open_live_runtime(
    redis: ArqRedis, sessions: async_sessionmaker[AsyncSession], llm: LLM | None = None
) -> AsyncIterator[LiveRuntime]:
    settings = get_settings()
    router = ModelRouter.from_yaml(Path(settings.models_file))
    async with open_checkpointer(settings.database_url) as checkpointer:
        yield LiveRuntime(
            service=InterviewService(checkpointer),
            llm=llm or get_llm(),
            redis=redis,
            sessions=sessions,
            analyzer_model=router.route(LLMTask.TURN_ANALYZER).model,
            hard_stop_grace_s=settings.hard_stop_grace_s,
        )
