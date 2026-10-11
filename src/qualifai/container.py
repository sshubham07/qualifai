"""Composition root shared by the two processes (api + worker, ADR-0001): builds the one LLM
gateway so neither the API layer nor job code constructs provider clients itself."""

from functools import cache

from qualifai.config.settings import get_settings
from qualifai.llm.factory import build_gateway
from qualifai.llm.gateway import LLM


@cache
def get_llm() -> LLM:
    return build_gateway(get_settings())
