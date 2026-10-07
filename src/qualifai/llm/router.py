"""Task → (provider, model, params) routing loaded from content/models.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from qualifai.llm.tasks import LLMTask


@dataclass(frozen=True, slots=True)
class ModelRoute:
    provider: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout_s: float = 60.0


class ModelRouter:
    def __init__(self, routes: dict[LLMTask, ModelRoute]) -> None:
        missing = set(LLMTask) - routes.keys()
        if missing:
            raise ValueError(f"models.yaml is missing routes for: {sorted(missing)}")
        self._routes = routes

    @classmethod
    def from_yaml(cls, path: Path) -> ModelRouter:
        raw = yaml.safe_load(path.read_text())
        routes = {LLMTask(k): ModelRoute(**v) for k, v in raw["tasks"].items()}
        return cls(routes)

    def route(self, task: LLMTask) -> ModelRoute:
        return self._routes[task]
