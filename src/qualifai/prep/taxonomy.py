"""Skill normalisation: dictionary first (deterministic), embeddings only as a later fallback."""

from collections.abc import Mapping


def normalize_skill(raw: str, aliases: Mapping[str, str]) -> str | None:
    key = raw.strip().lower()
    return aliases.get(key)
