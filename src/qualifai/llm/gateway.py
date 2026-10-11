"""LLM Gateway — one client for every OpenAI-compatible provider (Ollama, Groq, vLLM, ...).

Responsibilities:
  * route each task to its configured model
  * request structured JSON output and validate it with Pydantic (retry on failure)
  * stream text for live phrasing
  * log provider / model / tokens / latency per call (cost + quality analysis later)
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Protocol, TypeVar

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from qualifai.domain.errors import LLMOutputError
from qualifai.llm.router import ModelRouter
from qualifai.llm.tasks import LLMTask

log = structlog.get_logger(__name__)
T = TypeVar("T", bound=BaseModel)
_RETRY_WAIT = wait_exponential(min=0.5, max=4)


class LLM(Protocol):
    """What the rest of the system depends on — makes FakeLLM a drop-in for tests."""

    async def structured(self, task: LLMTask, system: str, user: str, schema: type[T]) -> T: ...

    def stream(self, task: LLMTask, system: str, user: str) -> AsyncIterator[str]: ...


class LLMGateway:
    def __init__(self, router: ModelRouter, clients: dict[str, AsyncOpenAI]) -> None:
        self._router = router
        self._clients = clients

    async def structured(self, task: LLMTask, system: str, user: str, schema: type[T]) -> T:
        # AsyncRetrying rather than @retry: the decorator erases the signature, so the class
        # would no longer satisfy the LLM protocol under mypy.
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((ValidationError, LLMOutputError)),
            stop=stop_after_attempt(3),
            wait=_RETRY_WAIT,
            reraise=True,
        ):
            with attempt:
                return await self._structured_once(task, system, user, schema)
        raise LLMOutputError(f"{task}: no attempt was made")  # unreachable; keeps mypy honest

    async def _structured_once(self, task: LLMTask, system: str, user: str, schema: type[T]) -> T:
        route = self._router.route(task)
        client = self._clients[route.provider]
        started = time.perf_counter()
        resp = await client.chat.completions.create(
            model=route.model,
            temperature=route.temperature,
            max_tokens=route.max_tokens,
            timeout=route.timeout_s,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
            },
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        content = resp.choices[0].message.content
        if not content:
            raise LLMOutputError(f"{task}: empty response")
        result = schema.model_validate_json(content)
        log.info(
            "llm.call",
            task=task,
            provider=route.provider,
            model=route.model,
            latency_ms=round((time.perf_counter() - started) * 1000),
            prompt_tokens=getattr(resp.usage, "prompt_tokens", None),
            completion_tokens=getattr(resp.usage, "completion_tokens", None),
        )
        return result

    async def stream(self, task: LLMTask, system: str, user: str) -> AsyncIterator[str]:
        route = self._router.route(task)
        client = self._clients[route.provider]
        stream = await client.chat.completions.create(
            model=route.model,
            temperature=route.temperature,
            max_tokens=route.max_tokens,
            stream=True,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
