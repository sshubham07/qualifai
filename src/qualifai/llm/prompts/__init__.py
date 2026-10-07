"""Prompt templates live as .md files next to this module; loaded by name and versioned in git."""

from functools import cache
from pathlib import Path

_DIR = Path(__file__).parent


@cache
def load_prompt(name: str) -> str:
    return (_DIR / f"{name}.md").read_text()
