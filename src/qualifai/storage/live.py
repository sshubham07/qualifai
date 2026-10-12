"""Redis side of a live interview (ADR-0005): autosaved drafts and the event channel the page
listens to. Both are disposable: Postgres holds the transcript, and the answer to POST /answers
carries the next question even when nobody heard the stream."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from qualifai.domain.models import Draft

log = structlog.get_logger(__name__)
DRAFT_TTL_S = 3 * 60 * 60  # longer than any interview; a forgotten draft cleans itself up


def _draft_key(interview_id: UUID | str) -> str:
    return f"qualifai:draft:{interview_id}"


def channel(interview_id: UUID | str) -> str:
    return f"qualifai:live:{interview_id}"


class RedisDrafts:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def save(self, interview_id: UUID, draft: Draft) -> None:
        await self._redis.set(_draft_key(interview_id), draft.model_dump_json(), ex=DRAFT_TTL_S)

    async def load(self, interview_id: UUID) -> Draft | None:
        raw = await self._redis.get(_draft_key(interview_id))
        return Draft.model_validate_json(raw) if raw else None

    async def clear(self, interview_id: UUID) -> None:
        await self._redis.delete(_draft_key(interview_id))


class RedisPublisher:
    """Best effort: a lost event costs the typing effect, never the interview."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def __call__(self, interview_id: str, event: dict[str, Any]) -> None:
        try:
            await self._redis.publish(channel(interview_id), json.dumps(event))
        except RedisError:
            log.warning("live.publish_failed", interview_id=interview_id, live_event=event["event"])


async def subscribe(redis: Redis, interview_id: UUID) -> AsyncIterator[dict[str, Any]]:
    """Events of one interview as they are published; stops after `ended`."""
    async with redis.pubsub() as pubsub:
        await pubsub.subscribe(channel(interview_id))
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            event: dict[str, Any] = json.loads(message["data"])
            ended = event["event"] == "ended"  # read before the consumer gets hold of the dict
            yield event
            if ended:
                return
