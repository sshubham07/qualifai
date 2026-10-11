"""Build the LLM gateway from content/models.yaml + settings (ADR-0004)."""

from __future__ import annotations

from pathlib import Path

import yaml
from openai import AsyncOpenAI
from pydantic import SecretStr

from qualifai.config.settings import Settings
from qualifai.llm.gateway import LLMGateway
from qualifai.llm.router import ModelRouter


def _setting(settings: Settings, env_name: str | None) -> str | None:
    """models.yaml names env vars (QUALIFAI_GROQ_API_KEY); Settings holds them as attributes."""
    if env_name is None:
        return None
    value = getattr(settings, env_name.removeprefix("QUALIFAI_").lower(), None)
    return value.get_secret_value() if isinstance(value, SecretStr) else value


def build_gateway(settings: Settings) -> LLMGateway:
    path = Path(settings.models_file)
    providers = yaml.safe_load(path.read_text())["providers"]
    clients: dict[str, AsyncOpenAI] = {}
    for name, spec in providers.items():
        base_url = _setting(settings, spec["base_url_env"])
        if base_url is None:
            continue  # provider not configured in this environment (e.g. vLLM locally)
        api_key = _setting(settings, spec.get("api_key_env"))
        clients[name] = AsyncOpenAI(base_url=base_url, api_key=api_key or "not-needed")
    return LLMGateway(ModelRouter.from_yaml(path), clients)
