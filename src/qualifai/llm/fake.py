"""Deterministic fake LLM for unit / e2e tests and offline demos. No network."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from qualifai.domain.errors import SpeechUnavailable
from qualifai.llm.speech import Speech, chunks_of
from qualifai.llm.tasks import LLMTask

T = TypeVar("T", bound=BaseModel)
Responder = Callable[[str, str], dict[str, Any] | str]


class FakeLLM:
    def __init__(self, responders: dict[LLMTask, Responder]) -> None:
        self._responders = responders
        self.calls: list[tuple[LLMTask, str]] = []

    async def structured(self, task: LLMTask, system: str, user: str, schema: type[T]) -> T:
        self.calls.append((task, user))
        out = self._responders[task](system, user)
        return schema.model_validate(out)

    async def stream(self, task: LLMTask, system: str, user: str) -> AsyncIterator[str]:
        self.calls.append((task, user))
        text = self._responders[task](system, user)
        for word in str(text).split(" "):
            yield word + " "

    async def speak(self, task: LLMTask, text: str) -> Speech:
        self.calls.append((task, text))
        if task not in self._responders:
            raise SpeechUnavailable(f"{task}: no fake voice")
        return Speech("audio/wav", chunks_of(str(self._responders[task]("", text)).encode()))
